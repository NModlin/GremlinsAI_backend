# tests/conftest.py
"""
Pytest configuration and shared fixtures for GremlinsAI tests.
Comprehensive testing framework with real service integration.
"""

import pytest
import asyncio
import sys
import os
import tempfile
import shutil
import time
import httpx
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import patch

# Add the app directory to the Python path
app_dir = Path(__file__).parent.parent / "app"
sys.path.insert(0, str(app_dir))

# Add the root directory to the Python path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Import after path setup
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False

try:
    import weaviate
    WEAVIATE_AVAILABLE = True
except ImportError:
    WEAVIATE_AVAILABLE = False


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def docker_client():
    """Get Docker client for container management."""
    if not DOCKER_AVAILABLE:
        pytest.skip("Docker not available")

    try:
        client = docker.from_env()
        client.ping()
        return client
    except Exception as e:
        pytest.skip(f"Docker not available: {e}")


@pytest.fixture(scope="session")
def test_weaviate_container(docker_client):
    """Start a test Weaviate container for integration tests."""
    if not DOCKER_AVAILABLE:
        pytest.skip("Docker not available for Weaviate container")

    container_name = "test-weaviate-gremlins"

    # Clean up any existing container
    try:
        existing = docker_client.containers.get(container_name)
        existing.stop()
        existing.remove()
    except docker.errors.NotFound:
        pass

    # Start Weaviate container
    container = docker_client.containers.run(
        "semitechnologies/weaviate:1.24.0",
        name=container_name,
        ports={"8080/tcp": 8080},
        environment={
            "QUERY_DEFAULTS_LIMIT": "25",
            "AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED": "true",
            "PERSISTENCE_DATA_PATH": "/var/lib/weaviate",
            "DEFAULT_VECTORIZER_MODULE": "none",
            "ENABLE_MODULES": "text2vec-openai,text2vec-cohere,text2vec-huggingface,ref2vec-centroid,generative-openai,qna-openai",
            "CLUSTER_HOSTNAME": "node1"
        },
        detach=True,
        remove=True
    )

    # Wait for Weaviate to be ready
    max_retries = 30
    for i in range(max_retries):
        try:
            response = httpx.get("http://localhost:8080/v1/meta", timeout=5.0)
            if response.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(2)
    else:
        container.stop()
        pytest.fail("Weaviate container failed to start")

    yield container

    # Cleanup
    try:
        container.stop()
    except Exception:
        pass


@pytest.fixture(scope="session")
def test_database_url():
    """Create a temporary SQLite database for testing."""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test.db"
    database_url = f"sqlite+aiosqlite:///{db_path}"

    yield database_url

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="session")
async def test_db_engine(test_database_url):
    """Create test database engine."""
    engine = create_async_engine(
        test_database_url,
        echo=False,
        future=True
    )

    # Create tables
    from app.database.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def test_db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = sessionmaker(
        test_db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables and configurations."""
    # Set test environment variables
    test_env = {
        "TESTING": "true",
        "LOG_LEVEL": "DEBUG",
        "DATABASE_URL": "sqlite+aiosqlite:///./test.db",
        "WEAVIATE_URL": "http://localhost:8080",
        "OLLAMA_BASE_URL": "http://localhost:11434",
        "OLLAMA_MODEL": "llama3.2:3b",
        "REDIS_URL": "redis://localhost:6379",
        "LLM_CACHE_TTL": "300",  # 5 minutes for tests
        "OPENAI_API_KEY": "test-key-not-used",
        "ANTHROPIC_API_KEY": "test-key-not-used"
    }

    # Store original values
    original_env = {}
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    yield

    # Restore original environment
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest.fixture
def test_client():
    """Create FastAPI test client."""
    from app.main import app
    from app.database.database import get_db

    # Override database dependency for testing
    async def override_get_db():
        # This will be overridden in specific tests
        pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
async def async_test_client():
    """Create async HTTP client for testing."""
    from app.main import app

    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def sample_document_content():
    """Sample document content for testing."""
    return """
    # GremlinsAI Documentation

    GremlinsAI is a production-ready AI agent system that provides:

    ## Features
    - Intelligent document processing
    - Multi-modal content understanding
    - Real-time collaboration
    - Advanced RAG capabilities

    ## Architecture
    The system uses a microservices architecture with:
    - FastAPI backend
    - Weaviate vector database
    - Redis caching layer
    - Ollama for local LLM inference

    ## Getting Started
    1. Install dependencies
    2. Configure environment variables
    3. Start the services
    4. Upload your first document

    This system can handle complex queries and provide accurate responses
    based on your document corpus.
    """


@pytest.fixture
def sample_test_queries():
    """Sample queries for testing RAG functionality."""
    return [
        "What is GremlinsAI?",
        "How does the architecture work?",
        "What are the main features?",
        "How do I get started?",
        "What databases does it use?"
    ]


@pytest.fixture
def mock_ollama_service():
    """Mock Ollama service for tests that don't need real LLM."""
    from unittest.mock import AsyncMock, Mock

    mock_response = Mock()
    mock_response.content = "This is a test response from the mocked LLM service."

    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = mock_response

    with patch('app.core.production_llm_manager.ChatOllama', return_value=mock_llm):
        yield mock_llm


@pytest.fixture
def performance_test_config():
    """Configuration for performance tests."""
    return {
        "concurrent_users": 10,
        "requests_per_user": 5,
        "max_response_time": 2.0,  # seconds
        "success_rate_threshold": 0.95,  # 95%
        "memory_limit_mb": 512,
        "cpu_limit_percent": 80
    }
