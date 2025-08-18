"""
Distributed Tracing Service for Phase 4, Task 4.2: Monitoring & Observability

This module provides comprehensive distributed tracing using OpenTelemetry to track
request flows through the GremlinsAI application. It enables performance bottleneck
identification and end-to-end request visibility.

Features:
- OpenTelemetry SDK integration
- Automatic FastAPI instrumentation
- Custom spans for critical operations
- LLM and Weaviate query tracing
- Multi-agent workflow tracing
- Performance bottleneck identification
"""

import os
import time
import functools
from typing import Dict, Any, Optional, Callable
from contextlib import contextmanager

from opentelemetry import trace, baggage
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.trace import Status, StatusCode
from opentelemetry.semconv.trace import SpanAttributes

from app.core.config import get_settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


class TracingService:
    """
    Comprehensive distributed tracing service for GremlinsAI.
    
    Provides OpenTelemetry-based tracing for request flows, performance
    monitoring, and operational visibility across all application components.
    """
    
    def __init__(self):
        """Initialize tracing service."""
        self.tracer_provider = None
        self.tracer = None
        self._setup_tracing()
        
        logger.info("TracingService initialized with OpenTelemetry")
    
    def _setup_tracing(self):
        """Setup OpenTelemetry tracing configuration."""
        try:
            # Create resource with service information
            resource = Resource.create({
                "service.name": "gremlinsai",
                "service.version": getattr(settings, 'version', '1.0.0'),
                "service.environment": getattr(settings, 'environment', 'development'),
                "service.instance.id": os.getenv('HOSTNAME', 'localhost')
            })
            
            # Create tracer provider
            self.tracer_provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(self.tracer_provider)
            
            # Setup exporters
            self._setup_exporters()
            
            # Get tracer
            self.tracer = trace.get_tracer(__name__)
            
            # Setup automatic instrumentation
            self._setup_auto_instrumentation()
            
            logger.info("OpenTelemetry tracing configured successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup tracing: {e}")
            # Create a no-op tracer as fallback
            self.tracer = trace.NoOpTracer()
    
    def _setup_exporters(self):
        """Setup trace exporters for different environments."""
        try:
            # Console exporter for development
            if getattr(settings, 'environment', 'development') == 'development':
                console_exporter = ConsoleSpanExporter()
                console_processor = BatchSpanProcessor(console_exporter)
                self.tracer_provider.add_span_processor(console_processor)
            
            # Jaeger exporter
            jaeger_endpoint = os.getenv('JAEGER_ENDPOINT', 'http://localhost:14268/api/traces')
            if jaeger_endpoint:
                jaeger_exporter = JaegerExporter(
                    endpoint=jaeger_endpoint,
                    collector_endpoint=jaeger_endpoint
                )
                jaeger_processor = BatchSpanProcessor(jaeger_exporter)
                self.tracer_provider.add_span_processor(jaeger_processor)
                logger.info(f"Jaeger exporter configured: {jaeger_endpoint}")
            
            # OTLP exporter for production
            otlp_endpoint = os.getenv('OTLP_ENDPOINT')
            if otlp_endpoint:
                otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
                otlp_processor = BatchSpanProcessor(otlp_exporter)
                self.tracer_provider.add_span_processor(otlp_processor)
                logger.info(f"OTLP exporter configured: {otlp_endpoint}")
            
        except Exception as e:
            logger.error(f"Error setting up trace exporters: {e}")
    
    def _setup_auto_instrumentation(self):
        """Setup automatic instrumentation for common libraries."""
        try:
            # Instrument HTTP requests
            RequestsInstrumentor().instrument()
            
            # Instrument Redis (if available)
            try:
                RedisInstrumentor().instrument()
            except Exception:
                pass  # Redis instrumentation is optional
            
            # Instrument SQLAlchemy (if available)
            try:
                SQLAlchemyInstrumentor().instrument()
            except Exception:
                pass  # SQLAlchemy instrumentation is optional
            
            logger.info("Automatic instrumentation configured")
            
        except Exception as e:
            logger.error(f"Error setting up auto instrumentation: {e}")
    
    def instrument_fastapi(self, app):
        """Instrument FastAPI application for automatic tracing."""
        try:
            FastAPIInstrumentor.instrument_app(
                app,
                tracer_provider=self.tracer_provider,
                excluded_urls="/health,/metrics,/docs,/openapi.json"
            )
            logger.info("FastAPI instrumentation configured")
            
        except Exception as e:
            logger.error(f"Error instrumenting FastAPI: {e}")
    
    @contextmanager
    def trace_operation(self, operation_name: str, attributes: Optional[Dict[str, Any]] = None):
        """
        Context manager for tracing operations.
        
        Args:
            operation_name: Name of the operation being traced
            attributes: Additional attributes to add to the span
            
        Yields:
            Span object for additional customization
        """
        with self.tracer.start_as_current_span(operation_name) as span:
            try:
                # Add default attributes
                span.set_attribute("operation.name", operation_name)
                span.set_attribute("service.name", "gremlinsai")
                
                # Add custom attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, str(value))
                
                yield span
                
                # Mark as successful
                span.set_status(Status(StatusCode.OK))
                
            except Exception as e:
                # Record exception
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
    
    def trace_function(self, operation_name: Optional[str] = None, 
                      attributes: Optional[Dict[str, Any]] = None):
        """
        Decorator for tracing function calls.
        
        Args:
            operation_name: Custom operation name (defaults to function name)
            attributes: Additional attributes to add to the span
            
        Returns:
            Decorated function
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                op_name = operation_name or f"{func.__module__}.{func.__name__}"
                
                with self.trace_operation(op_name, attributes) as span:
                    # Add function-specific attributes
                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.module", func.__module__)
                    
                    # Execute function
                    result = await func(*args, **kwargs)
                    
                    return result
            
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                op_name = operation_name or f"{func.__module__}.{func.__name__}"
                
                with self.trace_operation(op_name, attributes) as span:
                    # Add function-specific attributes
                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.module", func.__module__)
                    
                    # Execute function
                    result = func(*args, **kwargs)
                    
                    return result
            
            # Return appropriate wrapper based on function type
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    def trace_llm_request(self, provider: str, model: str, prompt_tokens: int = 0):
        """
        Create a span for LLM requests.
        
        Args:
            provider: LLM provider (e.g., 'openai', 'anthropic')
            model: Model name
            prompt_tokens: Number of input tokens
            
        Returns:
            Context manager for the LLM request span
        """
        attributes = {
            "llm.provider": provider,
            "llm.model": model,
            "llm.prompt_tokens": prompt_tokens,
            "operation.type": "llm_request"
        }
        
        return self.trace_operation(f"llm.{provider}.{model}", attributes)
    
    def trace_weaviate_query(self, query_type: str, collection: str = ""):
        """
        Create a span for Weaviate queries.
        
        Args:
            query_type: Type of query (e.g., 'search', 'get', 'create')
            collection: Weaviate collection name
            
        Returns:
            Context manager for the Weaviate query span
        """
        attributes = {
            "weaviate.query_type": query_type,
            "weaviate.collection": collection,
            "operation.type": "weaviate_query"
        }
        
        return self.trace_operation(f"weaviate.{query_type}", attributes)
    
    def trace_multi_agent_task(self, workflow_type: str, agents: list):
        """
        Create a span for multi-agent tasks.
        
        Args:
            workflow_type: Type of workflow
            agents: List of agents involved
            
        Returns:
            Context manager for the multi-agent task span
        """
        attributes = {
            "multi_agent.workflow_type": workflow_type,
            "multi_agent.agents": ",".join(agents),
            "multi_agent.agent_count": len(agents),
            "operation.type": "multi_agent_task"
        }
        
        return self.trace_operation(f"multi_agent.{workflow_type}", attributes)
    
    def trace_rag_query(self, query_type: str, document_count: int = 0):
        """
        Create a span for RAG queries.
        
        Args:
            query_type: Type of RAG query
            document_count: Number of documents retrieved
            
        Returns:
            Context manager for the RAG query span
        """
        attributes = {
            "rag.query_type": query_type,
            "rag.document_count": document_count,
            "operation.type": "rag_query"
        }
        
        return self.trace_operation(f"rag.{query_type}", attributes)
    
    def trace_document_processing(self, document_type: str, document_size: int = 0):
        """
        Create a span for document processing.
        
        Args:
            document_type: Type of document being processed
            document_size: Size of document in bytes
            
        Returns:
            Context manager for the document processing span
        """
        attributes = {
            "document.type": document_type,
            "document.size_bytes": document_size,
            "operation.type": "document_processing"
        }
        
        return self.trace_operation(f"document.process.{document_type}", attributes)
    
    def add_baggage(self, key: str, value: str):
        """
        Add baggage to the current trace context.
        
        Args:
            key: Baggage key
            value: Baggage value
        """
        try:
            baggage.set_baggage(key, value)
        except Exception as e:
            logger.debug(f"Error setting baggage: {e}")
    
    def get_baggage(self, key: str) -> Optional[str]:
        """
        Get baggage from the current trace context.
        
        Args:
            key: Baggage key
            
        Returns:
            Baggage value or None
        """
        try:
            return baggage.get_baggage(key)
        except Exception as e:
            logger.debug(f"Error getting baggage: {e}")
            return None
    
    def get_current_trace_id(self) -> Optional[str]:
        """
        Get the current trace ID.
        
        Returns:
            Trace ID as string or None
        """
        try:
            span = trace.get_current_span()
            if span and span.get_span_context().is_valid:
                return format(span.get_span_context().trace_id, '032x')
            return None
        except Exception as e:
            logger.debug(f"Error getting trace ID: {e}")
            return None
    
    def get_current_span_id(self) -> Optional[str]:
        """
        Get the current span ID.
        
        Returns:
            Span ID as string or None
        """
        try:
            span = trace.get_current_span()
            if span and span.get_span_context().is_valid:
                return format(span.get_span_context().span_id, '016x')
            return None
        except Exception as e:
            logger.debug(f"Error getting span ID: {e}")
            return None
    
    def shutdown(self):
        """Shutdown tracing service and flush remaining spans."""
        try:
            if self.tracer_provider:
                self.tracer_provider.shutdown()
            logger.info("Tracing service shutdown completed")
        except Exception as e:
            logger.error(f"Error shutting down tracing service: {e}")


# Global tracing service instance
tracing_service = TracingService()

# Convenience decorators
trace_function = tracing_service.trace_function
trace_operation = tracing_service.trace_operation
