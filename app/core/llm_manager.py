# app/core/llm_manager.py
"""
Production LLM Manager for GremlinsAI

This module provides a robust LLM management system with automatic failover,
intelligent routing, and performance optimization for production environments.
"""

import os
import time
import asyncio
import logging
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

from app.monitoring.metrics import metrics

try:
    from langchain_anthropic import ChatAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# Import Redis-backed context store
try:
    from app.core.context_store import ConversationContextStore
    REDIS_CONTEXT_STORE_AVAILABLE = True
except ImportError:
    # Fallback to simple in-memory store if Redis context store not available
    REDIS_CONTEXT_STORE_AVAILABLE = False

logger = logging.getLogger(__name__)


class LLMProviderType(str, Enum):
    """LLM provider types for the manager."""
    OPENAI = "openai"
    OLLAMA = "ollama"
    ANTHROPIC = "anthropic"


@dataclass
class ConversationContext:
    """Context for conversation management with memory capabilities."""
    conversation_id: Optional[str] = None
    messages: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    max_context_length: int = 4000

    # Memory system fields
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    key_facts: List[Dict[str, Any]] = field(default_factory=list)
    interaction_summary: str = ""
    memory_keywords: List[str] = field(default_factory=list)
    memory_last_updated: Optional[str] = None
    
    def add_message(self, role: str, content: str, **kwargs):
        """Add a message to the conversation context."""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        self.messages.append(message)
        
        # Trim context if it gets too long
        if len(self.messages) > self.max_context_length:
            self.messages = self.messages[-self.max_context_length:]
    
    def get_langchain_messages(self) -> List[BaseMessage]:
        """Convert context messages to LangChain format."""
        lc_messages = []
        for msg in self.messages:
            if msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                lc_messages.append(AIMessage(content=msg["content"]))
        return lc_messages


@dataclass
class LLMResponse:
    """Response from LLM with metadata."""
    content: str
    provider: str
    model: str
    response_time: float
    token_count: Optional[int] = None
    finish_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    fallback_used: bool = False
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# ConversationContextStore moved to app/core/context_store.py for Redis backend support


