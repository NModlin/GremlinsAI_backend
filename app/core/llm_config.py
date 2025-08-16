# app/core/llm_config.py
"""
Local LLM Configuration Module for GremlinsAI

This module provides configuration and initialization for various local LLM providers
including Ollama, Hugging Face Transformers, and other local inference servers.
"""

import os
import logging
import time
from typing import Optional, Dict, Any, Union
from enum import Enum

logger = logging.getLogger(__name__)

class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    OLLAMA = "ollama"
    HUGGINGFACE = "huggingface"
    LLAMACPP = "llamacpp"
    MOCK = "mock"

class LLMConfig:
    """Configuration class for LLM providers."""
    
    def __init__(self):
        self.provider = self._detect_provider()
        self.model_name = self._get_model_name()
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "2048"))
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        
    def _detect_provider(self) -> LLMProvider:
        """Auto-detect the best available LLM provider."""
        # Check for OpenAI API key first
        if os.getenv("OPENAI_API_KEY"):
            return LLMProvider.OPENAI
            
        # Check for Ollama
        if os.getenv("OLLAMA_BASE_URL") or self._check_ollama_available():
            return LLMProvider.OLLAMA
            
        # Check for Hugging Face
        if os.getenv("USE_HUGGINGFACE") == "true":
            return LLMProvider.HUGGINGFACE
            
        # Default to mock for development
        logger.warning("No LLM provider configured, using mock provider")
        return LLMProvider.MOCK
    
    def _check_ollama_available(self) -> bool:
        """Check if Ollama is available on the default port."""
        try:
            import httpx
            response = httpx.get("http://localhost:11434/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False
    
    def _get_model_name(self) -> str:
        """Get the model name based on provider."""
        provider_models = {
            LLMProvider.OPENAI: os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
            LLMProvider.OLLAMA: os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
            LLMProvider.HUGGINGFACE: os.getenv("HF_MODEL", "microsoft/DialoGPT-medium"),
            LLMProvider.LLAMACPP: os.getenv("LLAMACPP_MODEL", "llama-2-7b-chat.gguf"),
            LLMProvider.MOCK: "mock-model"
        }
        return provider_models.get(self.provider, "default-model")

def create_llm(config: Optional[LLMConfig] = None):
    """
    Create an LLM instance based on the configuration.
    
    Args:
        config: LLM configuration. If None, auto-detects the best provider.
        
    Returns:
        LLM instance compatible with LangChain
    """
    if config is None:
        config = LLMConfig()
    
    logger.info(f"Initializing LLM with provider: {config.provider}, model: {config.model_name}")
    
    try:
        if config.provider == LLMProvider.OPENAI:
            return _create_openai_llm(config)
        elif config.provider == LLMProvider.OLLAMA:
            return _create_ollama_llm(config)
        elif config.provider == LLMProvider.HUGGINGFACE:
            return _create_huggingface_llm(config)
        elif config.provider == LLMProvider.LLAMACPP:
            return _create_llamacpp_llm(config)
        else:
            logger.warning(f"Provider {config.provider} not implemented, using mock")
            return _create_mock_llm(config)
            
    except Exception as e:
        logger.error(f"Failed to initialize {config.provider} LLM: {e}")
        logger.info("Falling back to mock LLM")
        return _create_mock_llm(config)

def _create_openai_llm(config: LLMConfig):
    """Create OpenAI LLM instance."""
    from langchain_openai import ChatOpenAI
    
    return ChatOpenAI(
        model=config.model_name,
        temperature=config.temperature,
        max_tokens=config.max_tokens
    )

def _create_ollama_llm(config: LLMConfig):
    """Create Ollama LLM instance."""
    try:
        from langchain_ollama import ChatOllama
        
        return ChatOllama(
            model=config.model_name,
            base_url=config.base_url,
            temperature=config.temperature,
            num_predict=config.max_tokens
        )
    except ImportError:
        logger.error("langchain-ollama not installed. Install with: pip install langchain-ollama")
        raise

def _create_huggingface_llm(config: LLMConfig):
    """Create Hugging Face LLM instance."""
    try:
        from langchain_huggingface import HuggingFacePipeline
        from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
        
        # Load model and tokenizer
        tokenizer = AutoTokenizer.from_pretrained(config.model_name)
        model = AutoModelForCausalLM.from_pretrained(
            config.model_name,
            device_map="auto",
            torch_dtype="auto"
        )
        
        # Create pipeline
        pipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=config.max_tokens,
            temperature=config.temperature,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )
        
        return HuggingFacePipeline(pipeline=pipe)
        
    except ImportError:
        logger.error("Hugging Face dependencies not installed. Install with: pip install transformers accelerate")
        raise

