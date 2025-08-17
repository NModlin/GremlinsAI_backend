# tests/unit/test_llm_manager.py
"""
Unit tests for ProductionLLMManager

Tests cover:
- Primary/fallback provider initialization
- Automatic failover logic
- Response time requirements
- Context management
- Error handling
- Performance metrics
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from app.core.llm_manager import (
    ProductionLLMManager,
    ConversationContext,
    ConversationContextStore,
    LLMResponse,
    LLMProviderType
)


class TestConversationContext:
    """Test conversation context management."""
    
    def test_context_creation(self):
        """Test creating a new conversation context."""
        context = ConversationContext(conversation_id="test-123")
        assert context.conversation_id == "test-123"
        assert len(context.messages) == 0
        assert context.max_context_length == 4000
    
    def test_add_message(self):
        """Test adding messages to context."""
        context = ConversationContext()
        context.add_message("user", "Hello")
        context.add_message("assistant", "Hi there!")
        
        assert len(context.messages) == 2
        assert context.messages[0]["role"] == "user"
        assert context.messages[0]["content"] == "Hello"
        assert context.messages[1]["role"] == "assistant"
        assert context.messages[1]["content"] == "Hi there!"
        assert "timestamp" in context.messages[0]
    
    def test_context_trimming(self):
        """Test context trimming when max length exceeded."""
        context = ConversationContext(max_context_length=2)
        context.add_message("user", "Message 1")
        context.add_message("assistant", "Response 1")
        context.add_message("user", "Message 2")
        context.add_message("assistant", "Response 2")
        
        # Should only keep the last 2 messages
        assert len(context.messages) == 2
        assert context.messages[0]["content"] == "Message 2"
        assert context.messages[1]["content"] == "Response 2"
    
    def test_get_langchain_messages(self):
        """Test converting to LangChain message format."""
        context = ConversationContext()
        context.add_message("user", "Hello")
        context.add_message("assistant", "Hi!")
        
        lc_messages = context.get_langchain_messages()
        assert len(lc_messages) == 2
        assert lc_messages[0].content == "Hello"
        assert lc_messages[1].content == "Hi!"


class TestConversationContextStore:
    """Test conversation context store."""
    
    def test_get_context(self):
        """Test getting or creating context."""
        store = ConversationContextStore()
        context = store.get_context("test-123")
        
        assert context.conversation_id == "test-123"
        assert len(context.messages) == 0
        
        # Getting same context should return same instance
        context2 = store.get_context("test-123")
        assert context is context2
    
    def test_update_context(self):
        """Test updating context."""
        store = ConversationContextStore()
        context = ConversationContext(conversation_id="test-123")
        context.add_message("user", "Hello")
        
        store.update_context("test-123", context)
        retrieved = store.get_context("test-123")
        
        assert len(retrieved.messages) == 1
        assert retrieved.messages[0]["content"] == "Hello"
    
    def test_clear_context(self):
        """Test clearing context."""
        store = ConversationContextStore()
        store.get_context("test-123")  # Create context
        store.clear_context("test-123")
        
        # Should create new context when accessed again
        new_context = store.get_context("test-123")
        assert len(new_context.messages) == 0


class TestProductionLLMManager:
    """Test ProductionLLMManager functionality."""
    
    @pytest.fixture
    def mock_openai_response(self):
        """Mock OpenAI response."""
        mock_response = Mock()
        mock_response.content = "This is a test response from OpenAI"
        mock_response.usage = {"total_tokens": 50}
        mock_response.finish_reason = "stop"
        return mock_response
    
    @pytest.fixture
    def mock_ollama_response(self):
        """Mock Ollama response."""
        mock_response = Mock()
        mock_response.content = "This is a test response from Ollama"
        mock_response.usage = {"total_tokens": 45}
        mock_response.finish_reason = "stop"
        return mock_response
    
    @patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test-key',
        'OLLAMA_BASE_URL': 'http://localhost:11434',
        'OPENAI_MODEL': 'gpt-3.5-turbo',
        'OLLAMA_MODEL': 'llama3.2:3b'
    })
    @patch('httpx.get')
    @patch('app.core.llm_manager.ChatOpenAI')
    @patch('app.core.llm_manager.ChatOllama')
    def test_manager_initialization(self, mock_ollama, mock_openai, mock_httpx):
        """Test LLM manager initialization."""
        # Mock successful Ollama connection
        mock_httpx.return_value.status_code = 200
        
        manager = ProductionLLMManager()
        
        assert manager.primary_llm is not None
        assert manager.fallback_llm is not None
        assert isinstance(manager.context_store, ConversationContextStore)
        assert manager.metrics["total_requests"] == 0
    
    @patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test-key',
        'OLLAMA_BASE_URL': 'http://localhost:11434'
    })
    @patch('httpx.get')
    @patch('app.core.llm_manager.ChatOpenAI')
    @patch('app.core.llm_manager.ChatOllama')
    async def test_successful_primary_response(self, mock_ollama, mock_openai, mock_httpx, mock_openai_response):
        """Test successful response from primary LLM."""
        # Setup mocks
        mock_httpx.return_value.status_code = 200
        mock_primary = AsyncMock()
        mock_primary.ainvoke.return_value = mock_openai_response
        mock_openai.return_value = mock_primary
        
        manager = ProductionLLMManager()
        
        # Test response generation
        response = await manager.generate_response("Hello, how are you?")
        
        assert isinstance(response, LLMResponse)
        assert response.content == "This is a test response from OpenAI"
        assert response.provider in ["openai", "ollama"]  # Allow either provider
        assert response.fallback_used is False
        assert response.response_time > 0
        assert response.error is None
        
        # Check metrics
        assert manager.metrics["total_requests"] == 1
        assert manager.metrics["successful_requests"] == 1
        assert manager.metrics["failed_requests"] == 0
        assert manager.metrics["fallback_requests"] == 0
    
    @patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test-key',
        'OLLAMA_BASE_URL': 'http://localhost:11434'
    })
    @patch('httpx.get')
    @patch('app.core.llm_manager.ChatOpenAI')
    @patch('app.core.llm_manager.ChatOllama')
    async def test_failover_to_fallback(self, mock_ollama, mock_openai, mock_httpx, mock_ollama_response):
        """Test automatic failover to fallback LLM when primary fails."""
        # Setup mocks
        mock_httpx.return_value.status_code = 200
        
        # Primary LLM fails
        mock_primary = AsyncMock()
        mock_primary.ainvoke.side_effect = Exception("OpenAI API error")
        mock_openai.return_value = mock_primary
        
        # Fallback LLM succeeds
        mock_fallback = AsyncMock()
        mock_fallback.ainvoke.return_value = mock_ollama_response
        mock_ollama.return_value = mock_fallback
        
        manager = ProductionLLMManager()
        
        # Test response generation
        response = await manager.generate_response("Hello, how are you?")
        
        assert isinstance(response, LLMResponse)
        assert response.content == "This is a test response from Ollama"
        assert response.provider == "ollama"
        assert response.fallback_used is True
        assert response.error is None
        
        # Check metrics
        assert manager.metrics["total_requests"] == 1
        assert manager.metrics["successful_requests"] == 1
        assert manager.metrics["failed_requests"] == 1  # Primary failed
        assert manager.metrics["fallback_requests"] == 1
    
    @patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test-key',
        'OLLAMA_BASE_URL': 'http://localhost:11434'
    })
    @patch('httpx.get')
    @patch('app.core.llm_manager.ChatOpenAI')
    @patch('app.core.llm_manager.ChatOllama')
    async def test_both_providers_fail(self, mock_ollama, mock_openai, mock_httpx):
        """Test behavior when both primary and fallback providers fail."""
        # Setup mocks
        mock_httpx.return_value.status_code = 200
        
        # Both LLMs fail
        mock_primary = AsyncMock()
        mock_primary.ainvoke.side_effect = Exception("OpenAI API error")
        mock_openai.return_value = mock_primary
        
        mock_fallback = AsyncMock()
        mock_fallback.ainvoke.side_effect = Exception("Ollama connection error")
        mock_ollama.return_value = mock_fallback
        
        manager = ProductionLLMManager()
        
        # Test response generation
        response = await manager.generate_response("Hello, how are you?")
        
        assert isinstance(response, LLMResponse)
        assert "technical difficulties" in response.content
        assert response.provider == "none"
        assert response.fallback_used is True
        assert response.error == "All LLM providers failed"
        
        # Check metrics
        assert manager.metrics["total_requests"] == 1
        assert manager.metrics["successful_requests"] == 0
        assert manager.metrics["failed_requests"] == 2  # Both failed
    
    @patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test-key',
        'OLLAMA_BASE_URL': 'http://localhost:11434'
    })
    @patch('httpx.get')
    @patch('app.core.llm_manager.ChatOpenAI')
    @patch('app.core.llm_manager.ChatOllama')
    async def test_response_timeout(self, mock_ollama, mock_openai, mock_httpx):
        """Test response timeout handling."""
        # Setup mocks
        mock_httpx.return_value.status_code = 200
        
        # Primary LLM times out
        mock_primary = AsyncMock()
        mock_primary.ainvoke.side_effect = asyncio.TimeoutError()
        mock_openai.return_value = mock_primary
        
        # Fallback LLM succeeds quickly
        mock_fallback = AsyncMock()
        mock_response = Mock()
        mock_response.content = "Quick fallback response"
        mock_fallback.ainvoke.return_value = mock_response
        mock_ollama.return_value = mock_fallback
        
        manager = ProductionLLMManager()
        
        # Test response generation
        response = await manager.generate_response("Hello, how are you?")
        
        assert response.content == "Quick fallback response"
        assert response.provider == "ollama"
        assert response.fallback_used is True
        assert manager.metrics["fallback_requests"] == 1
    
    @patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test-key',
        'OLLAMA_BASE_URL': 'http://localhost:11434'
    })
    @patch('httpx.get')
    @patch('app.core.llm_manager.ChatOpenAI')
    @patch('app.core.llm_manager.ChatOllama')
    async def test_context_management(self, mock_ollama, mock_openai, mock_httpx, mock_openai_response):
        """Test conversation context management."""
        # Setup mocks
        mock_httpx.return_value.status_code = 200
        mock_primary = AsyncMock()
        mock_primary.ainvoke.return_value = mock_openai_response
        mock_openai.return_value = mock_primary
        
        manager = ProductionLLMManager()
        
        # First message
        response1 = await manager.generate_response(
            "Hello", 
            conversation_id="test-conv"
        )
        
        # Second message in same conversation
        response2 = await manager.generate_response(
            "How are you?", 
            conversation_id="test-conv"
        )
        
        # Check that context was maintained
        context = manager.context_store.get_context("test-conv")
        assert len(context.messages) == 4  # 2 user + 2 assistant messages
        assert context.messages[0]["content"] == "Hello"
        assert context.messages[2]["content"] == "How are you?"
    
    def test_metrics_tracking(self):
        """Test performance metrics tracking."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            with patch('httpx.get') as mock_httpx:
                mock_httpx.return_value.status_code = 200
                with patch('app.core.llm_manager.ChatOpenAI'):
                    with patch('app.core.llm_manager.ChatOllama'):
                        manager = ProductionLLMManager()
                        
                        # Test metrics update
                        manager._update_metrics(1.5, LLMProviderType.OPENAI)
                        manager._update_metrics(2.0, LLMProviderType.OLLAMA)
                        
                        metrics = manager.get_metrics()
                        assert "provider_usage" in metrics
                        assert metrics["provider_usage"]["openai"] == 1
                        assert metrics["provider_usage"]["ollama"] == 1
    
    def test_health_status(self):
        """Test health status reporting."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            with patch('httpx.get') as mock_httpx:
                mock_httpx.return_value.status_code = 200
                with patch('app.core.llm_manager.ChatOpenAI'):
                    with patch('app.core.llm_manager.ChatOllama'):
                        manager = ProductionLLMManager()
                        
                        health = manager.get_health_status()
                        
                        assert "primary_llm_available" in health
                        assert "fallback_llm_available" in health
                        assert "success_rate" in health
                        assert "average_response_time" in health
                        assert health["primary_llm_available"] is True
                        assert health["fallback_llm_available"] is True


if __name__ == "__main__":
    pytest.main([__file__])
