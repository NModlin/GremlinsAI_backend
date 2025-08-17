"""
Global pytest configuration for GremlinsAI Backend Tests

This module provides shared fixtures and configuration for all test types:
- Unit tests
- Integration tests  
- End-to-end tests
- Performance tests

Features:
- Database setup and teardown
- Mock service configuration
- Test environment isolation
- Async test support
- Staging environment setup
"""

import pytest
import asyncio
import os
import tempfile
import shutil
from typing import AsyncGenerator, Generator
from unittest.mock import patch, Mock, MagicMock

# Async test support
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_data_dir():
    """Create temporary directory for test data."""
    temp_dir = tempfile.mkdtemp(prefix="gremlinsai_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="session")
def test_config():
    """Test configuration settings."""
    return {
        "database_url": "sqlite+aiosqlite:///:memory:",
        "test_mode": True,
        "log_level": "INFO",
        "mock_external_services": True,
        "staging_environment": True
    }


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider for testing."""
    mock_llm = Mock()
    mock_llm.invoke.return_value = "Test LLM response"
    mock_llm.stream.return_value = ["Test", " streaming", " response"]
    return mock_llm


@pytest.fixture
def mock_vector_store():
    """Mock vector store for testing."""
    mock_store = Mock()
    mock_store.search.return_value = []
    mock_store.add_documents.return_value = True
    mock_store.delete_documents.return_value = True
    return mock_store


@pytest.fixture
def mock_weaviate_client():
    """Mock Weaviate client for testing."""
    client = Mock()
    
    # Mock collections
    client.collections = Mock()
    client.collections.get = Mock()
    
    # Create mock collection
    collection = Mock()
    client.collections.get.return_value = collection
    
    # Mock query methods
    collection.query = Mock()
    collection.query.near_text = Mock()
    collection.query.bm25 = Mock()
    collection.query.hybrid = Mock()
    
    # Mock query results
    mock_result = Mock()
    mock_result.objects = []
    
    collection.query.near_text.return_value = mock_result
    collection.query.bm25.return_value = mock_result
    collection.query.hybrid.return_value = mock_result
    
    return client


@pytest.fixture
def mock_external_services():
    """Mock all external services for integration testing."""
    with patch('app.core.agent.agent_graph_app') as mock_agent, \
         patch('app.core.multi_agent.multi_agent_orchestrator') as mock_multi_agent, \
         patch('app.core.rag_system.rag_system') as mock_rag, \
         patch('app.core.vector_store.vector_store') as mock_vector_store, \
         patch('app.core.orchestrator.enhanced_orchestrator') as mock_orchestrator:
        
        # Configure mock agent
        mock_agent.stream.return_value = [
            {
                'agent': {
                    'agent_outcome': {
                        'return_values': {'output': 'Test agent response'}
                    }
                }
            }
        ]
        
        # Configure mock multi-agent
        mock_multi_agent.execute_simple_query.return_value = {
            'result': 'Test multi-agent response',
            'agents_used': ['researcher'],
            'task_type': 'simple_research',
            'sources': []
        }
        
        mock_multi_agent.get_agent_capabilities.return_value = {
            'researcher': {
                'role': 'Research Specialist',
                'capabilities': 'Information gathering and analysis',
                'tools': 'web_search, document_analysis'
            },
            'analyst': {
                'role': 'Data Analyst', 
                'capabilities': 'Data analysis and insights',
                'tools': 'statistical_analysis, visualization'
            }
        }
        
        # Configure mock RAG
        mock_rag.query.return_value = {
            'answer': 'Test RAG response',
            'sources': [],
            'confidence': 0.85
        }
        
        # Configure mock vector store
        mock_vector_store.search.return_value = []
        
        # Configure mock orchestrator
        mock_task_result = Mock()
        mock_task_result.task_id = "test-task-123"
        mock_task_result.status = "COMPLETED"
        mock_task_result.result = "Test orchestrator result"
        mock_task_result.execution_time = 1.5
        mock_task_result.error = None
        
        mock_orchestrator.execute_task.return_value = mock_task_result
        mock_orchestrator.get_health_status.return_value = {
            "status": "healthy",
            "active_tasks": 0,
            "completed_tasks": 10,
            "failed_tasks": 0,
            "uptime": 3600.0
        }
        
        yield {
            'agent': mock_agent,
            'multi_agent': mock_multi_agent,
            'rag': mock_rag,
            'vector_store': mock_vector_store,
            'orchestrator': mock_orchestrator
        }


@pytest.fixture
def mock_database_services():
    """Mock database-related services."""
    with patch('app.services.chat_history.ChatHistoryService') as mock_chat_service, \
         patch('app.services.document_service.DocumentService') as mock_doc_service, \
         patch('app.services.agent_memory.AgentMemoryService') as mock_memory_service:
        
        # Configure mock chat service
        mock_conversation = Mock()
        mock_conversation.id = "test-conv-123"
        mock_conversation.title = "Test Conversation"
        mock_conversation.is_active = True
        
        mock_message = Mock()
        mock_message.id = "test-msg-123"
        mock_message.conversation_id = "test-conv-123"
        mock_message.role = "user"
        mock_message.content = "Test message"
        
        mock_chat_service.create_conversation.return_value = mock_conversation
        mock_chat_service.add_message.return_value = mock_message
        mock_chat_service.get_conversation.return_value = mock_conversation
        mock_chat_service.get_messages.return_value = [mock_message]
        
        # Configure mock document service
        mock_document = Mock()
        mock_document.id = "test-doc-123"
        mock_document.title = "Test Document"
        mock_document.content = "Test content"
        mock_document.is_active = True
        
        mock_doc_service.create_document.return_value = mock_document
        mock_doc_service.get_document.return_value = mock_document
        mock_doc_service.list_documents.return_value = ([mock_document], 1)
        
        # Configure mock memory service
        mock_memory_service.create_agent_context_prompt.return_value = "Test context prompt"
        
        yield {
            'chat_service': mock_chat_service,
            'document_service': mock_doc_service,
            'memory_service': mock_memory_service
        }


@pytest.fixture
def staging_environment():
    """Setup staging environment configuration."""
    staging_config = {
        "environment": "staging",
        "database_url": "sqlite+aiosqlite:///test_staging.db",
        "redis_url": "redis://localhost:6379/1",
        "log_level": "DEBUG",
        "enable_cors": True,
        "mock_external_apis": True
    }
    
    # Set environment variables
    original_env = {}
    for key, value in staging_config.items():
        original_env[key] = os.environ.get(key.upper())
        os.environ[key.upper()] = str(value)
    
    yield staging_config
    
    # Restore original environment
    for key, value in original_env.items():
        if value is not None:
            os.environ[key.upper()] = value
        elif key.upper() in os.environ:
            del os.environ[key.upper()]


@pytest.fixture
def performance_monitoring():
    """Setup performance monitoring for tests."""
    import time
    import psutil
    import threading
    
    metrics = {
        'start_time': None,
        'end_time': None,
        'memory_usage': [],
        'cpu_usage': []
    }
    
    def monitor_resources():
        """Monitor system resources during test execution."""
        process = psutil.Process()
        while metrics['start_time'] and not metrics['end_time']:
            try:
                metrics['memory_usage'].append(process.memory_info().rss / 1024 / 1024)  # MB
                metrics['cpu_usage'].append(process.cpu_percent())
                time.sleep(0.1)
            except:
                break
    
    # Start monitoring
    metrics['start_time'] = time.time()
    monitor_thread = threading.Thread(target=monitor_resources, daemon=True)
    monitor_thread.start()
    
    yield metrics
    
    # Stop monitoring
    metrics['end_time'] = time.time()
    
    # Calculate summary statistics
    if metrics['memory_usage']:
        metrics['avg_memory_mb'] = sum(metrics['memory_usage']) / len(metrics['memory_usage'])
        metrics['max_memory_mb'] = max(metrics['memory_usage'])
    
    if metrics['cpu_usage']:
        metrics['avg_cpu_percent'] = sum(metrics['cpu_usage']) / len(metrics['cpu_usage'])
        metrics['max_cpu_percent'] = max(metrics['cpu_usage'])
    
    metrics['total_time_seconds'] = metrics['end_time'] - metrics['start_time']


# Test markers for different test categories
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as an end-to-end test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "staging: mark test as requiring staging environment"
    )


# Async test configuration
@pytest.fixture(scope="session")
def asyncio_mode():
    """Configure asyncio mode for pytest-asyncio."""
    return "auto"


# Test data fixtures
@pytest.fixture
def sample_conversation_data():
    """Sample conversation data for testing."""
    return {
        "title": "Test Conversation",
        "initial_message": "Hello, this is a test conversation."
    }


@pytest.fixture
def sample_document_data():
    """Sample document data for testing."""
    return {
        "title": "Test Document",
        "content": "This is a test document for integration testing.",
        "content_type": "text/plain",
        "tags": ["test", "integration"]
    }


@pytest.fixture
def sample_agent_request():
    """Sample agent request data for testing."""
    return {
        "input": "What is artificial intelligence?",
        "save_conversation": True
    }


@pytest.fixture
def sample_multi_agent_request():
    """Sample multi-agent request data for testing."""
    return {
        "input": "Research the latest developments in quantum computing",
        "workflow_type": "simple_research",
        "save_conversation": True
    }