def _create_llamacpp_llm(config: LLMConfig):
    """Create LlamaCpp LLM instance."""
    try:
        from langchain_community.llms import LlamaCpp
        
        model_path = os.getenv("LLAMACPP_MODEL_PATH", f"./models/{config.model_name}")
        
        return LlamaCpp(
            model_path=model_path,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            n_ctx=4096,  # Context window
            verbose=False
        )
    except ImportError:
        logger.error("llama-cpp-python not installed. Install with: pip install llama-cpp-python")
        raise

def _create_mock_llm(config: LLMConfig):
    """Create a mock LLM for development/testing."""
    from langchain_core.language_models.fake import FakeListLLM
    
    responses = [
        "I'm a mock AI assistant. I can help you with various tasks, but I'm not connected to a real language model.",
        "This is a simulated response from the GremlinsAI system. In a real deployment, this would be powered by a local LLM.",
        "Mock response: I understand your query and would provide a helpful response if connected to a real language model.",
        "Development mode: This response is generated by a mock LLM for testing purposes."
    ]
    
    return FakeListLLM(responses=responses)

# Global LLM configuration instance
llm_config = LLMConfig()

# Global LLM instance cache with thread safety
import threading
_llm_instance_cache = None
_llm_config_hash = None
_llm_cache_lock = threading.RLock()

def _get_config_hash(config: LLMConfig) -> str:
    """Generate a hash of the current LLM configuration for cache invalidation."""
    config_tuple = (
        config.provider.value,
        config.model_name,
        config.temperature,
        config.max_tokens,
        config.base_url
    )
    return str(hash(config_tuple))

def get_llm():
    """
    Get the configured LLM instance with caching.

    This function implements thread-safe caching to avoid creating multiple
    LLM instances unnecessarily, which improves performance and reduces memory usage.

    Returns:
        LLM instance compatible with LangChain
    """
    global _llm_instance_cache, _llm_config_hash, _llm_metrics

    with _llm_cache_lock:
        # Check if config changed
        current_hash = _get_config_hash(llm_config)

        if _llm_instance_cache is None or _llm_config_hash != current_hash:
            logger.info(f"Creating new LLM instance (provider: {llm_config.provider}, model: {llm_config.model_name})")
            _llm_instance_cache = create_llm(llm_config)
            _llm_config_hash = current_hash
            _llm_metrics.record_cache_miss()
            logger.info("LLM instance cached successfully")
        else:
            _llm_metrics.record_cache_hit()
            logger.debug("Using cached LLM instance")

        return _llm_instance_cache

def invalidate_llm_cache():
    """
    Invalidate the LLM cache to force creation of a new instance.
    Useful for testing or when configuration changes externally.
    """
    global _llm_instance_cache, _llm_config_hash

    with _llm_cache_lock:
        logger.info("Invalidating LLM cache")
        _llm_instance_cache = None
        _llm_config_hash = None

def get_llm_cache_info() -> Dict[str, Any]:
    """Get information about the LLM cache status."""
    with _llm_cache_lock:
        return {
            "cache_active": _llm_instance_cache is not None,
            "config_hash": _llm_config_hash,
            "cache_instance_type": type(_llm_instance_cache).__name__ if _llm_instance_cache else None
        }

