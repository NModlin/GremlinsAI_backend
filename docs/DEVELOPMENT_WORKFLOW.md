# GremlinsAI Development Workflow Guide v10.0.0

## Table of Contents

1. [Development Environment Setup](#development-environment-setup)
2. [Code Standards & Guidelines](#code-standards--guidelines)
3. [Git Workflow](#git-workflow)
4. [Testing Strategy](#testing-strategy)
5. [Code Review Process](#code-review-process)
6. [Continuous Integration](#continuous-integration)
7. [Release Process](#release-process)
8. [Contributing Guidelines](#contributing-guidelines)

## Development Environment Setup

### Prerequisites
```bash
# Required software
- Python 3.11+
- Git 2.30+
- Docker 20.10+
- Docker Compose 2.0+
- Node.js 18+ (for frontend development)
```

### Initial Setup
```bash
# 1. Clone repository
git clone https://github.com/your-org/GremlinsAI_backend.git
cd GremlinsAI_backend

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or .venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Install pre-commit hooks
pre-commit install

# 5. Copy environment configuration
cp .env.example .env.development
```

### IDE Configuration

#### VS Code Settings
```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "./.venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests/"],
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    ".pytest_cache": true,
    ".coverage": true
  }
}
```

#### Recommended Extensions
```json
// .vscode/extensions.json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.flake8",
    "ms-python.mypy-type-checker",
    "ms-python.black-formatter",
    "ms-python.isort",
    "bradlc.vscode-tailwindcss",
    "ms-vscode.vscode-json",
    "redhat.vscode-yaml",
    "ms-vscode.vscode-typescript-next"
  ]
}
```

## Code Standards & Guidelines

### Python Code Style

#### Black Formatting
```bash
# Format all Python files
black app/ tests/

# Check formatting without changes
black --check app/ tests/
```

#### Import Organization (isort)
```python
# Standard library imports
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

# Third-party imports
import fastapi
import sqlalchemy
from pydantic import BaseModel

# Local application imports
from app.core.config import settings
from app.database.models import User
from app.services.agent_service import AgentService
```

#### Type Hints
```python
# Always use type hints
from typing import Dict, List, Optional, Union, Any

async def process_query(
    query: str,
    context: Optional[Dict[str, Any]] = None,
    use_multi_agent: bool = False
) -> Dict[str, Union[str, int, float]]:
    """Process user query with optional context."""
    pass

# Use Pydantic models for complex types
from pydantic import BaseModel

class QueryRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = None
    use_multi_agent: bool = False
    save_conversation: bool = True
```

#### Documentation Standards
```python
def complex_function(param1: str, param2: int) -> Dict[str, Any]:
    """
    Brief description of what the function does.
    
    Args:
        param1: Description of first parameter
        param2: Description of second parameter
        
    Returns:
        Dictionary containing the result with keys:
        - 'status': Operation status
        - 'data': Processed data
        - 'metadata': Additional information
        
    Raises:
        ValueError: When param1 is empty
        RuntimeError: When processing fails
        
    Example:
        >>> result = complex_function("test", 42)
        >>> print(result['status'])
        'success'
    """
    pass
```

### API Design Standards

#### Endpoint Naming
```python
# Good: RESTful, descriptive
POST /api/v1/conversations
GET /api/v1/conversations/{conversation_id}
PUT /api/v1/conversations/{conversation_id}
DELETE /api/v1/conversations/{conversation_id}

# Good: Action-based for non-CRUD operations
POST /api/v1/agent/invoke
POST /api/v1/multi-agent/workflow
POST /api/analytics/process

# Avoid: Unclear or non-standard
GET /api/v1/get_conversation  # Bad
POST /api/v1/conversation_create  # Bad
```

#### Response Format
```python
# Standard success response
{
  "status": "success",
  "data": {...},
  "metadata": {
    "timestamp": "2024-01-15T10:00:00Z",
    "execution_time": 1.23,
    "version": "v10.0.0"
  }
}

# Standard error response
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Input validation failed",
    "details": {
      "field": "query",
      "reason": "Field is required"
    },
    "timestamp": "2024-01-15T10:00:00Z",
    "request_id": "uuid"
  }
}
```

### Database Standards

#### Model Definitions
```python
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Conversation(Base):
    """Conversation model with proper naming and constraints."""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True, nullable=False)
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, title='{self.title}')>"
```

#### Migration Standards
```python
# Alembic migration example
"""Add analytics metrics table

Revision ID: abc123
Revises: def456
Create Date: 2024-01-15 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

def upgrade():
    """Add analytics_metrics table."""
    op.create_table(
        'analytics_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('metric_type', sa.String(50), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_analytics_metrics_type_timestamp', 'metric_type', 'timestamp')
    )

def downgrade():
    """Remove analytics_metrics table."""
    op.drop_table('analytics_metrics')
```

## Git Workflow

### Branch Strategy
```bash
# Main branches
main          # Production-ready code
develop       # Integration branch for features

# Feature branches
feature/T4.1-multi-agent-system
feature/T4.2-multimodal-processing
feature/T4.3-monitoring-integration

# Release branches
release/v10.0.0

# Hotfix branches
hotfix/critical-security-fix
```

### Commit Message Format
```bash
# Format: <type>(<scope>): <description>
# 
# <body>
# 
# <footer>

# Examples:
feat(api): add real-time collaboration endpoints

Implement WebSocket-based collaboration with operational transform
for conflict resolution and sub-200ms latency.

- Add collaboration session management
- Implement operational transform algorithm
- Add WebSocket connection handling
- Include comprehensive integration tests

Closes #123

fix(llm): resolve memory leak in model loading

The Ollama model loading was not properly releasing GPU memory
when models were unloaded. Added explicit cleanup and verification.

Fixes #456

docs(api): update authentication examples

Add OAuth 2.0 examples and API key generation instructions
for the complete API reference documentation.
```

### Commit Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `perf`: Performance improvements
- `ci`: CI/CD changes

### Pull Request Process
```bash
# 1. Create feature branch
git checkout -b feature/new-analytics-endpoint

# 2. Make changes and commit
git add .
git commit -m "feat(analytics): add query trend analysis endpoint"

# 3. Push branch
git push origin feature/new-analytics-endpoint

# 4. Create pull request with template
```

#### Pull Request Template
```markdown
## Description
Brief description of changes and motivation.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Performance impact assessed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] No breaking changes (or properly documented)

## Screenshots (if applicable)
Add screenshots for UI changes.

## Related Issues
Closes #123
References #456
```

## Testing Strategy

### Test Structure
```
tests/
├── unit/                 # Unit tests (fast, isolated)
│   ├── test_agents.py
│   ├── test_services.py
│   └── test_utils.py
├── integration/          # Integration tests (slower, with dependencies)
│   ├── test_api_endpoints.py
│   ├── test_database.py
│   └── test_external_services.py
├── e2e/                  # End-to-end tests (full workflow)
│   ├── test_user_workflows.py
│   └── test_multi_agent_scenarios.py
├── performance/          # Performance and load tests
│   ├── test_response_times.py
│   └── test_concurrent_users.py
└── fixtures/             # Test data and fixtures
    ├── sample_data.json
    └── mock_responses.py
```

### Test Standards
```python
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

class TestAgentService:
    """Test suite for agent service functionality."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client for testing."""
        mock_client = AsyncMock()
        mock_client.generate.return_value = "Test response"
        return mock_client
    
    @pytest.mark.asyncio
    async def test_agent_invoke_success(self, mock_llm_client):
        """Test successful agent invocation."""
        # Arrange
        service = AgentService(llm_client=mock_llm_client)
        query = "What is AI?"
        
        # Act
        result = await service.invoke(query)
        
        # Assert
        assert result.output == "Test response"
        assert result.execution_time > 0
        mock_llm_client.generate.assert_called_once_with(query)
    
    @pytest.mark.asyncio
    async def test_agent_invoke_with_context(self, mock_llm_client):
        """Test agent invocation with conversation context."""
        # Test implementation
        pass
    
    def test_agent_configuration_validation(self):
        """Test agent configuration validation."""
        # Test implementation
        pass
```

### Running Tests
```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# Run with coverage
pytest --cov=app --cov-report=html --cov-report=term

# Run performance tests
pytest tests/performance/ -v

# Run tests matching pattern
pytest -k "test_agent" -v

# Run tests with specific markers
pytest -m "slow" -v
pytest -m "not slow" -v
```

### Test Configuration
```python
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --strict-markers
    --disable-warnings
    --tb=short
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    e2e: marks tests as end-to-end tests
    performance: marks tests as performance tests
```

## Code Review Process

### Review Checklist
```markdown
## Code Quality
- [ ] Code follows established style guidelines
- [ ] Functions and classes are well-documented
- [ ] Complex logic is commented
- [ ] No obvious performance issues
- [ ] Error handling is appropriate

## Testing
- [ ] New code has adequate test coverage
- [ ] Tests are meaningful and test the right things
- [ ] Tests pass consistently
- [ ] Edge cases are covered

## Security
- [ ] No sensitive data in code or logs
- [ ] Input validation is present
- [ ] Authentication/authorization is correct
- [ ] No SQL injection vulnerabilities

## Architecture
- [ ] Changes align with system architecture
- [ ] No unnecessary dependencies added
- [ ] Interfaces are clean and well-defined
- [ ] Database changes are properly migrated
```

### Review Guidelines
1. **Be Constructive**: Provide specific, actionable feedback
2. **Focus on Code**: Review the code, not the person
3. **Explain Why**: Provide reasoning for suggestions
4. **Suggest Alternatives**: Offer better approaches when possible
5. **Approve When Ready**: Don't hold up good code for minor issues

## Continuous Integration

### GitHub Actions Workflow
```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.11, 3.12]
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run linting
      run: |
        flake8 app/ tests/
        black --check app/ tests/
        mypy app/
    
    - name: Run tests
      run: |
        pytest --cov=app --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

## Release Process

### Version Management
```bash
# Semantic versioning: MAJOR.MINOR.PATCH
# v10.0.0 - Major release with breaking changes
# v10.1.0 - Minor release with new features
# v10.1.1 - Patch release with bug fixes

# Update version in multiple files
# app/__init__.py
__version__ = "10.1.0"

# pyproject.toml
[tool.poetry]
version = "10.1.0"
```

### Release Checklist
```markdown
## Pre-Release
- [ ] All tests pass
- [ ] Documentation updated
- [ ] Version numbers updated
- [ ] Changelog updated
- [ ] Security review completed
- [ ] Performance benchmarks run

## Release
- [ ] Create release branch
- [ ] Final testing in staging
- [ ] Create GitHub release
- [ ] Deploy to production
- [ ] Monitor deployment

## Post-Release
- [ ] Verify production deployment
- [ ] Update documentation site
- [ ] Announce release
- [ ] Monitor for issues
```

## Contributing Guidelines

### Getting Started
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Code of Conduct
- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Follow the established guidelines
- Report issues appropriately

This development workflow ensures high code quality, comprehensive testing, and smooth collaboration across the GremlinsAI development team.
