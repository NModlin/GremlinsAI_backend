# app/core/production_llm_manager.py
"""
Production-grade LLM Manager for GremlinsAI

This module implements a robust LLM management system following prometheus.md specifications:
- Ollama → OpenAI → Anthropic fallback chain
- Connection pooling for 50+ concurrent requests
- Context window management and token counting
- Redis-based response caching (60% reduction target)
- No fallback to mock implementations
"""

import os
import time
import asyncio
import hashlib
import logging
import json
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import tiktoken
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

try:
    from langchain_anthropic import ChatAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class LLMProviderType(str, Enum):
    """LLM provider types in fallback order."""
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


@dataclass
class LLMResponse:
    """Response from LLM with metadata."""
    content: str
    provider: LLMProviderType
    response_time: float
    tokens_used: int
    cached: bool = False
    fallback_used: bool = False
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ConnectionPool:
    """Connection pool for LLM providers."""
    provider_type: LLMProviderType
    connections: List[Any] = field(default_factory=list)
    max_size: int = 10
    active_count: int = 0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class ProductionLLMManager:
    """
    Production-grade LLM manager with robust failover and caching.
    
    Features:
    - Ollama → OpenAI → Anthropic fallback chain
    - Connection pooling for 50+ concurrent requests
    - Context window management and token counting
    - Redis response caching (60% reduction target)
    - No mock implementations
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """Initialize the production LLM manager."""
        self.redis_url = redis_url
        self.redis_client = None
        self.cache_ttl = int(os.getenv("LLM_CACHE_TTL", "3600"))  # 1 hour default
        
        # Connection pools for each provider
        self.connection_pools = {
            LLMProviderType.OLLAMA: ConnectionPool(LLMProviderType.OLLAMA, max_size=20),
            LLMProviderType.OPENAI: ConnectionPool(LLMProviderType.OPENAI, max_size=15),
            LLMProviderType.ANTHROPIC: ConnectionPool(LLMProviderType.ANTHROPIC, max_size=15)
        }
        
        # Provider instances
        self.providers = {}
        
        # Token counting
        self.tokenizer = None
        self.max_context_tokens = {
            LLMProviderType.OLLAMA: 4096,
            LLMProviderType.OPENAI: 16384,  # gpt-3.5-turbo-16k
            LLMProviderType.ANTHROPIC: 100000  # Claude-3
        }
        
        # Metrics
        self.metrics = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "provider_usage": {provider.value: 0 for provider in LLMProviderType},
            "fallback_usage": {provider.value: 0 for provider in LLMProviderType},
            "average_response_time": 0.0,
            "concurrent_requests": 0
        }
        
        # Initialize components
        self._initialize_redis()
        self._initialize_tokenizer()
        self._initialize_providers()
        
        logger.info("ProductionLLMManager initialized with production-grade features")

    def _initialize_redis(self):
        """Initialize Redis client for caching."""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, caching disabled")
            return
            
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Redis cache initialized successfully")
        except Exception as e:
            logger.warning(f"Redis initialization failed: {e}, caching disabled")
            self.redis_client = None

    def _initialize_tokenizer(self):
        """Initialize tokenizer for token counting."""
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")  # GPT-3.5/4 encoding
            logger.info("Tokenizer initialized for context management")
        except Exception as e:
            logger.warning(f"Tokenizer initialization failed: {e}")

    def _initialize_providers(self):
        """Initialize LLM providers in fallback order."""
        # Initialize in fallback order: Ollama → OpenAI → Anthropic
        provider_initializers = [
            (LLMProviderType.OLLAMA, self._initialize_ollama),
            (LLMProviderType.OPENAI, self._initialize_openai),
            (LLMProviderType.ANTHROPIC, self._initialize_anthropic)
        ]
        
        for provider_type, initializer in provider_initializers:
            try:
                provider = initializer()
                self.providers[provider_type] = provider
                logger.info(f"{provider_type.value} provider initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize {provider_type.value}: {e}")
        
        if not self.providers:
            raise RuntimeError("No LLM providers could be initialized")
        
        logger.info(f"Initialized {len(self.providers)} LLM providers")

    def _initialize_ollama(self):
        """Initialize Ollama provider (primary)."""
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
        
        # Test Ollama availability
        try:
            import httpx
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{base_url}/api/tags")
                if response.status_code != 200:
                    raise ConnectionError(f"Ollama not available at {base_url}")
        except Exception as e:
            raise ConnectionError(f"Cannot connect to Ollama: {e}")
        
        return ChatOllama(
            model=model,
            base_url=base_url,
            temperature=0.1,
            num_predict=2048,
            timeout=30,
            keep_alive="5m",
            num_ctx=4096
        )

    def _initialize_openai(self):
        """Initialize OpenAI provider (fallback)."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        return ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo-16k"),
            temperature=0.1,
            max_tokens=2048,
            timeout=30,
            max_retries=2,
            api_key=api_key
        )

    def _initialize_anthropic(self):
        """Initialize Anthropic provider (last resort)."""
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("langchain-anthropic not installed")
        
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        return ChatAnthropic(
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229"),
            temperature=0.1,
            max_tokens=2048,
            timeout=30,
            max_retries=2,
            api_key=api_key
        )

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if not self.tokenizer:
            # Rough estimation: 1 token ≈ 4 characters
            return len(text) // 4
        
        try:
            return len(self.tokenizer.encode(text))
        except Exception:
            return len(text) // 4

    def _truncate_context(self, prompt: str, context: str, provider: LLMProviderType) -> str:
        """Truncate context to fit within token limits."""
        max_tokens = self.max_context_tokens[provider]
        prompt_tokens = self._count_tokens(prompt)
        
        # Reserve tokens for prompt and response
        available_tokens = max_tokens - prompt_tokens - 512  # 512 for response
        
        if available_tokens <= 0:
            return ""
        
        context_tokens = self._count_tokens(context)
        if context_tokens <= available_tokens:
            return context
        
        # Truncate context intelligently (keep recent parts)
        lines = context.split('\n')
        truncated_lines = []
        current_tokens = 0
        
        # Start from the end (most recent)
        for line in reversed(lines):
            line_tokens = self._count_tokens(line)
            if current_tokens + line_tokens > available_tokens:
                break
            truncated_lines.insert(0, line)
            current_tokens += line_tokens
        
        return '\n'.join(truncated_lines)

    def _generate_cache_key(self, prompt: str, context: str = "") -> str:
        """Generate cache key for prompt and context."""
        content = f"{prompt}|{context}"
        return f"llm_cache:{hashlib.md5(content.encode()).hexdigest()}"

    async def _get_cached_response(self, cache_key: str) -> Optional[LLMResponse]:
        """Get cached response if available."""
        if not self.redis_client:
            return None
        
        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                data = json.loads(cached_data)
                response = LLMResponse(**data)
                response.cached = True
                self.metrics["cache_hits"] += 1
                return response
        except Exception as e:
            logger.warning(f"Cache retrieval failed: {e}")
        
        self.metrics["cache_misses"] += 1
        return None

    async def _cache_response(self, cache_key: str, response: LLMResponse):
        """Cache response for future use."""
        if not self.redis_client:
            return
        
        try:
            # Don't cache the cached flag
            cache_data = {
                "content": response.content,
                "provider": response.provider.value,
                "response_time": response.response_time,
                "tokens_used": response.tokens_used,
                "fallback_used": response.fallback_used,
                "error": response.error,
                "timestamp": response.timestamp
            }
            
            self.redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(cache_data)
            )
        except Exception as e:
            logger.warning(f"Cache storage failed: {e}")

    async def _get_connection(self, provider_type: LLMProviderType):
        """Get connection from pool or create new one."""
        pool = self.connection_pools[provider_type]

        async with pool.lock:
            if pool.connections:
                connection = pool.connections.pop()
                pool.active_count += 1
                return connection

            if pool.active_count < pool.max_size:
                # Create new connection
                provider = self.providers.get(provider_type)
                if provider:
                    pool.active_count += 1
                    return provider

            # Pool exhausted, wait and retry
            await asyncio.sleep(0.1)
            return await self._get_connection(provider_type)

    async def _return_connection(self, provider_type: LLMProviderType, connection):
        """Return connection to pool."""
        pool = self.connection_pools[provider_type]

        async with pool.lock:
            if len(pool.connections) < pool.max_size:
                pool.connections.append(connection)
            pool.active_count = max(0, pool.active_count - 1)

    async def _call_provider(self, provider_type: LLMProviderType, messages: List[BaseMessage]) -> LLMResponse:
        """Call specific LLM provider with connection pooling."""
        start_time = time.time()

        try:
            connection = await self._get_connection(provider_type)

            # Call the LLM
            response = await connection.ainvoke(messages)
            response_time = time.time() - start_time

            # Count tokens
            tokens_used = self._count_tokens(response.content)

            # Return connection to pool
            await self._return_connection(provider_type, connection)

            # Update metrics
            self.metrics["provider_usage"][provider_type.value] += 1

            return LLMResponse(
                content=response.content,
                provider=provider_type,
                response_time=response_time,
                tokens_used=tokens_used
            )

        except Exception as e:
            logger.error(f"{provider_type.value} provider failed: {e}")
            raise

    async def generate_response(self, prompt: str, context: str = "") -> LLMResponse:
        """
        Generate response with Ollama → OpenAI → Anthropic fallback chain.

        Args:
            prompt: The main prompt/query
            context: Additional context (will be truncated if needed)

        Returns:
            LLMResponse with content and metadata
        """
        start_time = time.time()
        self.metrics["total_requests"] += 1
        self.metrics["concurrent_requests"] += 1

        try:
            # Check cache first
            cache_key = self._generate_cache_key(prompt, context)
            cached_response = await self._get_cached_response(cache_key)
            if cached_response:
                return cached_response

            # Try providers in fallback order
            fallback_chain = [
                LLMProviderType.OLLAMA,
                LLMProviderType.OPENAI,
                LLMProviderType.ANTHROPIC
            ]

            last_error = None

            for i, provider_type in enumerate(fallback_chain):
                if provider_type not in self.providers:
                    continue

                try:
                    # Truncate context for this provider
                    truncated_context = self._truncate_context(prompt, context, provider_type)

                    # Prepare messages
                    messages = []
                    if truncated_context:
                        messages.append(HumanMessage(content=f"Context: {truncated_context}"))
                    messages.append(HumanMessage(content=prompt))

                    # Call provider
                    response = await self._call_provider(provider_type, messages)

                    # Mark if fallback was used
                    if i > 0:
                        response.fallback_used = True
                        self.metrics["fallback_usage"][provider_type.value] += 1

                    # Cache successful response
                    await self._cache_response(cache_key, response)

                    return response

                except Exception as e:
                    last_error = e
                    logger.warning(f"{provider_type.value} failed, trying next provider: {e}")
                    continue

            # All providers failed
            error_msg = f"All LLM providers failed. Last error: {last_error}"
            logger.error(error_msg)

            return LLMResponse(
                content="I apologize, but I'm currently unable to process your request due to technical difficulties.",
                provider=LLMProviderType.OLLAMA,  # Default
                response_time=time.time() - start_time,
                tokens_used=0,
                error=error_msg
            )

        finally:
            self.metrics["concurrent_requests"] = max(0, self.metrics["concurrent_requests"] - 1)

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        cache_hit_rate = 0.0
        total_cache_requests = self.metrics["cache_hits"] + self.metrics["cache_misses"]
        if total_cache_requests > 0:
            cache_hit_rate = self.metrics["cache_hits"] / total_cache_requests

        return {
            **self.metrics,
            "cache_hit_rate": cache_hit_rate,
            "providers_available": list(self.providers.keys()),
            "connection_pools": {
                provider.value: {
                    "active": pool.active_count,
                    "available": len(pool.connections),
                    "max_size": pool.max_size
                }
                for provider, pool in self.connection_pools.items()
            }
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all providers."""
        health_status = {}

        for provider_type, provider in self.providers.items():
            try:
                test_messages = [HumanMessage(content="Hello")]
                start_time = time.time()
                await provider.ainvoke(test_messages)
                response_time = time.time() - start_time

                health_status[provider_type.value] = {
                    "status": "healthy",
                    "response_time": response_time
                }
            except Exception as e:
                health_status[provider_type.value] = {
                    "status": "unhealthy",
                    "error": str(e)
                }

        return health_status


# Global instance
_production_llm_manager = None

def get_llm_manager() -> ProductionLLMManager:
    """Get the global ProductionLLMManager instance."""
    global _production_llm_manager
    if _production_llm_manager is None:
        _production_llm_manager = ProductionLLMManager()
    return _production_llm_manager