class ProductionLLMManager:
    """
    Production-grade LLM manager with automatic failover and intelligent routing.
    
    Features:
    - Automatic failover between primary and fallback providers
    - Response time optimization (<2s target)
    - Context management and injection
    - Performance monitoring and metrics
    - Support for OpenAI, Ollama, and Anthropic
    """
    
    def __init__(self):
        """Initialize the production LLM manager with optimized connection pooling."""
        # Initialize context store (Redis-backed if available, in-memory fallback)
        if REDIS_CONTEXT_STORE_AVAILABLE:
            self.context_store = ConversationContextStore()
        else:
            # Fallback to simple in-memory store
            self.context_store = self._create_fallback_context_store()

        self.primary_llm = None
        self.fallback_llm = None

        # Enhanced connection pooling for better CPU utilization
        self._connection_pool = {}
        self._pool_size = int(os.getenv("LLM_POOL_SIZE", "5"))
        self._active_connections = 0
        self._connection_lock = asyncio.Lock()

        # Session management for persistent connections
        self._session_cache = {}
        self._session_timeout = 300  # 5 minutes

        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "fallback_requests": 0,
            "average_response_time": 0.0,
            "provider_usage": {},
            "pool_hits": 0,
            "pool_misses": 0
        }

        # Initialize LLM providers with connection pooling
        self._initialize_providers()

        logger.info(f"ProductionLLMManager initialized with connection pool size: {self._pool_size}")
        logger.info("Enhanced session management and CPU optimization enabled")

    def _create_fallback_context_store(self):
        """Create fallback in-memory context store when Redis is not available."""
        class SimpleConversationContextStore:
            def __init__(self):
                self._contexts: Dict[str, ConversationContext] = {}

            def get_context(self, conversation_id: str) -> ConversationContext:
                if conversation_id not in self._contexts:
                    self._contexts[conversation_id] = ConversationContext(
                        conversation_id=conversation_id
                    )
                return self._contexts[conversation_id]

            def update_context(self, conversation_id: str, context: ConversationContext):
                self._contexts[conversation_id] = context

            def clear_context(self, conversation_id: str):
                if conversation_id in self._contexts:
                    del self._contexts[conversation_id]

        return SimpleConversationContextStore()

    def _initialize_providers(self):
        """Initialize primary and fallback LLM providers."""
        # Try to initialize providers in order of preference
        providers_to_try = [
            ("primary", self._initialize_openai),
            ("anthropic", self._initialize_anthropic),
            ("fallback", self._initialize_ollama)
        ]

        initialized_count = 0
        for provider_type, init_func in providers_to_try:
            try:
                llm = init_func()
                if provider_type == "primary":
                    self.primary_llm = llm
                elif provider_type == "anthropic" and not self.primary_llm:
                    self.primary_llm = llm  # Use Anthropic as primary if OpenAI not available
                elif provider_type == "anthropic" and self.primary_llm:
                    self.fallback_llm = llm  # Use Anthropic as fallback if OpenAI is primary
                else:  # fallback/ollama
                    if not self.fallback_llm:
                        self.fallback_llm = llm

                logger.info(f"{provider_type.title()} LLM initialized: {type(llm).__name__}")
                initialized_count += 1
            except Exception as e:
                logger.warning(f"Failed to initialize {provider_type} LLM: {e}")

        if initialized_count == 0:
            raise RuntimeError("No LLM providers could be initialized")
    
    def _initialize_openai(self):
        """Initialize OpenAI LLM provider."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))
        max_tokens = int(os.getenv("LLM_MAX_TOKENS", "2048"))
        
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=30,  # 30 second timeout
            max_retries=2
        )
    
    def _initialize_anthropic(self):
        """Initialize Anthropic LLM provider."""
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("langchain-anthropic not installed")

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        model = os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229")
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))
        max_tokens = int(os.getenv("LLM_MAX_TOKENS", "2048"))

        return ChatAnthropic(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=30,
            max_retries=2
        )

    def _initialize_ollama(self):
        """Initialize Ollama LLM provider with optimized connection pooling."""
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))
        max_tokens = int(os.getenv("LLM_MAX_TOKENS", "2048"))

        # Test Ollama availability with connection pooling
        try:
            import httpx

            # Create persistent HTTP client for connection reuse
            client = httpx.Client(
                timeout=5.0,
                limits=httpx.Limits(
                    max_keepalive_connections=self._pool_size,
                    max_connections=self._pool_size * 2,
                    keepalive_expiry=300  # 5 minutes
                )
            )

            response = client.get(f"{base_url}/api/tags")
            if response.status_code != 200:
                raise ConnectionError(f"Ollama service not available at {base_url}")

            # Store client for reuse
            self._connection_pool['ollama_client'] = client

        except Exception as e:
            raise ConnectionError(f"Cannot connect to Ollama: {e}")

        # Create optimized ChatOllama instance
        ollama_llm = ChatOllama(
            model=model,
            base_url=base_url,
            temperature=temperature,
            num_predict=max_tokens,
            timeout=30,
            # Performance optimizations
            keep_alive="5m",  # Keep model loaded for 5 minutes
            num_ctx=4096,     # Optimized context window
            num_thread=4      # Optimize for multi-threading
        )

        # Add connection pooling metadata
        ollama_llm._connection_pool_enabled = True
        ollama_llm._pool_size = self._pool_size

        return ollama_llm

    async def _get_pooled_connection(self, provider_type: str):
        """Get a connection from the pool or create a new one."""
        async with self._connection_lock:
            pool_key = f"{provider_type}_pool"

            if pool_key not in self._connection_pool:
                self._connection_pool[pool_key] = []

            pool = self._connection_pool[pool_key]

            # Try to get an existing connection
            if pool:
                connection = pool.pop()
                self.metrics["pool_hits"] += 1
                logger.debug(f"Reusing pooled connection for {provider_type}")
                return connection

            # Create new connection if pool is empty
            self.metrics["pool_misses"] += 1
            if provider_type == "ollama":
                return self.fallback_llm
            else:
                return self.primary_llm

    async def _return_connection_to_pool(self, connection, provider_type: str):
        """Return a connection to the pool."""
        async with self._connection_lock:
            pool_key = f"{provider_type}_pool"

            if pool_key not in self._connection_pool:
                self._connection_pool[pool_key] = []

            pool = self._connection_pool[pool_key]

            # Only keep up to pool_size connections
            if len(pool) < self._pool_size:
                pool.append(connection)
                logger.debug(f"Returned connection to {provider_type} pool")

    async def generate_response(
        self, 
        query: str, 
        context: Optional[ConversationContext] = None,
        conversation_id: Optional[str] = None
    ) -> LLMResponse:
        """
        Generate response with automatic failover and context injection.
        
        Args:
            query: User query/prompt
            context: Optional conversation context
            conversation_id: Optional conversation ID for context management
            
        Returns:
            LLMResponse with content and metadata
        """
        start_time = time.time()
        self.metrics["total_requests"] += 1
        
        # Get or create conversation context
        if conversation_id and not context:
            context = self.context_store.get_context(conversation_id)
        elif not context:
            context = ConversationContext()
        
        # Add current query to context
        context.add_message("user", query)
        
        # Prepare messages for LLM
        messages = context.get_langchain_messages()
        
        # Try primary LLM first
        if self.primary_llm:
            try:
                # Determine provider type based on LLM class
                provider_type = self._get_provider_type(self.primary_llm)
                response = await self._call_llm(
                    self.primary_llm,
                    messages,
                    provider_type,
                    start_time
                )
                
                # Add response to context
                context.add_message("assistant", response.content)
                if conversation_id:
                    self.context_store.update_context(conversation_id, context)
                
                self.metrics["successful_requests"] += 1
                self._update_metrics(response.response_time, provider_type)
                return response
                
            except Exception as e:
                logger.warning(f"Primary LLM failed: {e}")
                self.metrics["failed_requests"] += 1
        
        # Fallback to secondary LLM
        if self.fallback_llm:
            try:
                logger.info("Using fallback LLM provider")
                fallback_provider_type = self._get_provider_type(self.fallback_llm)

                # Record fallback activation
                metrics.record_llm_fallback(fallback_provider_type.value)

                response = await self._call_llm(
                    self.fallback_llm,
                    messages,
                    fallback_provider_type,
                    start_time
                )
                response.fallback_used = True
                
                # Add response to context
                context.add_message("assistant", response.content)
                if conversation_id:
                    self.context_store.update_context(conversation_id, context)
                
                self.metrics["successful_requests"] += 1
                self.metrics["fallback_requests"] += 1
                self._update_metrics(response.response_time, fallback_provider_type)
                return response
                
            except Exception as e:
                logger.error(f"Fallback LLM also failed: {e}")
                self.metrics["failed_requests"] += 1
        
        # Both providers failed
        response_time = time.time() - start_time
        return LLMResponse(
            content="I apologize, but I'm currently unable to process your request due to technical difficulties. Please try again later.",
            provider="none",
            model="none",
            response_time=response_time,
            error="All LLM providers failed",
            fallback_used=True
        )

    def _get_provider_type(self, llm) -> LLMProviderType:
        """Determine provider type from LLM instance."""
        class_name = type(llm).__name__
        if "OpenAI" in class_name:
            return LLMProviderType.OPENAI
        elif "Anthropic" in class_name:
            return LLMProviderType.ANTHROPIC
        elif "Ollama" in class_name:
            return LLMProviderType.OLLAMA
        else:
            return LLMProviderType.OLLAMA  # Default fallback

    async def _call_llm(
        self,
        llm,
        messages: List[BaseMessage],
        provider: LLMProviderType,
        start_time: float
    ) -> LLMResponse:
        """Call LLM with optimized connection pooling and timeout handling."""
        connection = None
        try:
            # Get optimized connection from pool
            connection = await self._get_pooled_connection(provider.value.lower())

            # Use asyncio.wait_for to enforce timeout with optimized settings
            response = await asyncio.wait_for(
                connection.ainvoke(messages),
                timeout=1.8  # Slightly reduced timeout for better P99 performance
            )

            response_time = time.time() - start_time
            model_name = getattr(connection, 'model_name', getattr(connection, 'model', 'unknown'))
            token_count = getattr(response, 'usage', {}).get('total_tokens', 0)

            # Record enhanced Prometheus metrics
            metrics.record_llm_request(
                provider=provider.value,
                model=model_name,
                operation="generate",
                duration=response_time,
                success=True,
                tokens_used=token_count
            )

            # Record connection pool metrics
            pool_efficiency = self.metrics["pool_hits"] / max(1, self.metrics["pool_hits"] + self.metrics["pool_misses"])
            logger.debug(f"Connection pool efficiency: {pool_efficiency:.2%}")

            # Return connection to pool for reuse
            if connection:
                await self._return_connection_to_pool(connection, provider.value.lower())

            return LLMResponse(
                content=response.content,
                provider=provider.value,
                model=model_name,
                response_time=response_time,
                token_count=token_count,
                finish_reason=getattr(response, 'finish_reason', None)
            )
            
        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            model_name = getattr(llm, 'model_name', getattr(llm, 'model', 'unknown'))

            # Record failed request metrics
            metrics.record_llm_request(
                provider=provider.value,
                model=model_name,
                operation="generate",
                duration=response_time,
                success=False
            )

            raise Exception(f"LLM response timeout after {response_time:.2f}s")
        except Exception as e:
            response_time = time.time() - start_time
            model_name = getattr(llm, 'model_name', getattr(llm, 'model', 'unknown'))

            # Record failed request metrics
            metrics.record_llm_request(
                provider=provider.value,
                model=model_name,
                operation="generate",
                duration=response_time,
                success=False
            )

            raise Exception(f"LLM call failed after {response_time:.2f}s: {str(e)}")
    
    def _update_metrics(self, response_time: float, provider: LLMProviderType):
        """Update performance metrics."""
        # Update average response time
        total = self.metrics["successful_requests"]
        current_avg = self.metrics["average_response_time"]
        if total > 0:
            self.metrics["average_response_time"] = (
                (current_avg * (total - 1) + response_time) / total
            )
        else:
            self.metrics["average_response_time"] = response_time

        # Update provider usage
        provider_key = provider.value
        if provider_key not in self.metrics["provider_usage"]:
            self.metrics["provider_usage"][provider_key] = 0
        self.metrics["provider_usage"][provider_key] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return self.metrics.copy()
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of LLM providers."""
        return {
            "primary_llm_available": self.primary_llm is not None,
            "fallback_llm_available": self.fallback_llm is not None,
            "total_requests": self.metrics["total_requests"],
            "success_rate": (
                self.metrics["successful_requests"] / max(1, self.metrics["total_requests"])
            ) * 100,
            "average_response_time": self.metrics["average_response_time"],
            "fallback_usage_rate": (
                self.metrics["fallback_requests"] / max(1, self.metrics["successful_requests"])
            ) * 100
        }


# Global instance for the application
_llm_manager_instance = None

def get_llm_manager() -> ProductionLLMManager:
    """Get the global LLM manager instance."""
    global _llm_manager_instance
    if _llm_manager_instance is None:
        _llm_manager_instance = ProductionLLMManager()
    return _llm_manager_instance