def get_specialized_llm(agent_type: str):
    """
    Get LLM instance with agent-specific parameters.

    This function provides role-specific LLM configurations optimized for different
    agent types while maintaining the benefits of instance caching.

    Args:
        agent_type: Type of agent ('researcher', 'writer', 'analyst', 'coordinator', or 'default')

    Returns:
        LLM instance with specialized parameters for the agent type
    """
    global _llm_metrics
    _llm_metrics.record_specialized_request(agent_type)

    base_llm = get_llm()  # Get cached base instance

    # Agent-specific parameter configurations
    agent_configs = {
        'researcher': {
            'temperature': 0.1,  # More focused and factual
            'max_tokens': 2048,
            'description': 'Optimized for factual research and information gathering'
        },
        'writer': {
            'temperature': 0.3,  # More creative and varied
            'max_tokens': 2048,
            'description': 'Optimized for creative and engaging content creation'
        },
        'analyst': {
            'temperature': 0.05,  # Very precise and analytical
            'max_tokens': 2048,
            'description': 'Optimized for precise analysis and data interpretation'
        },
        'coordinator': {
            'temperature': 0.2,  # Balanced for task management
            'max_tokens': 1024,  # Shorter responses for coordination
            'description': 'Optimized for task coordination and workflow management'
        },
        'default': {
            'temperature': llm_config.temperature,
            'max_tokens': llm_config.max_tokens,
            'description': 'Default configuration'
        }
    }

    config = agent_configs.get(agent_type.lower(), agent_configs['default'])

    # For Ollama, we can create a bound instance with different parameters
    if llm_config.provider == LLMProvider.OLLAMA:
        try:
            # Create a new instance with specialized parameters
            from langchain_ollama import ChatOllama

            specialized_llm = ChatOllama(
                model=llm_config.model_name,
                base_url=llm_config.base_url,
                temperature=config['temperature'],
                num_predict=config['max_tokens']
            )

            # Add metadata for monitoring
            specialized_llm._agent_type = agent_type
            specialized_llm._config_description = config['description']

            logger.debug(f"Created specialized LLM for {agent_type}: {config['description']}")
            return specialized_llm

        except Exception as e:
            logger.warning(f"Failed to create specialized LLM for {agent_type}, using base LLM: {e}")
            return base_llm

    # For other providers, try to bind parameters if supported
    try:
        if hasattr(base_llm, 'bind'):
            specialized_llm = base_llm.bind(
                temperature=config['temperature'],
                max_tokens=config['max_tokens']
            )
            specialized_llm._agent_type = agent_type
            specialized_llm._config_description = config['description']
            return specialized_llm
    except Exception as e:
        logger.debug(f"Parameter binding not supported for {llm_config.provider}, using base LLM: {e}")

    # Fallback to base LLM
    return base_llm

def get_agent_config_info(agent_type: str) -> Dict[str, Any]:
    """Get information about agent-specific configuration."""
    agent_configs = {
        'researcher': {'temperature': 0.1, 'max_tokens': 2048, 'focus': 'factual_research'},
        'writer': {'temperature': 0.3, 'max_tokens': 2048, 'focus': 'creative_content'},
        'analyst': {'temperature': 0.05, 'max_tokens': 2048, 'focus': 'precise_analysis'},
        'coordinator': {'temperature': 0.2, 'max_tokens': 1024, 'focus': 'task_management'},
        'default': {'temperature': llm_config.temperature, 'max_tokens': llm_config.max_tokens, 'focus': 'general'}
    }

    config = agent_configs.get(agent_type.lower(), agent_configs['default'])

    return {
        "agent_type": agent_type,
        "temperature": config['temperature'],
        "max_tokens": config['max_tokens'],
        "focus": config['focus'],
        "provider": llm_config.provider.value,
        "base_model": llm_config.model_name
    }

