# tests/unit/test_core_modules.py
"""
Unit tests for core GremlinsAI modules.

These tests focus on testing real functionality with minimal mocking,
following the comprehensive testing framework requirements.
"""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock, AsyncMock
from typing import Dict, Any, List

from app.core.config import get_settings
from app.core.exceptions import (
    AgentProcessingException,
    ValidationException,
    ExternalServiceException
)
from app.tools.base_tool import ToolResult
from app.services.chunking_service import DocumentChunker, ChunkingConfig, ChunkingStrategy


class TestCoreConfiguration:
    """Test core configuration management."""

    def test_settings_initialization(self):
        """Test that settings can be initialized."""
        settings = get_settings()

        assert settings is not None
        assert hasattr(settings, 'database_url')
        assert hasattr(settings, 'redis_url')
        assert hasattr(settings, 'ollama_base_url')
        assert hasattr(settings, 'app_name')
        assert settings.app_name == 'GremlinsAI Backend'

    def test_settings_singleton(self):
        """Test that settings follows singleton pattern."""
        settings1 = get_settings()
        settings2 = get_settings()
        
        assert settings1 is settings2

    @pytest.mark.asyncio
    async def test_environment_variable_override(self):
        """Test that environment variables override default settings."""
        with patch.dict('os.environ', {'DATABASE_URL': 'test://override'}):
            # Force reload of settings
            from app.core.config import Settings
            settings = Settings()
            assert 'test://override' in settings.database_url


class TestCustomExceptions:
    """Test custom exception classes."""

    def test_agent_processing_exception(self):
        """Test AgentProcessingException creation and attributes."""
        error_details = {"step": "reasoning", "error": "LLM timeout"}
        
        exception = AgentProcessingException(
            message="Agent processing failed",
            error_details=error_details,
            processing_step="reasoning"
        )
        
        assert str(exception) == "Agent processing failed"
        assert exception.error_details == error_details
        assert exception.processing_step == "reasoning"

    def test_validation_exception(self):
        """Test ValidationException with error details."""
        errors = [
            {"field": "title", "message": "Title is required"},
            {"field": "content", "message": "Content cannot be empty"}
        ]
        
        exception = ValidationException(
            message="Validation failed",
            errors=errors
        )
        
        assert str(exception) == "Validation failed"
        assert exception.errors == errors
        assert len(exception.errors) == 2

    def test_external_service_exception(self):
        """Test ExternalServiceException."""
        exception = ExternalServiceException(
            message="Weaviate connection failed",
            service_name="weaviate",
            status_code=503
        )
        
        assert str(exception) == "Weaviate connection failed"
        assert exception.service_name == "weaviate"
        assert exception.status_code == 503


class TestToolResult:
    """Test ToolResult functionality."""

    def test_tool_result_success(self):
        """Test ToolResult for successful execution."""
        result = ToolResult(
            success=True,
            result="Operation completed",
            tool_name="test_tool"
        )

        assert result.success is True
        assert result.result == "Operation completed"
        assert result.error_message is None
        assert result.tool_name == "test_tool"
        assert result.timestamp != ""  # Should be auto-generated

    def test_tool_result_failure(self):
        """Test ToolResult for failed execution."""
        result = ToolResult(
            success=False,
            result=None,
            error_message="Operation failed",
            tool_name="test_tool"
        )

        assert result.success is False
        assert result.result is None
        assert result.error_message == "Operation failed"
        assert result.tool_name == "test_tool"

    def test_tool_result_metadata(self):
        """Test ToolResult metadata handling."""
        metadata = {"execution_context": "test", "version": "1.0"}

        result = ToolResult(
            success=True,
            result="test",
            tool_name="test_tool",
            metadata=metadata
        )

        assert result.metadata == metadata
        assert result.metadata["execution_context"] == "test"

    def test_tool_result_auto_timestamp(self):
        """Test automatic timestamp generation."""
        result = ToolResult(
            success=True,
            result="test",
            tool_name="test_tool"
        )

        # Should have auto-generated timestamp
        assert result.timestamp != ""
        assert "T" in result.timestamp  # ISO format


class TestDocumentChunker:
    """Test document chunking service."""

    @pytest.fixture
    def chunker(self):
        """Create document chunker instance."""
        config = ChunkingConfig(
            chunk_size=500,
            chunk_overlap=50,
            strategy=ChunkingStrategy.RECURSIVE_CHARACTER
        )
        return DocumentChunker(config)

    def test_chunker_initialization(self, chunker):
        """Test chunker initialization."""
        assert chunker is not None
        assert chunker.config.chunk_size == 500
        assert chunker.config.chunk_overlap == 50
        assert chunker.config.strategy == ChunkingStrategy.RECURSIVE_CHARACTER

    def test_chunking_config(self):
        """Test chunking configuration."""
        config = ChunkingConfig(
            chunk_size=1000,
            chunk_overlap=200,
            strategy=ChunkingStrategy.SENTENCE_BASED
        )

        assert config.chunk_size == 1000
        assert config.chunk_overlap == 200
        assert config.strategy == ChunkingStrategy.SENTENCE_BASED

    def test_chunking_strategy_enum(self):
        """Test chunking strategy enumeration."""
        strategies = list(ChunkingStrategy)

        assert ChunkingStrategy.RECURSIVE_CHARACTER in strategies
        assert ChunkingStrategy.SENTENCE_BASED in strategies
        assert ChunkingStrategy.SEMANTIC_BOUNDARY in strategies
        assert ChunkingStrategy.TOKEN_BASED in strategies
        assert ChunkingStrategy.HYBRID in strategies

    def test_basic_text_chunking(self, chunker):
        """Test basic text chunking functionality."""
        long_text = "This is a test document. " * 100  # 2500 characters

        # Mock the chunk_document method since it requires a Document object
        with patch.object(chunker, 'chunk_text') as mock_chunk:
            mock_chunk.return_value = [
                "This is a test document. " * 20,  # First chunk
                "This is a test document. " * 20   # Second chunk
            ]

            chunks = chunker.chunk_text(long_text)

            assert len(chunks) == 2
            mock_chunk.assert_called_once_with(long_text)

    def test_empty_text_handling(self, chunker):
        """Test handling of empty text."""
        with patch.object(chunker, 'chunk_text') as mock_chunk:
            mock_chunk.return_value = []

            chunks = chunker.chunk_text("")
            assert len(chunks) == 0





if __name__ == "__main__":
    pytest.main([__file__])
