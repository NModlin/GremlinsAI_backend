# app/core/context_store.py
"""
Redis-backed conversation context management for GremlinsAI

This module provides persistent conversation context storage using Redis,
supporting high-throughput scenarios with configurable memory management.
"""

import json
import logging
import os
import time
from typing import Dict, Any, Optional, List
from dataclasses import asdict
from datetime import datetime, timedelta

try:
    import redis
    from redis.exceptions import RedisError, ConnectionError as RedisConnectionError
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from app.core.llm_manager import ConversationContext

logger = logging.getLogger(__name__)


class ConversationContextStore:
    """
    Redis-backed conversation context store with memory management.
    
    Features:
    - Persistent storage across application restarts
    - Automatic context pruning to manage memory usage
    - Configurable TTL for conversation expiration
    - Memory usage monitoring and optimization
    - Fallback to in-memory storage if Redis unavailable
    """
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        max_messages_per_conversation: int = 100,
        conversation_ttl_hours: int = 24,
        max_message_size: int = 10000,
        enable_compression: bool = True
    ):
        """
        Initialize the Redis-backed context store.
        
        Args:
            redis_url: Redis connection URL (default: from REDIS_URL env var)
            max_messages_per_conversation: Maximum messages to retain per conversation
            conversation_ttl_hours: Hours before conversation expires
            max_message_size: Maximum size of individual messages in characters
            enable_compression: Whether to compress stored data
        """
        self.max_messages = max_messages_per_conversation
        self.ttl_seconds = conversation_ttl_hours * 3600
        self.max_message_size = max_message_size
        self.enable_compression = enable_compression
        
        # Fallback in-memory store
        self._memory_store: Dict[str, ConversationContext] = {}
        
        # Initialize Redis connection
        self.redis_client = None
        self.use_redis = False
        
        if REDIS_AVAILABLE:
            try:
                redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
                self.redis_client = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                
                # Test connection
                self.redis_client.ping()
                self.use_redis = True
                logger.info(f"Redis context store initialized: {redis_url}")
                
            except (RedisConnectionError, RedisError) as e:
                logger.warning(f"Redis connection failed, using in-memory fallback: {e}")
                self.redis_client = None
                self.use_redis = False
        else:
            logger.warning("Redis not available, using in-memory context store")
    
    def _get_redis_key(self, conversation_id: str) -> str:
        """Generate Redis key for conversation."""
        return f"conversation:{conversation_id}"
    
    def _serialize_context(self, context: ConversationContext) -> str:
        """Serialize conversation context to JSON."""
        try:
            # Convert dataclass to dict
            context_dict = asdict(context)
            
            # Compress messages if enabled
            if self.enable_compression and len(context_dict.get("messages", [])) > 10:
                context_dict["_compressed"] = True
                # Simple compression: keep only essential fields for older messages
                messages = context_dict["messages"]
                if len(messages) > 20:
                    # Keep full detail for recent messages, compress older ones
                    recent_messages = messages[-20:]
                    older_messages = []
                    for msg in messages[:-20]:
                        compressed_msg = {
                            "role": msg.get("role"),
                            "content": msg.get("content", "")[:500],  # Truncate long content
                            "timestamp": msg.get("timestamp")
                        }
                        older_messages.append(compressed_msg)
                    context_dict["messages"] = older_messages + recent_messages
            
            return json.dumps(context_dict, default=str)
            
        except Exception as e:
            logger.error(f"Failed to serialize context: {e}")
            raise
    
    def _deserialize_context(self, data: str) -> ConversationContext:
        """Deserialize JSON to conversation context."""
        try:
            context_dict = json.loads(data)
            
            # Remove compression flag if present
            context_dict.pop("_compressed", None)
            
            # Create ConversationContext from dict
            return ConversationContext(**context_dict)
            
        except Exception as e:
            logger.error(f"Failed to deserialize context: {e}")
            raise
    
    def _prune_context(self, context: ConversationContext) -> ConversationContext:
        """Prune context to stay within memory limits."""
        if len(context.messages) <= self.max_messages:
            return context
        
        # Keep the most recent messages
        context.messages = context.messages[-self.max_messages:]
        
        # Update metadata
        context.metadata["pruned_at"] = datetime.utcnow().isoformat()
        context.metadata["original_message_count"] = context.metadata.get("total_messages", len(context.messages))
        
        logger.debug(f"Pruned conversation {context.conversation_id} to {len(context.messages)} messages")
        return context
    
    def _validate_message_size(self, context: ConversationContext) -> ConversationContext:
        """Validate and truncate oversized messages."""
        for message in context.messages:
            content = message.get("content", "")
            if len(content) > self.max_message_size:
                message["content"] = content[:self.max_message_size] + "... [truncated]"
                message["truncated"] = True
        
        return context
    
    def get_context(self, conversation_id: str) -> ConversationContext:
        """Get or create conversation context."""
        if not conversation_id:
            raise ValueError("conversation_id cannot be empty")
        
        # Try Redis first
        if self.use_redis and self.redis_client:
            try:
                redis_key = self._get_redis_key(conversation_id)
                data = self.redis_client.get(redis_key)
                
                if data:
                    context = self._deserialize_context(data)
                    # Refresh TTL on access
                    self.redis_client.expire(redis_key, self.ttl_seconds)
                    return context
                else:
                    # Create new context
                    context = ConversationContext(conversation_id=conversation_id)
                    self.update_context(conversation_id, context)
                    return context
                    
            except (RedisError, json.JSONDecodeError) as e:
                logger.error(f"Redis error getting context {conversation_id}: {e}")
                # Fall through to memory store
        
        # Fallback to in-memory store
        if conversation_id not in self._memory_store:
            self._memory_store[conversation_id] = ConversationContext(
                conversation_id=conversation_id
            )
        return self._memory_store[conversation_id]
    
    def update_context(self, conversation_id: str, context: ConversationContext):
        """Update conversation context."""
        if not conversation_id:
            raise ValueError("conversation_id cannot be empty")
        
        # Validate and prune context
        context = self._validate_message_size(context)
        context = self._prune_context(context)
        
        # Update metadata
        context.metadata["last_updated"] = datetime.utcnow().isoformat()
        context.metadata["total_messages"] = len(context.messages)
        
        # Try Redis first
        if self.use_redis and self.redis_client:
            try:
                redis_key = self._get_redis_key(conversation_id)
                serialized_data = self._serialize_context(context)
                
                # Store with TTL
                self.redis_client.setex(redis_key, self.ttl_seconds, serialized_data)
                
                # Remove from memory store if it exists (Redis is primary)
                self._memory_store.pop(conversation_id, None)
                return
                
            except (RedisError, json.JSONEncodeError) as e:
                logger.error(f"Redis error updating context {conversation_id}: {e}")
                # Fall through to memory store
        
        # Fallback to in-memory store
        self._memory_store[conversation_id] = context
    
    def clear_context(self, conversation_id: str):
        """Clear conversation context."""
        if not conversation_id:
            return
        
        # Clear from Redis
        if self.use_redis and self.redis_client:
            try:
                redis_key = self._get_redis_key(conversation_id)
                self.redis_client.delete(redis_key)
            except RedisError as e:
                logger.error(f"Redis error clearing context {conversation_id}: {e}")
        
        # Clear from memory store
        self._memory_store.pop(conversation_id, None)
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage statistics."""
        stats = {
            "redis_available": self.use_redis,
            "memory_store_conversations": len(self._memory_store),
            "max_messages_per_conversation": self.max_messages,
            "conversation_ttl_hours": self.ttl_seconds // 3600,
            "compression_enabled": self.enable_compression
        }
        
        if self.use_redis and self.redis_client:
            try:
                # Get Redis memory info
                info = self.redis_client.info("memory")
                stats.update({
                    "redis_used_memory": info.get("used_memory", 0),
                    "redis_used_memory_human": info.get("used_memory_human", "0B"),
                    "redis_connected_clients": self.redis_client.info("clients").get("connected_clients", 0)
                })
                
                # Count conversation keys
                conversation_keys = self.redis_client.keys("conversation:*")
                stats["redis_conversations"] = len(conversation_keys)
                
            except RedisError as e:
                logger.error(f"Error getting Redis memory stats: {e}")
                stats["redis_error"] = str(e)
        
        return stats
    
    def cleanup_expired_conversations(self) -> int:
        """Clean up expired conversations and return count of cleaned items."""
        cleaned_count = 0
        
        # Clean up memory store (simple TTL check)
        current_time = datetime.utcnow()
        expired_keys = []
        
        for conv_id, context in self._memory_store.items():
            last_updated = context.metadata.get("last_updated")
            if last_updated:
                try:
                    updated_time = datetime.fromisoformat(last_updated.replace('Z', '+00:00').replace('+00:00', ''))
                    if (current_time - updated_time).total_seconds() > self.ttl_seconds:
                        expired_keys.append(conv_id)
                except (ValueError, TypeError):
                    # Invalid timestamp, consider it expired
                    expired_keys.append(conv_id)
        
        for key in expired_keys:
            del self._memory_store[key]
            cleaned_count += 1
        
        logger.info(f"Cleaned up {cleaned_count} expired conversations")
        return cleaned_count
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on the context store."""
        health = {
            "status": "healthy",
            "redis_available": self.use_redis,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if self.use_redis and self.redis_client:
            try:
                # Test Redis connection
                start_time = time.time()
                self.redis_client.ping()
                health["redis_ping_ms"] = round((time.time() - start_time) * 1000, 2)
                health["redis_status"] = "connected"
            except RedisError as e:
                health["status"] = "degraded"
                health["redis_status"] = "disconnected"
                health["redis_error"] = str(e)
        else:
            health["redis_status"] = "not_configured"
        
        # Add memory usage stats
        health.update(self.get_memory_usage())
        
        return health


# Global instance for the application
_context_store_instance = None

def get_context_store() -> ConversationContextStore:
    """Get the global context store instance."""
    global _context_store_instance
    if _context_store_instance is None:
        _context_store_instance = ConversationContextStore()
    return _context_store_instance