class LLMPool:
    """
    Connection pool for LLM instances to handle concurrent requests efficiently.

    This class manages a pool of LLM instances to improve concurrent request handling
    while maintaining memory efficiency. Uses round-robin distribution for load balancing.
    """

    def __init__(self, pool_size: int = 2, agent_type: str = "default"):
        """
        Initialize LLM pool.

        Args:
            pool_size: Number of LLM instances in the pool
            agent_type: Type of agent for specialized configuration
        """
        self.pool_size = max(1, pool_size)  # Ensure at least 1 instance
        self.agent_type = agent_type
        self.instances = []
        self.current_index = 0
        self.creation_count = 0
        self.request_count = 0
        self._pool_lock = threading.RLock()

        logger.info(f"Initializing LLM pool with size {self.pool_size} for {agent_type} agent")

    def get_llm(self):
        """
        Get an LLM instance from the pool using round-robin distribution.

        Returns:
            LLM instance from the pool
        """
        with self._pool_lock:
            self.request_count += 1

            # Create pool instances if not already created
            if not self.instances:
                self._create_pool()

            # Get instance using round-robin
            llm = self.instances[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.instances)

            logger.debug(f"Serving LLM instance {self.current_index} from pool (request #{self.request_count})")
            return llm

    def _create_pool(self):
        """Create the pool of LLM instances."""
        logger.info(f"Creating LLM pool with {self.pool_size} instances for {self.agent_type}")

        for i in range(self.pool_size):
            try:
                # Always create new instances for the pool to enable true pooling
                if self.agent_type == "default":
                    # Create new instance directly instead of using cache
                    llm = create_llm(llm_config)
                else:
                    llm = get_specialized_llm(self.agent_type)

                self.instances.append(llm)
                self.creation_count += 1
                logger.debug(f"Created pool instance {i+1}/{self.pool_size}")

            except Exception as e:
                logger.error(f"Failed to create pool instance {i+1}: {e}")
                # If we can't create the full pool, work with what we have
                if not self.instances:
                    raise Exception(f"Failed to create any LLM instances for pool: {e}")
                break

        logger.info(f"LLM pool created with {len(self.instances)} instances")

    def get_pool_stats(self) -> Dict[str, Any]:
        """Get statistics about the pool usage."""
        with self._pool_lock:
            return {
                "pool_size": len(self.instances),
                "target_pool_size": self.pool_size,
                "agent_type": self.agent_type,
                "creation_count": self.creation_count,
                "request_count": self.request_count,
                "current_index": self.current_index,
                "instances_created": len(self.instances) > 0
            }

    def invalidate_pool(self):
        """Invalidate the pool, forcing recreation on next request."""
        with self._pool_lock:
            logger.info(f"Invalidating LLM pool for {self.agent_type}")
            self.instances.clear()
            self.current_index = 0
            self.creation_count = 0

# Global pool instances for different agent types
_llm_pools: Dict[str, LLMPool] = {}
_pool_lock = threading.RLock()

def get_pooled_llm(agent_type: str = "default", pool_size: int = 2):
    """
    Get an LLM instance from a connection pool.

    This function provides connection pooling for better concurrent request handling.
    Each agent type gets its own pool with specialized configurations.

    Args:
        agent_type: Type of agent ('researcher', 'writer', 'analyst', 'coordinator', 'default')
        pool_size: Size of the connection pool (default: 2)

    Returns:
        LLM instance from the appropriate pool
    """
    global _llm_pools, _llm_metrics
    _llm_metrics.record_pooled_request()

    with _pool_lock:
        # Create pool if it doesn't exist
        if agent_type not in _llm_pools:
            _llm_pools[agent_type] = LLMPool(pool_size=pool_size, agent_type=agent_type)

        return _llm_pools[agent_type].get_llm()

def get_pool_stats(agent_type: str = None) -> Dict[str, Any]:
    """
    Get statistics for LLM pools.

    Args:
        agent_type: Specific agent type to get stats for, or None for all pools

    Returns:
        Dictionary with pool statistics
    """
    with _pool_lock:
        if agent_type:
            if agent_type in _llm_pools:
                return _llm_pools[agent_type].get_pool_stats()
            else:
                return {"error": f"No pool found for agent type: {agent_type}"}
        else:
            # Return stats for all pools
            return {
                pool_type: pool.get_pool_stats()
                for pool_type, pool in _llm_pools.items()
            }

def invalidate_all_pools():
    """Invalidate all LLM pools."""
    with _pool_lock:
        logger.info("Invalidating all LLM pools")
        for pool in _llm_pools.values():
            pool.invalidate_pool()
        _llm_pools.clear()

