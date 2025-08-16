# tests/conftest.py
"""
Shared test configuration and fixtures for GremlinsAI Backend Test Suite.

This module provides common fixtures, test database setup, mocking configuration,
and other shared testing utilities used across all test modules.
"""

import os
import pytest
import pytest_asyncio
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


@pytest_asyncio.fixture(scope="function")
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


@pytest_asyncio.fixture
async def override_get_db(test_engine):
    """Override the get_db dependency for testing."""
    # Create a session maker for the test engine
    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def _override_get_db():
        async with async_session() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_client(override_get_db) -> TestClient:
    """Create a test client for the FastAPI application."""
    return TestClient(app)


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
    mock_store.is_connected = True
    mock_store.search_similar = Mock(return_value=[
        {"id": "doc1", "score": 0.95, "payload": {"content": "Test document 1"}},
        {"id": "doc2", "score": 0.87, "payload": {"content": "Test document 2"}}
    ])
    mock_store.add_document = Mock(return_value="test-doc-id")
    mock_store.delete_document = Mock(return_value=True)
    mock_store.chunk_text = Mock(return_value=["Test chunk 1", "Test chunk 2"])
    mock_store.embed_text = Mock(return_value=[0.1, 0.2, 0.3])
    mock_store.embedding_model_name = "test-model"
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
async def sample_conversation(test_engine) -> Conversation:
    """Create a sample conversation for testing."""
    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        conversation = Conversation(
            title="Test Conversation",
            user_id="test-user-123"
        )
        session.add(conversation)
        await session.commit()
        await session.refresh(conversation)
        return conversation


@pytest.fixture
async def sample_messages(test_engine, sample_conversation) -> list[Message]:
    """Create sample messages for testing."""
    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
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
            session.add(message)

        await session.commit()

        for message in messages:
            await session.refresh(message)

        return messages


@pytest.fixture
async def sample_document(test_engine) -> Document:
    """Create a sample document for testing."""
    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        document = Document(
            title="Test Document",
            content="This is a test document content for testing purposes.",
            content_type="text/plain",
            tags=["test", "sample"]
        )
        session.add(document)
        await session.commit()
        await session.refresh(document)
        return document


# Service Fixtures

@pytest.fixture
def chat_history_service() -> ChatHistoryService:
    """Create a ChatHistoryService instance for testing."""
    return ChatHistoryService()


@pytest.fixture
def document_service() -> DocumentService:
    """Create a DocumentService instance for testing."""
    return DocumentService()


# Mock Patches

@pytest.fixture(autouse=True)
def mock_external_services():
    """Automatically mock external services for all tests."""
    with patch('app.core.tools.duckduckgo_search') as mock_search, \
         patch('app.core.multi_agent.multi_agent_orchestrator') as mock_multi_agent, \
         patch('app.core.vector_store.vector_store') as mock_vector, \
         patch('app.services.document_service.vector_store') as mock_doc_vector, \
         patch('app.core.service_monitor.check_multimodal_dependencies') as mock_multimodal_check, \
         patch('app.core.service_monitor.check_openai_availability') as mock_openai_check, \
         patch('app.core.service_monitor.check_qdrant_availability') as mock_qdrant_check:

        # Configure mock search
        mock_search.return_value = "Mock search results for testing"

        # Configure mock multi-agent
        mock_multi_agent.execute_workflow = AsyncMock(return_value={
            "result": "Mock multi-agent result",
            "agents_used": ["researcher"],
            "execution_time": 1.0
        })

        # Configure mock vector store
        mock_vector.is_connected = True
        mock_vector.search_similar = Mock(return_value=[])
        mock_vector.add_document = Mock(return_value="test-doc-id")
        mock_vector.chunk_text = Mock(return_value=["Test chunk"])
        mock_vector.embed_text = Mock(return_value=[0.1, 0.2, 0.3])
        mock_vector.embedding_model_name = "test-model"

        # Configure mock document service vector store
        mock_doc_vector.is_connected = True
        mock_doc_vector.search_similar = Mock(return_value=[])
        mock_doc_vector.add_document = Mock(return_value="test-doc-id")
        mock_doc_vector.chunk_text = Mock(return_value=["Test chunk"])
        mock_doc_vector.embed_text = Mock(return_value=[0.1, 0.2, 0.3])
        mock_doc_vector.embedding_model_name = "test-model"

        # Mock service monitoring functions to prevent unavailable service warnings
        from app.core.exceptions import ServiceStatus
        mock_service_status = ServiceStatus(
            service_name="test_service",
            status="available",
            fallback_available=True,
            capabilities_affected=[]
        )
        mock_multimodal_check.return_value = [mock_service_status, mock_service_status, mock_service_status]
        mock_openai_check.return_value = mock_service_status
        mock_qdrant_check.return_value = mock_service_status

        yield {
            "search": mock_search,
            "multi_agent": mock_multi_agent,
            "vector_store": mock_vector,
            "doc_vector_store": mock_doc_vector,
            "multimodal_check": mock_multimodal_check,
            "openai_check": mock_openai_check,
            "qdrant_check": mock_qdrant_check
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


def assert_sanitized_input(original_input: str, processed_input: str):
    """Assert that input has been properly sanitized."""
    # Check that malicious content has been removed or neutralized
    processed_lower = processed_input.lower()

    # Should not contain script tags
    assert "<script>" not in processed_lower
    assert "</script>" not in processed_lower

    # Should not contain javascript: protocols
    assert "javascript:" not in processed_lower

    # Should not contain event handlers
    assert "onerror=" not in processed_lower
    assert "onclick=" not in processed_lower
    assert "onload=" not in processed_lower

    # Should not contain data: URLs with scripts
    assert "data:text/html" not in processed_lower


def assert_error_response_format(response_data: dict, expected_status: int = None):
    """Assert that error response follows consistent format."""
    assert "detail" in response_data
    assert isinstance(response_data["detail"], (str, list))

    if isinstance(response_data["detail"], list):
        # Pydantic validation errors
        for error in response_data["detail"]:
            assert "loc" in error
            assert "msg" in error
            assert "type" in error

    # Optional error code for structured errors
    if "error_code" in response_data:
        assert isinstance(response_data["error_code"], str)
        assert response_data["error_code"].startswith("GREMLINS_")


def assert_multimodal_response_structure(response_data: dict, media_type: str):
    """Assert multimodal processing response structure."""
    expected_keys = ["id", "type", "processing_status", "results", "created_at", "processing_time"]
    assert_response_structure(response_data, expected_keys)

    assert response_data["type"] == media_type
    assert response_data["processing_status"] in ["pending", "processing", "completed", "failed"]
    assert isinstance(response_data["results"], dict)
    assert_valid_timestamp(response_data["created_at"])
    assert isinstance(response_data["processing_time"], (int, float))
    assert response_data["processing_time"] >= 0
