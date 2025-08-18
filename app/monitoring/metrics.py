"""
Prometheus Metrics for GremlinsAI Backend - Task T3.4

This module provides comprehensive Prometheus metrics collection for monitoring
system performance, AI-specific metrics, and application health.

Features:
- API request latency and error rates
- LLM response time and provider usage
- Tool usage and success/failure rates
- RAG retrieval relevance scores
- Custom AI metrics for production monitoring
"""

import time
import functools
from typing import Dict, Any, Optional, Callable
from prometheus_client import (
    Counter, Histogram, Gauge, Summary, Info,
    CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
)
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class MetricLabels:
    """Standard metric labels for consistency."""
    
    # API metrics
    API_METHOD = "method"
    API_ENDPOINT = "endpoint"
    API_STATUS_CODE = "status_code"
    
    # LLM metrics
    LLM_PROVIDER = "provider"
    LLM_MODEL = "model"
    LLM_OPERATION = "operation"
    
    # Agent metrics
    AGENT_TYPE = "agent_type"
    TOOL_NAME = "tool_name"
    TOOL_STATUS = "status"
    
    # RAG metrics
    RAG_OPERATION = "operation"
    RAG_SEARCH_TYPE = "search_type"


class GremlinsAIMetrics:
    """
    Centralized Prometheus metrics for GremlinsAI application.
    
    This class provides all the metrics needed for comprehensive monitoring
    of the AI system, including custom AI-specific metrics.
    """
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """Initialize metrics with optional custom registry."""
        self.registry = registry or CollectorRegistry()
        self._initialize_metrics()
        logger.info("GremlinsAI Prometheus metrics initialized")
    
    def _initialize_metrics(self):
        """Initialize all Prometheus metrics."""
        
        # =============================================================================
        # API METRICS
        # =============================================================================
        
        # API request counter
        self.api_requests_total = Counter(
            'gremlinsai_api_requests_total',
            'Total number of API requests',
            [MetricLabels.API_METHOD, MetricLabels.API_ENDPOINT, MetricLabels.API_STATUS_CODE],
            registry=self.registry
        )
        
        # API request duration histogram
        self.api_request_duration_seconds = Histogram(
            'gremlinsai_api_request_duration_seconds',
            'API request duration in seconds',
            [MetricLabels.API_METHOD, MetricLabels.API_ENDPOINT],
            buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 50.0, 100.0),
            registry=self.registry
        )
        
        # API error rate
        self.api_errors_total = Counter(
            'gremlinsai_api_errors_total',
            'Total number of API errors',
            [MetricLabels.API_METHOD, MetricLabels.API_ENDPOINT, MetricLabels.API_STATUS_CODE],
            registry=self.registry
        )
        
        # =============================================================================
        # LLM METRICS
        # =============================================================================
        
        # LLM response time histogram
        self.llm_response_duration_seconds = Histogram(
            'gremlinsai_llm_response_duration_seconds',
            'LLM response time in seconds',
            [MetricLabels.LLM_PROVIDER, MetricLabels.LLM_MODEL, MetricLabels.LLM_OPERATION],
            buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0, 120.0),
            registry=self.registry
        )
        
        # LLM requests counter
        self.llm_requests_total = Counter(
            'gremlinsai_llm_requests_total',
            'Total number of LLM requests',
            [MetricLabels.LLM_PROVIDER, MetricLabels.LLM_MODEL, MetricLabels.LLM_OPERATION],
            registry=self.registry
        )
        
        # LLM errors counter
        self.llm_errors_total = Counter(
            'gremlinsai_llm_errors_total',
            'Total number of LLM errors',
            [MetricLabels.LLM_PROVIDER, MetricLabels.LLM_MODEL],
            registry=self.registry
        )
        
        # LLM fallback usage
        self.llm_fallback_total = Counter(
            'gremlinsai_llm_fallback_total',
            'Total number of LLM fallback activations',
            [MetricLabels.LLM_PROVIDER],
            registry=self.registry
        )
        
        # LLM token usage
        self.llm_tokens_total = Counter(
            'gremlinsai_llm_tokens_total',
            'Total number of tokens processed',
            [MetricLabels.LLM_PROVIDER, MetricLabels.LLM_MODEL, 'token_type'],
            registry=self.registry
        )
        
        # =============================================================================
        # AGENT METRICS
        # =============================================================================
        
        # Tool usage counter
        self.agent_tool_usage_total = Counter(
            'gremlinsai_agent_tool_usage_total',
            'Total number of tool invocations',
            [MetricLabels.AGENT_TYPE, MetricLabels.TOOL_NAME, MetricLabels.TOOL_STATUS],
            registry=self.registry
        )
        
        # Tool execution time
        self.agent_tool_duration_seconds = Histogram(
            'gremlinsai_agent_tool_duration_seconds',
            'Tool execution time in seconds',
            [MetricLabels.AGENT_TYPE, MetricLabels.TOOL_NAME],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
            registry=self.registry
        )
        
        # Agent reasoning steps
        self.agent_reasoning_steps = Histogram(
            'gremlinsai_agent_reasoning_steps',
            'Number of reasoning steps per query',
            [MetricLabels.AGENT_TYPE],
            buckets=(1, 2, 3, 5, 8, 10, 15, 20),
            registry=self.registry
        )
        
        # Agent success rate
        self.agent_queries_total = Counter(
            'gremlinsai_agent_queries_total',
            'Total number of agent queries',
            [MetricLabels.AGENT_TYPE, 'status'],
            registry=self.registry
        )
        
        # =============================================================================
        # RAG METRICS
        # =============================================================================
        
        # RAG retrieval relevance scores
        self.rag_relevance_score = Histogram(
            'gremlinsai_rag_relevance_score',
            'RAG retrieval relevance scores',
            [MetricLabels.RAG_OPERATION, MetricLabels.RAG_SEARCH_TYPE],
            buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
            registry=self.registry
        )
        
        # RAG retrieval time
        self.rag_retrieval_duration_seconds = Histogram(
            'gremlinsai_rag_retrieval_duration_seconds',
            'RAG retrieval time in seconds',
            [MetricLabels.RAG_OPERATION, MetricLabels.RAG_SEARCH_TYPE],
            buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0),
            registry=self.registry
        )
        
        # RAG documents retrieved
        self.rag_documents_retrieved = Histogram(
            'gremlinsai_rag_documents_retrieved',
            'Number of documents retrieved by RAG',
            [MetricLabels.RAG_OPERATION],
            buckets=(1, 2, 3, 5, 10, 20, 50),
            registry=self.registry
        )
        
        # RAG cache hits
        self.rag_cache_total = Counter(
            'gremlinsai_rag_cache_total',
            'RAG cache hits and misses',
            ['cache_status'],
            registry=self.registry
        )
        
        # =============================================================================
        # SYSTEM METRICS
        # =============================================================================
        
        # Active conversations
        self.active_conversations = Gauge(
            'gremlinsai_active_conversations',
            'Number of active conversations',
            registry=self.registry
        )
        
        # Database connections
        self.database_connections = Gauge(
            'gremlinsai_database_connections',
            'Number of active database connections',
            ['pool_name'],
            registry=self.registry
        )
        
        # Memory usage
        self.memory_usage_bytes = Gauge(
            'gremlinsai_memory_usage_bytes',
            'Memory usage in bytes',
            ['component'],
            registry=self.registry
        )
        
        # Application info
        self.app_info = Info(
            'gremlinsai_app_info',
            'Application information',
            registry=self.registry
        )
        
        # Set application info
        self.app_info.info({
            'version': '1.0.0',
            'environment': 'production',
            'build_date': '2025-08-17'
        })
    
    # =============================================================================
    # METRIC RECORDING METHODS
    # =============================================================================
    
    def record_api_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record API request metrics."""
        self.api_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code
        ).inc()
        
        self.api_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
        
        if status_code >= 400:
            self.api_errors_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code
            ).inc()
    
    def record_llm_request(self, provider: str, model: str, operation: str, 
                          duration: float, success: bool = True, tokens_used: int = 0):
        """Record LLM request metrics."""
        self.llm_requests_total.labels(
            provider=provider,
            model=model,
            operation=operation
        ).inc()
        
        self.llm_response_duration_seconds.labels(
            provider=provider,
            model=model,
            operation=operation
        ).observe(duration)
        
        if not success:
            self.llm_errors_total.labels(
                provider=provider,
                model=model
            ).inc()
        
        if tokens_used > 0:
            self.llm_tokens_total.labels(
                provider=provider,
                model=model,
                token_type='total'
            ).inc(tokens_used)
    
    def record_llm_fallback(self, provider: str):
        """Record LLM fallback activation."""
        self.llm_fallback_total.labels(provider=provider).inc()
    
    def record_tool_usage(self, agent_type: str, tool_name: str, 
                         duration: float, success: bool = True):
        """Record agent tool usage metrics."""
        status = 'success' if success else 'failure'
        
        self.agent_tool_usage_total.labels(
            agent_type=agent_type,
            tool_name=tool_name,
            status=status
        ).inc()
        
        self.agent_tool_duration_seconds.labels(
            agent_type=agent_type,
            tool_name=tool_name
        ).observe(duration)
    
    def record_agent_query(self, agent_type: str, reasoning_steps: int, success: bool = True):
        """Record agent query metrics."""
        status = 'success' if success else 'failure'
        
        self.agent_queries_total.labels(
            agent_type=agent_type,
            status=status
        ).inc()
        
        self.agent_reasoning_steps.labels(
            agent_type=agent_type
        ).observe(reasoning_steps)
    
    def record_rag_retrieval(self, operation: str, search_type: str, 
                           duration: float, relevance_scores: list, 
                           documents_count: int):
        """Record RAG retrieval metrics."""
        self.rag_retrieval_duration_seconds.labels(
            operation=operation,
            search_type=search_type
        ).observe(duration)
        
        self.rag_documents_retrieved.labels(
            operation=operation
        ).observe(documents_count)
        
        # Record relevance scores
        for score in relevance_scores:
            self.rag_relevance_score.labels(
                operation=operation,
                search_type=search_type
            ).observe(score)
    
    def record_rag_cache(self, hit: bool):
        """Record RAG cache metrics."""
        status = 'hit' if hit else 'miss'
        self.rag_cache_total.labels(cache_status=status).inc()
    
    def update_active_conversations(self, count: int):
        """Update active conversations gauge."""
        self.active_conversations.set(count)
    
    def update_database_connections(self, pool_name: str, count: int):
        """Update database connections gauge."""
        self.database_connections.labels(pool_name=pool_name).set(count)
    
    def update_memory_usage(self, component: str, bytes_used: int):
        """Update memory usage gauge."""
        self.memory_usage_bytes.labels(component=component).set(bytes_used)
    
    def get_metrics(self) -> str:
        """Get metrics in Prometheus format."""
        return generate_latest(self.registry)


# Global metrics instance
metrics = GremlinsAIMetrics()


# =============================================================================
# DECORATORS FOR AUTOMATIC INSTRUMENTATION
# =============================================================================

def monitor_api_endpoint(endpoint_name: str = None):
    """Decorator to automatically monitor API endpoints."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            endpoint = endpoint_name or func.__name__
            method = "POST"  # Default, can be enhanced to detect actual method
            status_code = 200
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status_code = 500
                raise
            finally:
                duration = time.time() - start_time
                metrics.record_api_request(method, endpoint, status_code, duration)
        
        return wrapper
    return decorator


def monitor_llm_call(provider: str, model: str = "unknown", operation: str = "generate"):
    """Decorator to automatically monitor LLM calls."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                metrics.record_llm_request(provider, model, operation, duration, success)
        
        return wrapper
    return decorator


def monitor_tool_usage(agent_type: str, tool_name: str):
    """Decorator to automatically monitor tool usage."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                metrics.record_tool_usage(agent_type, tool_name, duration, success)
        
        return wrapper
    return decorator
