"""
Staging Environment Configuration for Integration Tests

This module provides configuration and setup utilities for running
integration tests against a staging environment that closely mirrors
production while maintaining test isolation and safety.

Features:
- Staging database configuration
- Mock external service setup
- Test data management
- Environment isolation
- Performance monitoring
- Security testing setup
"""

import os
import asyncio
import tempfile
from typing import Dict, Any, Optional
from pathlib import Path
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.database.database import Base
from app.core.config import get_settings


class StagingEnvironment:
    """Staging environment manager for integration tests."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._get_default_config()
        self.engine = None
        self.session_factory = None
        self.temp_dirs = []
        self.mock_services = {}
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default staging configuration."""
        return {
            "database_url": "sqlite+aiosqlite:///test_staging.db",
            "test_data_dir": tempfile.mkdtemp(prefix="gremlins_staging_"),
            "mock_external_services": True,
            "enable_performance_monitoring": True,
            "log_level": "INFO",
            "cors_enabled": True,
            "security_testing": True,
            "cleanup_on_exit": True
        }
    
    async def setup(self):
        """Setup staging environment."""
        print("🏗️  Setting up staging environment...")
        
        # Setup database
        await self._setup_database()
        
        # Setup mock services
        await self._setup_mock_services()
        
        # Setup test data directories
        await self._setup_test_directories()
        
        # Setup environment variables
        self._setup_environment_variables()
        
        print("✅ Staging environment ready")
    
    async def _setup_database(self):
        """Setup staging database."""
        print("📊 Setting up staging database...")
        
        # Create async engine
        self.engine = create_async_engine(
            self.config["database_url"],
            echo=False,
            future=True,
            pool_pre_ping=True
        )
        
        # Create session factory
        self.session_factory = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Create all tables
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("✅ Staging database initialized")
    
    async def _setup_mock_services(self):
        """Setup mock external services."""
        if not self.config["mock_external_services"]:
            return
        
        print("🎭 Setting up mock services...")
        
        # Mock LLM services
        self.mock_services["llm"] = {
            "provider": "mock",
            "model": "test-model",
            "responses": {
                "default": "This is a test response from the staging environment."
            }
        }
        
        # Mock vector store
        self.mock_services["vector_store"] = {
            "provider": "mock",
            "collection": "test_collection",
            "documents": []
        }
        
        # Mock external APIs
        self.mock_services["external_apis"] = {
            "search_api": "mock://search.example.com",
            "weather_api": "mock://weather.example.com"
        }
        
        print("✅ Mock services configured")
    
    async def _setup_test_directories(self):
        """Setup test data directories."""
        print("📁 Setting up test directories...")
        
        test_data_dir = Path(self.config["test_data_dir"])
        test_data_dir.mkdir(exist_ok=True)
        self.temp_dirs.append(test_data_dir)
        
        # Create subdirectories
        subdirs = ["documents", "uploads", "logs", "cache"]
        for subdir in subdirs:
            (test_data_dir / subdir).mkdir(exist_ok=True)
        
        print(f"✅ Test directories created at {test_data_dir}")
    
    def _setup_environment_variables(self):
        """Setup environment variables for staging."""
        print("🔧 Setting up environment variables...")
        
        env_vars = {
            "ENVIRONMENT": "staging",
            "DATABASE_URL": self.config["database_url"],
            "TEST_DATA_DIR": self.config["test_data_dir"],
            "LOG_LEVEL": self.config["log_level"],
            "MOCK_EXTERNAL_SERVICES": str(self.config["mock_external_services"]),
            "CORS_ENABLED": str(self.config["cors_enabled"])
        }
        
        for key, value in env_vars.items():
            os.environ[key] = value
        
        print("✅ Environment variables configured")
    
    @asynccontextmanager
    async def get_db_session(self):
        """Get database session for testing."""
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def seed_test_data(self):
        """Seed staging database with test data."""
        print("🌱 Seeding test data...")
        
        async with self.get_db_session() as session:
            # Add test conversations
            from app.services.chat_history import ChatHistoryService
            
            test_conversations = [
                {
                    "title": "Staging Test Conversation 1",
                    "initial_message": "This is a test conversation for staging."
                },
                {
                    "title": "Staging Test Conversation 2", 
                    "initial_message": "Another test conversation for integration testing."
                }
            ]
            
            for conv_data in test_conversations:
                try:
                    await ChatHistoryService.create_conversation(
                        db=session,
                        title=conv_data["title"],
                        initial_message=conv_data["initial_message"]
                    )
                except Exception as e:
                    print(f"⚠️  Warning: Could not seed conversation data: {e}")
            
            # Add test documents
            from app.services.document_service import DocumentService
            
            test_documents = [
                {
                    "title": "Staging Test Document 1",
                    "content": "This is test content for staging integration tests.",
                    "content_type": "text/plain",
                    "tags": ["staging", "test"]
                },
                {
                    "title": "Staging Test Document 2",
                    "content": "More test content for comprehensive testing.",
                    "content_type": "text/plain", 
                    "tags": ["staging", "integration"]
                }
            ]
            
            for doc_data in test_documents:
                try:
                    await DocumentService.create_document(
                        db=session,
                        **doc_data
                    )
                except Exception as e:
                    print(f"⚠️  Warning: Could not seed document data: {e}")
        
        print("✅ Test data seeded")
    
    async def cleanup(self):
        """Cleanup staging environment."""
        if not self.config["cleanup_on_exit"]:
            return
        
        print("🧹 Cleaning up staging environment...")
        
        # Close database connections
        if self.engine:
            await self.engine.dispose()
        
        # Remove temporary directories
        import shutil
        for temp_dir in self.temp_dirs:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                print(f"⚠️  Warning: Could not remove {temp_dir}: {e}")
        
        # Clean up environment variables
        staging_env_vars = [
            "ENVIRONMENT", "DATABASE_URL", "TEST_DATA_DIR",
            "LOG_LEVEL", "MOCK_EXTERNAL_SERVICES", "CORS_ENABLED"
        ]
        
        for var in staging_env_vars:
            if var in os.environ:
                del os.environ[var]
        
        print("✅ Staging environment cleaned up")
    
    def get_test_client_config(self) -> Dict[str, Any]:
        """Get configuration for test client."""
        return {
            "base_url": "http://testserver",
            "timeout": 30.0,
            "follow_redirects": True,
            "headers": {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "GremlinsAI-Integration-Tests/1.0"
            }
        }
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance monitoring configuration."""
        return {
            "enable_monitoring": self.config["enable_performance_monitoring"],
            "response_time_threshold": 5.0,  # seconds
            "memory_threshold": 500,  # MB
            "cpu_threshold": 80,  # percent
            "concurrent_requests": 10
        }
    
    def get_security_config(self) -> Dict[str, Any]:
        """Get security testing configuration."""
        return {
            "enable_security_tests": self.config["security_testing"],
            "test_sql_injection": True,
            "test_xss_protection": True,
            "test_cors_headers": True,
            "test_input_sanitization": True,
            "test_rate_limiting": False  # Disabled for staging
        }


# Global staging environment instance
_staging_env = None


async def get_staging_environment() -> StagingEnvironment:
    """Get or create staging environment instance."""
    global _staging_env
    
    if _staging_env is None:
        _staging_env = StagingEnvironment()
        await _staging_env.setup()
    
    return _staging_env


async def cleanup_staging_environment():
    """Cleanup global staging environment."""
    global _staging_env
    
    if _staging_env is not None:
        await _staging_env.cleanup()
        _staging_env = None


# Context manager for staging environment
@asynccontextmanager
async def staging_environment_context():
    """Context manager for staging environment lifecycle."""
    env = await get_staging_environment()
    try:
        await env.seed_test_data()
        yield env
    finally:
        await cleanup_staging_environment()


# Pytest fixtures for staging environment
def pytest_staging_fixtures():
    """Pytest fixtures for staging environment."""
    import pytest
    
    @pytest.fixture(scope="session")
    async def staging_env():
        """Staging environment fixture."""
        async with staging_environment_context() as env:
            yield env
    
    @pytest.fixture
    async def staging_db_session(staging_env):
        """Staging database session fixture."""
        async with staging_env.get_db_session() as session:
            yield session
    
    @pytest.fixture
    def staging_test_config(staging_env):
        """Staging test configuration fixture."""
        return {
            "client_config": staging_env.get_test_client_config(),
            "performance_config": staging_env.get_performance_config(),
            "security_config": staging_env.get_security_config()
        }
    
    return {
        "staging_env": staging_env,
        "staging_db_session": staging_db_session,
        "staging_test_config": staging_test_config
    }
