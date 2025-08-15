# GremlinsAI Backend Test Suite

Comprehensive testing suite for the GremlinsAI backend system, implementing the testing strategy outlined in `GremlinsTest.txt`.

## 🎯 Overview

This test suite provides comprehensive coverage of the GremlinsAI backend with **64+ tests** across multiple categories:

- **Unit Tests**: Individual function and component testing with mocked dependencies
- **Integration Tests**: API endpoint and service interaction testing
- **End-to-End Tests**: Complete user workflow testing
- **Performance Tests**: Load testing and performance validation

## 📁 Test Structure

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                 # Shared fixtures and configuration
├── README.md                   # This documentation
├── unit/                       # Unit tests
│   ├── __init__.py
│   ├── test_core_agent.py      # Core agent logic tests
│   ├── test_database_models.py # Database model tests
│   └── test_services.py        # Service layer tests
├── integration/                # Integration tests
│   ├── __init__.py
│   ├── test_agent_endpoints.py # Agent API endpoint tests
│   └── test_chat_history_endpoints.py # Chat history API tests
├── e2e/                        # End-to-end tests
│   ├── __init__.py
│   └── test_conversation_workflows.py # Complete workflow tests
└── performance/                # Performance tests
    ├── __init__.py
    └── test_endpoint_performance.py # Performance and load tests
```

## 🚀 Quick Start

### Prerequisites

1. **Python 3.11+** installed
2. **Virtual environment** activated
3. **Dependencies** installed: `pip install -r requirements.txt`
4. **Test dependencies** available (pytest, pytest-asyncio, etc.)

### Running Tests

#### Using the Test Runner (Recommended)

```bash
# Run all tests
python run_tests.py

# Run specific test categories
python run_tests.py --unit           # Unit tests only
python run_tests.py --integration    # Integration tests only
python run_tests.py --e2e           # End-to-end tests only
python run_tests.py --performance   # Performance tests only
python run_tests.py --fast          # Fast tests (exclude slow/performance)

# With options
python run_tests.py --coverage      # Generate coverage report
python run_tests.py --verbose       # Verbose output
```

#### Using pytest directly

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit                      # Unit tests
pytest -m integration              # Integration tests
pytest -m e2e                      # End-to-end tests
pytest -m performance              # Performance tests

# Run specific test files
pytest tests/unit/test_core_agent.py
pytest tests/integration/test_agent_endpoints.py

# With coverage
pytest --cov=app --cov-report=html
```

## 🧪 Test Categories

### Unit Tests (`-m unit`)

Test individual functions and components in isolation with all external dependencies mocked.

**Coverage:**
- Core agent logic and state management
- Database model validation and relationships
- Service layer business logic
- Utility functions and helpers
- Pydantic schema validation

**Example:**
```bash
pytest tests/unit/ -v
```

### Integration Tests (`-m integration`)

Test API endpoints and service interactions with mocked external services but real database operations.

**Coverage:**
- All API endpoints in `/api/v1/`
- Request/response validation
- Database integration
- Error handling
- Security validation

**Example:**
```bash
pytest tests/integration/ -v
```

### End-to-End Tests (`-m e2e`)

Test complete user workflows from start to finish, simulating real user interactions.

**Coverage:**
- Complete conversation workflows
- Multi-agent collaboration scenarios
- Document upload and RAG workflows
- Context-aware conversations
- Error recovery scenarios

**Example:**
```bash
pytest tests/e2e/ -v
```

### Performance Tests (`-m performance`)

Test system performance, load handling, and resource usage.

**Coverage:**
- Response time validation
- Concurrent request handling
- Memory usage monitoring
- Load testing scenarios
- Scalability validation

**Example:**
```bash
pytest tests/performance/ -v
```

## ⚙️ Configuration

### Test Environment

Tests use a separate test environment configured via `.env.test`:

