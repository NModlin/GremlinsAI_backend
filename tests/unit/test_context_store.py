# tests/unit/test_context_store.py
"""
Unit tests for Redis-backed ConversationContextStore

Tests cover:
- Context creation, retrieval, and updates
- Redis integration with fallback to in-memory
- Context pruning and memory management
- TTL and expiration handling
- Error handling and resilience
- Performance and memory usage
"""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from app.core.context_store import ConversationContextStore
from app.core.llm_manager import ConversationContext


class TestConversationContextStore:
    """Test ConversationContextStore functionality."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.get.return_value = None
        mock_redis.setex.return_value = True
        mock_redis.delete.return_value = 1
        mock_redis.expire.return_value = True
        mock_redis.keys.return_value = []
        mock_redis.info.return_value = {
            "used_memory": 1024000,
            "used_memory_human": "1.00M",
            "connected_clients": 5
        }
        return mock_redis
    
    @pytest.fixture
    def context_store_with_redis(self, mock_redis):
        """Create context store with mocked Redis."""
        with patch('app.core.context_store.redis.from_url', return_value=mock_redis):
            store = ConversationContextStore(
                redis_url="redis://localhost:6379/0",
                max_messages_per_conversation=50,
                conversation_ttl_hours=24
            )
        return store
    
    @pytest.fixture
    def context_store_no_redis(self):
        """Create context store without Redis (fallback mode)."""
        with patch('app.core.context_store.REDIS_AVAILABLE', False):
            store = ConversationContextStore()
        return store
    
    @pytest.fixture
    def sample_context(self):
        """Create a sample conversation context."""
        context = ConversationContext(conversation_id="test-123")
        context.add_message("user", "Hello, how are you?")
        context.add_message("assistant", "I'm doing well, thank you!")
        context.add_message("user", "What's the weather like?")
        return context
    
    def test_context_store_initialization_with_redis(self, mock_redis):
        """Test context store initialization with Redis."""
        with patch('app.core.context_store.redis.from_url', return_value=mock_redis):
            store = ConversationContextStore(redis_url="redis://localhost:6379/0")
            
            assert store.use_redis is True
            assert store.redis_client is not None
            assert store.max_messages == 100  # default
            assert store.ttl_seconds == 24 * 3600  # default
            mock_redis.ping.assert_called_once()
    
    def test_context_store_initialization_without_redis(self):
        """Test context store initialization without Redis."""
        with patch('app.core.context_store.REDIS_AVAILABLE', False):
            store = ConversationContextStore()
            
            assert store.use_redis is False
            assert store.redis_client is None
            assert len(store._memory_store) == 0
    
    def test_context_store_redis_connection_failure(self):
        """Test fallback when Redis connection fails."""
        mock_redis = MagicMock()
        mock_redis.ping.side_effect = Exception("Connection failed")

        with patch('app.core.context_store.redis.from_url', return_value=mock_redis):
            with patch('app.core.context_store.logger.warning'):  # Suppress warning logs
                store = ConversationContextStore(redis_url="redis://localhost:6379/0")

                assert store.use_redis is False
                assert store.redis_client is None
    
    def test_get_context_new_conversation(self, context_store_with_redis):
        """Test getting context for new conversation."""
        context = context_store_with_redis.get_context("new-conversation")
        
        assert context.conversation_id == "new-conversation"
        assert len(context.messages) == 0
        assert isinstance(context.metadata, dict)
    
    def test_get_context_existing_conversation(self, context_store_with_redis, mock_redis, sample_context):
        """Test getting context for existing conversation."""
        # Mock Redis to return serialized context
        serialized_context = json.dumps({
            "conversation_id": "test-123",
            "messages": [
                {"role": "user", "content": "Hello", "timestamp": "2023-01-01T00:00:00"},
                {"role": "assistant", "content": "Hi there!", "timestamp": "2023-01-01T00:01:00"}
            ],
            "metadata": {},
            "max_context_length": 4000
        })
        mock_redis.get.return_value = serialized_context
        
        context = context_store_with_redis.get_context("test-123")
        
        assert context.conversation_id == "test-123"
        assert len(context.messages) == 2
        assert context.messages[0]["content"] == "Hello"
        mock_redis.get.assert_called_with("conversation:test-123")
        mock_redis.expire.assert_called_once()
    
    def test_update_context_with_redis(self, context_store_with_redis, mock_redis, sample_context):
        """Test updating context with Redis backend."""
        context_store_with_redis.update_context("test-123", sample_context)
        
        mock_redis.setex.assert_called_once()
        args = mock_redis.setex.call_args
        assert args[0][0] == "conversation:test-123"  # key
        assert args[0][1] == 24 * 3600  # TTL
        
        # Verify serialized data contains expected fields
        serialized_data = args[0][2]
        data = json.loads(serialized_data)
        assert data["conversation_id"] == "test-123"
        assert len(data["messages"]) == 3
    
    def test_update_context_fallback_to_memory(self, context_store_no_redis, sample_context):
        """Test updating context with memory fallback."""
        context_store_no_redis.update_context("test-123", sample_context)
        
        stored_context = context_store_no_redis._memory_store["test-123"]
        assert stored_context.conversation_id == "test-123"
        assert len(stored_context.messages) == 3
    
    def test_clear_context_with_redis(self, context_store_with_redis, mock_redis):
        """Test clearing context with Redis backend."""
        context_store_with_redis.clear_context("test-123")
        
        mock_redis.delete.assert_called_with("conversation:test-123")
    
    def test_clear_context_fallback_to_memory(self, context_store_no_redis, sample_context):
        """Test clearing context with memory fallback."""
        # First add context
        context_store_no_redis.update_context("test-123", sample_context)
        assert "test-123" in context_store_no_redis._memory_store
        
        # Then clear it
        context_store_no_redis.clear_context("test-123")
        assert "test-123" not in context_store_no_redis._memory_store
    
    def test_context_pruning(self, context_store_with_redis):
        """Test context pruning when max messages exceeded."""
        # Create context with many messages
        context = ConversationContext(conversation_id="test-pruning")
        
        # Add more messages than the limit (50)
        for i in range(60):
            context.add_message("user", f"Message {i}")
        
        # Update context (should trigger pruning)
        context_store_with_redis.update_context("test-pruning", context)
        
        # Verify context was pruned
        assert len(context.messages) == 50  # max_messages
        assert context.messages[0]["content"] == "Message 10"  # Should keep last 50
        assert context.messages[-1]["content"] == "Message 59"
        assert "pruned_at" in context.metadata
    
    def test_message_size_validation(self, context_store_with_redis):
        """Test message size validation and truncation."""
        context = ConversationContext(conversation_id="test-size")
        
        # Add a very large message
        large_content = "x" * 15000  # Larger than default max_message_size (10000)
        context.add_message("user", large_content)
        
        context_store_with_redis.update_context("test-size", context)
        
        # Verify message was truncated
        assert len(context.messages[0]["content"]) <= 10000 + len("... [truncated]")
        assert context.messages[0]["content"].endswith("... [truncated]")
        assert context.messages[0].get("truncated") is True
    
    def test_context_compression(self, context_store_with_redis):
        """Test context compression for large conversations."""
        context = ConversationContext(conversation_id="test-compression")
        
        # Add many messages to trigger compression
        for i in range(30):
            long_content = f"This is a long message {i} " + "x" * 1000
            context.add_message("user", long_content)
            context.add_message("assistant", f"Response to message {i}")
        
        # Serialize context (should trigger compression)
        serialized = context_store_with_redis._serialize_context(context)
        data = json.loads(serialized)
        
        # Check that compression was applied
        assert data.get("_compressed") is True
        
        # Verify older messages were compressed (truncated content)
        older_messages = data["messages"][:-20]  # All but last 20
        for msg in older_messages:
            if msg["role"] == "user":
                assert len(msg["content"]) <= 500  # Compressed content limit
    
    def test_memory_usage_stats(self, context_store_with_redis, mock_redis):
        """Test memory usage statistics."""
        mock_redis.keys.return_value = ["conversation:1", "conversation:2", "conversation:3"]
        
        stats = context_store_with_redis.get_memory_usage()
        
        assert stats["redis_available"] is True
        assert stats["redis_conversations"] == 3
        assert stats["max_messages_per_conversation"] == 50
        assert stats["compression_enabled"] is True
        assert "redis_used_memory" in stats
        assert "redis_used_memory_human" in stats
    
    def test_cleanup_expired_conversations(self, context_store_no_redis):
        """Test cleanup of expired conversations in memory store."""
        # Add contexts with different timestamps
        old_context = ConversationContext(conversation_id="old")
        old_context.metadata["last_updated"] = (datetime.utcnow() - timedelta(hours=25)).isoformat()
        
        new_context = ConversationContext(conversation_id="new")
        new_context.metadata["last_updated"] = datetime.utcnow().isoformat()
        
        context_store_no_redis._memory_store["old"] = old_context
        context_store_no_redis._memory_store["new"] = new_context
        
        # Run cleanup
        cleaned_count = context_store_no_redis.cleanup_expired_conversations()
        
        assert cleaned_count == 1
        assert "old" not in context_store_no_redis._memory_store
        assert "new" in context_store_no_redis._memory_store
    
    def test_health_check_with_redis(self, context_store_with_redis, mock_redis):
        """Test health check with Redis available."""
        health = context_store_with_redis.health_check()
        
        assert health["status"] == "healthy"
        assert health["redis_available"] is True
        assert health["redis_status"] == "connected"
        assert "redis_ping_ms" in health
        assert "timestamp" in health
        mock_redis.ping.assert_called()
    
    def test_health_check_redis_failure(self, context_store_with_redis, mock_redis):
        """Test health check when Redis fails."""
        # Reset the mock to simulate failure during health check
        mock_redis.reset_mock()
        mock_redis.ping.side_effect = Exception("Redis down")

        health = context_store_with_redis.health_check()

        assert health["status"] == "degraded"
        assert health["redis_status"] == "disconnected"
        assert "redis_error" in health
    
    def test_health_check_no_redis(self, context_store_no_redis):
        """Test health check without Redis."""
        health = context_store_no_redis.health_check()
        
        assert health["status"] == "healthy"
        assert health["redis_available"] is False
        assert health["redis_status"] == "not_configured"
    
    def test_invalid_conversation_id(self, context_store_with_redis):
        """Test handling of invalid conversation IDs."""
        with pytest.raises(ValueError):
            context_store_with_redis.get_context("")
        
        with pytest.raises(ValueError):
            context_store_with_redis.update_context("", ConversationContext())
    
    def test_redis_serialization_error_handling(self, context_store_with_redis, mock_redis):
        """Test handling of Redis serialization errors."""
        # Mock Redis to return invalid JSON
        mock_redis.get.return_value = "invalid json"
        
        # Should fall back to creating new context
        context = context_store_with_redis.get_context("test-error")
        assert context.conversation_id == "test-error"
        assert len(context.messages) == 0
    
    def test_concurrent_access_simulation(self, context_store_with_redis, mock_redis):
        """Test behavior under simulated concurrent access."""
        import threading
        import time
        
        results = []
        
        def worker(worker_id):
            try:
                context = context_store_with_redis.get_context(f"concurrent-{worker_id}")
                context.add_message("user", f"Message from worker {worker_id}")
                context_store_with_redis.update_context(f"concurrent-{worker_id}", context)
                results.append(f"success-{worker_id}")
            except Exception as e:
                results.append(f"error-{worker_id}: {e}")
        
        # Simulate concurrent access
        threads = []
        for i in range(10):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All workers should succeed
        assert len(results) == 10
        assert all(result.startswith("success") for result in results)


if __name__ == "__main__":
    pytest.main([__file__])
