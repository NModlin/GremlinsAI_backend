# tests/conftest.py
"""
Shared test configuration and fixtures for GremlinsAI Backend Test Suite.

This module provides common fixtures, test database setup, mocking configuration,
and other shared testing utilities used across all test modules.
"""

import os
import pytest
import asyncio
import tempfile
import shutil
from typing import AsyncGenerator, Generator, Dict, Any
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

# Set test environment before importing app modules
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///./data/test_gremlinsai.db"
os.environ["DISABLE_EXTERNAL_APIS"] = "true"
os.environ["MOCK_LLM_RESPONSES"] = "true"
os.environ["OPENAI_API_KEY"] = "test-key-for-testing"

# Mock problematic imports before they're loaded
import sys
from unittest.mock import Mock

# Mock CrewAI components that might cause issues
sys.modules['crewai'] = Mock()
sys.modules['crewai_tools'] = Mock()
sys.modules['langchain_openai'] = Mock()

from app.main import app
from app.database.database import get_db, Base
from app.database.models import Conversation, Message, Document
from app.services.chat_history import ChatHistoryService
from app.services.document_service import DocumentService


# Test Database Configuration
TEST_DATABASE_URL = "sqlite+aiosqlite:///./data/test_gremlinsai.db"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    # Ensure test data directory exists
    Path("./data").mkdir(exist_ok=True)
    
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def test_db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def override_get_db(test_db_session):
    """Override the get_db dependency for testing."""
    async def _override_get_db():
        yield test_db_session
    
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def test_client(override_get_db) -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI application."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


# Mock Fixtures for External Services

@pytest.fixture
def mock_llm_response():
    """Mock LLM response for testing."""
    return {
        "output": "This is a mock AI response for testing purposes.",
        "usage": {"tokens": 50},
        "model": "mock-model"
    }


@pytest.fixture
def mock_search_results():
    """Mock search results for testing."""
    return [
        {
            "title": "Test Search Result 1",
            "url": "https://example.com/1",
            "snippet": "This is a test search result snippet."
        },
        {
            "title": "Test Search Result 2", 
            "url": "https://example.com/2",
            "snippet": "Another test search result snippet."
        }
    ]


@pytest.fixture
def mock_vector_store():
    """Mock vector store for testing."""
    mock_store = Mock()
    mock_store.search = AsyncMock(return_value=[
        {"id": "doc1", "score": 0.95, "payload": {"content": "Test document 1"}},
        {"id": "doc2", "score": 0.87, "payload": {"content": "Test document 2"}}
    ])
    mock_store.add_documents = AsyncMock(return_value=True)
    mock_store.delete_document = AsyncMock(return_value=True)
    return mock_store


@pytest.fixture
def mock_multi_agent_response():
    """Mock multi-agent workflow response."""
    return {
        "result": "This is a mock multi-agent workflow result.",
        "agents_used": ["researcher", "analyst", "writer"],
        "execution_time": 2.5,
        "workflow_type": "research_analyze_write"
    }


# Test Data Fixtures

@pytest.fixture
async def sample_conversation(test_db_session) -> Conversation:
    """Create a sample conversation for testing."""
    conversation = Conversation(
        title="Test Conversation",
        user_id="test-user-123"
    )
    test_db_session.add(conversation)
    await test_db_session.commit()
    await test_db_session.refresh(conversation)
    return conversation


@pytest.fixture
async def sample_messages(test_db_session, sample_conversation) -> list[Message]:
    """Create sample messages for testing."""
    messages = [
        Message(
            conversation_id=sample_conversation.id,
            role="user",
            content="Hello, this is a test message."
        ),
        Message(
            conversation_id=sample_conversation.id,
            role="assistant", 
            content="Hello! This is a test response."
        )
    ]
    
    for message in messages:
        test_db_session.add(message)
    
    await test_db_session.commit()
    
    for message in messages:
        await test_db_session.refresh(message)
    
    return messages


@pytest.fixture
async def sample_document(test_db_session) -> Document:
    """Create a sample document for testing."""
    document = Document(
        title="Test Document",
        content="This is a test document content for testing purposes.",
        content_type="text/plain",
        tags=["test", "sample"]
    )
    test_db_session.add(document)
    await test_db_session.commit()
    await test_db_session.refresh(document)
    return document


# Service Fixtures

@pytest.fixture
def chat_history_service(test_db_session) -> ChatHistoryService:
    """Create a ChatHistoryService instance for testing."""
    return ChatHistoryService()


@pytest.fixture
def document_service(test_db_session) -> DocumentService:
    """Create a DocumentService instance for testing."""
    return DocumentService()


# Mock Patches

@pytest.fixture(autouse=True)
def mock_external_services():
    """Automatically mock external services for all tests."""
    with patch('app.core.tools.duckduckgo_search') as mock_search, \
         patch('app.core.multi_agent.multi_agent_orchestrator') as mock_multi_agent, \
         patch('app.core.vector_store.vector_store') as mock_vector:
        
        # Configure mock search
        mock_search.return_value = "Mock search results for testing"
        
        # Configure mock multi-agent
        mock_multi_agent.execute_workflow = AsyncMock(return_value={
            "result": "Mock multi-agent result",
            "agents_used": ["researcher"],
            "execution_time": 1.0
        })
        
        # Configure mock vector store
        mock_vector.search = AsyncMock(return_value=[])
        mock_vector.add_documents = AsyncMock(return_value=True)
        
        yield {
            "search": mock_search,
            "multi_agent": mock_multi_agent,
            "vector_store": mock_vector
        }


# Performance Test Fixtures

@pytest.fixture
def performance_test_config():
    """Configuration for performance tests."""
    return {
        "duration": int(os.getenv("PERFORMANCE_TEST_DURATION", "10")),
        "users": int(os.getenv("PERFORMANCE_TEST_USERS", "5")),
        "ramp_up": int(os.getenv("PERFORMANCE_TEST_RAMP_UP", "2"))
    }


# Utility Functions

def assert_response_structure(response_data: Dict[str, Any], expected_keys: list[str]):
    """Assert that response data contains expected keys."""
    for key in expected_keys:
        assert key in response_data, f"Expected key '{key}' not found in response"


def assert_valid_uuid(uuid_string: str):
    """Assert that a string is a valid UUID."""
    import uuid
    try:
        uuid.UUID(uuid_string)
    except ValueError:
        pytest.fail(f"'{uuid_string}' is not a valid UUID")


def assert_valid_timestamp(timestamp_string: str):
    """Assert that a string is a valid ISO timestamp."""
    from datetime import datetime
    try:
        datetime.fromisoformat(timestamp_string.replace('Z', '+00:00'))
    except ValueError:
        pytest.fail(f"'{timestamp_string}' is not a valid ISO timestamp")