```bash
# Test Database
DATABASE_URL=sqlite:///./data/test_gremlinsai.db
TESTING=true

# Mock External Services
DISABLE_EXTERNAL_APIS=true
MOCK_LLM_RESPONSES=true
MOCK_SEARCH_RESULTS=true

# Test Timeouts
TEST_TIMEOUT=30
AGENT_RESPONSE_TIMEOUT=10
```

### pytest Configuration

Test behavior is configured in `pytest.ini`:

```ini
[tool:pytest]
testpaths = tests
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    performance: Performance tests
    slow: Slow-running tests
```

## 🎭 Mocking Strategy

### External Services

All external services are mocked by default:

- **LLM APIs**: OpenAI, Anthropic calls return mock responses
- **Search APIs**: DuckDuckGo search returns mock results
- **Vector Store**: Qdrant operations are mocked
- **Multi-Agent**: CrewAI workflows return mock results

### Database

- **Unit Tests**: Database operations are fully mocked
- **Integration Tests**: Real database operations with test database
- **E2E Tests**: Real database operations with cleanup

## 📊 Coverage Reports

Generate coverage reports to track test coverage:

```bash
# Terminal report
pytest --cov=app --cov-report=term-missing

# HTML report
pytest --cov=app --cov-report=html
# Open htmlcov/index.html in browser

# XML report (for CI/CD)
pytest --cov=app --cov-report=xml
```

## 🔧 Writing New Tests

### Test File Naming

- Unit tests: `test_*.py` in `tests/unit/`
- Integration tests: `test_*_endpoints.py` in `tests/integration/`
- E2E tests: `test_*_workflows.py` in `tests/e2e/`
- Performance tests: `test_*_performance.py` in `tests/performance/`

### Test Function Naming

Use descriptive names that explain what is being tested:

```python
def test_agent_invoke_with_valid_input():
    """Test agent invocation with valid input."""
    pass

def test_conversation_creation_with_missing_title():
    """Test conversation creation when title is missing."""
    pass
```

### Test Markers

Mark tests with appropriate categories:

```python
@pytest.mark.unit
def test_unit_function():
    pass

@pytest.mark.integration
def test_api_endpoint():
    pass

@pytest.mark.e2e
def test_complete_workflow():
    pass

@pytest.mark.performance
def test_response_time():
    pass

@pytest.mark.slow
def test_long_running_operation():
    pass
```

### Using Fixtures

Leverage shared fixtures from `conftest.py`:

```python
def test_with_test_client(test_client):
    """Test using the FastAPI test client."""
    response = test_client.get("/api/v1/health")
    assert response.status_code == 200

async def test_with_db_session(test_db_session):
    """Test with database session."""
    # Use test_db_session for database operations
    pass
```

## 🚨 Troubleshooting

### Common Issues

1. **Import Errors**: Ensure `PYTHONPATH` includes project root
2. **Database Errors**: Check test database permissions and path
3. **Async Test Issues**: Use `pytest-asyncio` and `@pytest.mark.asyncio`
4. **Mock Issues**: Verify mock patches target the correct import paths

### Debug Mode

Run tests with verbose output and no capture:

```bash
pytest -v -s --tb=long
```

### Test Data Cleanup

Tests automatically clean up test data, but you can manually clean:

```bash
rm -f data/test_gremlinsai.db
rm -rf data/test_multimodal/
```

## 📈 Continuous Integration

### GitHub Actions Example

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python run_tests.py --coverage
```

## 🎯 Test Goals

This test suite aims to achieve:

- **✅ 64+ comprehensive tests** covering all major functionality
- **✅ 80%+ code coverage** across the application
- **✅ Fast feedback** with tests completing in under 2 minutes
- **✅ Reliable results** with consistent, deterministic test outcomes
- **✅ Easy maintenance** with clear structure and documentation

## 📞 Support

For questions about the test suite:

1. Check this README for common patterns
2. Review existing tests for examples
3. Check `GremlinsTest.txt` for testing strategy details
4. Open an issue for test-related bugs or improvements