# Global metrics tracking
class LLMMetrics:
    """Class to track LLM usage metrics and performance."""

    def __init__(self):
        self.reset_metrics()
        self._metrics_lock = threading.RLock()

    def reset_metrics(self):
        """Reset all metrics to initial state."""
        with getattr(self, '_metrics_lock', threading.RLock()):
            self.cache_hits = 0
            self.cache_misses = 0
            self.specialized_llm_requests = 0
            self.pooled_llm_requests = 0
            self.total_llm_creations = 0
            self.agent_type_requests = {}
            self.start_time = time.time()
            self.last_reset_time = time.time()

    def record_cache_hit(self):
        """Record a cache hit."""
        with self._metrics_lock:
            self.cache_hits += 1

    def record_cache_miss(self):
        """Record a cache miss (new LLM creation)."""
        with self._metrics_lock:
            self.cache_misses += 1
            self.total_llm_creations += 1

    def record_specialized_request(self, agent_type: str):
        """Record a specialized LLM request."""
        with self._metrics_lock:
            self.specialized_llm_requests += 1
            self.agent_type_requests[agent_type] = self.agent_type_requests.get(agent_type, 0) + 1

    def record_pooled_request(self):
        """Record a pooled LLM request."""
        with self._metrics_lock:
            self.pooled_llm_requests += 1

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        with self._metrics_lock:
            current_time = time.time()
            uptime = current_time - self.start_time
            time_since_reset = current_time - self.last_reset_time

            total_requests = self.cache_hits + self.cache_misses
            cache_hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0

            return {
                "uptime_seconds": uptime,
                "time_since_reset_seconds": time_since_reset,
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses,
                "total_requests": total_requests,
                "cache_hit_rate_percent": cache_hit_rate,
                "specialized_llm_requests": self.specialized_llm_requests,
                "pooled_llm_requests": self.pooled_llm_requests,
                "total_llm_creations": self.total_llm_creations,
                "agent_type_requests": self.agent_type_requests.copy(),
                "requests_per_second": total_requests / time_since_reset if time_since_reset > 0 else 0
            }

# Global metrics instance
_llm_metrics = LLMMetrics()

def get_llm_metrics() -> Dict[str, Any]:
    """Get current LLM usage metrics."""
    return _llm_metrics.get_metrics()

def reset_llm_metrics():
    """Reset LLM metrics."""
    _llm_metrics.reset_metrics()
    logger.info("LLM metrics reset")

def get_llm_health_status() -> Dict[str, Any]:
    """
    Get comprehensive health status of the LLM system.

    Returns:
        Dictionary with health status information
    """
    try:
        # Test basic LLM functionality
        start_time = time.time()
        test_llm = get_llm()
        llm_creation_time = time.time() - start_time

        # Get system information
        cache_info = get_llm_cache_info()
        metrics = get_llm_metrics()
        pool_stats = get_pool_stats()

        # Check if LLM is actually available
        llm_available = test_llm is not None and llm_config.provider != LLMProvider.MOCK

        # Calculate health score
        health_score = 100
        issues = []

        if not llm_available:
            health_score -= 50
            issues.append("LLM not available or using mock provider")

        if not cache_info["cache_active"]:
            health_score -= 20
            issues.append("LLM cache not active")

        if llm_creation_time > 2.0:  # If LLM creation takes more than 2 seconds
            health_score -= 15
            issues.append(f"Slow LLM creation time: {llm_creation_time:.2f}s")

        if metrics["cache_hit_rate_percent"] < 50 and metrics["total_requests"] > 10:
            health_score -= 10
            issues.append(f"Low cache hit rate: {metrics['cache_hit_rate_percent']:.1f}%")

        # Determine overall status
        if health_score >= 90:
            status = "healthy"
        elif health_score >= 70:
            status = "degraded"
        else:
            status = "unhealthy"

        return {
            "status": status,
            "health_score": max(0, health_score),
            "llm_available": llm_available,
            "llm_creation_time": llm_creation_time,
            "provider": llm_config.provider.value,
            "model": llm_config.model_name,
            "cache_active": cache_info["cache_active"],
            "active_pools": len(pool_stats) if isinstance(pool_stats, dict) else 0,
            "metrics": metrics,
            "issues": issues,
            "timestamp": time.time()
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "health_score": 0,
            "error": str(e),
            "timestamp": time.time()
        }

def get_llm_info() -> Dict[str, Any]:
    """Get information about the current LLM configuration."""
    cache_info = get_llm_cache_info()
    pool_info = get_pool_stats()
    metrics = get_llm_metrics()

    return {
        "provider": llm_config.provider.value,
        "model_name": llm_config.model_name,
        "temperature": llm_config.temperature,
        "max_tokens": llm_config.max_tokens,
        "base_url": llm_config.base_url if llm_config.provider == LLMProvider.OLLAMA else None,
        "available": llm_config.provider != LLMProvider.MOCK,
        "cache_active": cache_info["cache_active"],
        "cache_instance_type": cache_info["cache_instance_type"],
        "specialized_agents_supported": True,
        "connection_pooling_supported": True,
        "active_pools": len(pool_info) if isinstance(pool_info, dict) else 0,
        "metrics": metrics
    }
