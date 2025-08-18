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

# OpenTelemetry is optional; gracefully disable if not installed
try:
    from opentelemetry import trace, baggage
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.resources import Resource
    try:
        from opentelemetry.exporter.jaeger.thrift import JaegerExporter  # type: ignore
    except ImportError:
        JaegerExporter = None  # type: ignore
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.trace import Status, StatusCode
    from opentelemetry.semconv.trace import SpanAttributes
    OPENTELEMETRY_AVAILABLE = True


except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    trace = None  # type: ignore
    baggage = None  # type: ignore
    TracerProvider = None  # type: ignore
    BatchSpanProcessor = ConsoleSpanExporter = Resource = None  # type: ignore
    JaegerExporter = None  # type: ignore
    OTLPSpanExporter = None  # type: ignore
    FastAPIInstrumentor = RequestsInstrumentor = SQLAlchemyInstrumentor = RedisInstrumentor = None  # type: ignore
    Status = StatusCode = SpanAttributes = None  # type: ignore

from app.core.config import get_settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()

class MinimalTracingService:
    """No-op tracing service for Phase 0 to allow app startup without OTel deps."""
    def __init__(self):
        self.tracer_provider = None
    def instrument_fastapi(self, app):
        return None
    @contextmanager
    def trace_operation(self, operation_name: str, attributes: Optional[Dict[str, Any]] = None):
        class _Span:
            def set_attribute(self, *args, **kwargs):
                pass
            def set_status(self, *args, **kwargs):
                pass
            def record_exception(self, *args, **kwargs):
                pass
        yield _Span()
    def trace_function(self, operation_name: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None):
        def decorator(func: Callable) -> Callable:
            return func
        return decorator
    def shutdown(self):
        return None




# Simple internal no-op tracer used when OpenTelemetry is unavailable
class _NoopSpan:
    def set_attribute(self, *args, **kwargs):
        pass
    def set_status(self, *args, **kwargs):
        pass
    def record_exception(self, *args, **kwargs):
        pass

class _NoopTracer:
    def start_as_current_span(self, *args, **kwargs):
        class _CM:
            def __enter__(self_inner):
                return _NoopSpan()
            def __exit__(self_inner, exc_type, exc, tb):
                return False
        return _CM()

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

        # Respect hard feature flag: observability_enabled
        if not getattr(settings, 'observability_enabled', False):
            logger.info("Observability disabled by configuration; using No-op tracer")
            self.tracer = _NoopTracer()
            return

        self._setup_tracing()

        logger.info("TracingService initialized with OpenTelemetry")

# Simple internal no-op tracer used when OpenTelemetry is unavailable
class _NoopSpan:
    def set_attribute(self, *args, **kwargs):
        pass
    def set_status(self, *args, **kwargs):
        pass
    def record_exception(self, *args, **kwargs):
        pass

class _NoopTracer:
    def start_as_current_span(self, *args, **kwargs):
        class _CM:
            def __enter__(self_inner):
                return _NoopSpan()
            def __exit__(self_inner, exc_type, exc, tb):
                return False
        return _CM()

    def _setup_tracing(self):
        """Setup OpenTelemetry tracing configuration."""
        try:
            # Create resource with service information
            resource = Resource.create({
                "service.name": "gremlinsai",
                "service.version": getattr(settings, 'app_version', getattr(settings, 'version', '1.0.0')),
                "service.environment": getattr(settings, 'environment', 'development'),
                "service.instance.id": os.getenv('HOSTNAME', 'localhost')
            })

            # Create tracer provider
            if not OPENTELEMETRY_AVAILABLE:
                logger.warning("OpenTelemetry not installed; tracing disabled")
                self.tracer = _NoopTracer()
                return

            self.tracer_provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(self.tracer_provider)

            # Setup exporters
            if getattr(settings, 'observability_enabled', False):
                self._setup_exporters()
            else:
                logger.info("Observability flag disabled exporters")

            # Get tracer
            self.tracer = trace.get_tracer(__name__)

            # Setup automatic instrumentation
            if getattr(settings, 'observability_enabled', False):
                self._setup_auto_instrumentation()
            else:
                logger.info("Observability flag disabled auto-instrumentation")

            logger.info("OpenTelemetry tracing configured successfully")

        except Exception as e:
            logger.error(f"Failed to setup tracing: {e}")
            # Create a no-op tracer as fallback
            self.tracer = _NoopTracer()

    def _setup_exporters(self):
        """Setup trace exporters for different environments."""
        try:
            # Console exporter for development
            if getattr(settings, 'environment', 'development') == 'development':
                console_exporter = ConsoleSpanExporter()
                console_processor = BatchSpanProcessor(console_exporter)
                self.tracer_provider.add_span_processor(console_processor)

            # Jaeger exporter (optional)
            if OPENTELEMETRY_AVAILABLE and JaegerExporter is not None:
                jaeger_endpoint = os.getenv('JAEGER_ENDPOINT', 'http://localhost:14268/api/traces')
                if jaeger_endpoint:
                    try:
                        jaeger_exporter = JaegerExporter(
                            endpoint=jaeger_endpoint,
                            collector_endpoint=jaeger_endpoint
                        )
                        jaeger_processor = BatchSpanProcessor(jaeger_exporter)
                        self.tracer_provider.add_span_processor(jaeger_processor)
                        logger.info(f"Jaeger exporter configured: {jaeger_endpoint}")
                    except Exception as je:
                        logger.warning(f"Jaeger exporter setup failed: {je}")

            # OTLP exporter for production (optional)
            if OPENTELEMETRY_AVAILABLE and OTLPSpanExporter is not None:
                otlp_endpoint = os.getenv('OTLP_ENDPOINT')
                if otlp_endpoint:
                    try:
                        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
                        otlp_processor = BatchSpanProcessor(otlp_exporter)
                        self.tracer_provider.add_span_processor(otlp_processor)
                        logger.info(f"OTLP exporter configured: {otlp_endpoint}")
                    except Exception as oe:
                        logger.warning(f"OTLP exporter setup failed: {oe}")

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
            if not getattr(settings, 'observability_enabled', False):
                logger.info("Observability disabled; skipping FastAPI instrumentation")
                return

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
try:
    if not getattr(settings, 'observability_enabled', False):
        logger.info("Observability disabled by configuration; using MinimalTracingService")
        tracing_service = MinimalTracingService()
    else:
        tracing_service = TracingService()
except Exception as _e:
    # Fallback to minimal no-op service to allow app to start in Phase 0
    logger.warning(f"TracingService failed to initialize, falling back to MinimalTracingService: {_e}")
    tracing_service = MinimalTracingService()

# Convenience decorators
trace_function = tracing_service.trace_function
trace_operation = tracing_service.trace_operation
