# app/main.py
"""
GremlinsAI Backend Main Application.

Production-ready FastAPI application with:
- Structured logging and correlation IDs
- Environment-aware configuration
- Secure secrets management
- Comprehensive error handling
- Performance monitoring
"""

import logging
import sys
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.endpoints import agent, chat_history, orchestrator, multi_agent, documents, realtime, docs, developer_portal, multimodal, health, oauth, metrics, auth
from app.api.v1.websocket import endpoints as websocket_endpoints
from app.database.database import ensure_data_directory
from app.core.config import get_settings
from app.core.logging_config import setup_logging, RequestLoggingMiddleware, get_logger, log_security_event
from app.core.exceptions import GremlinsAIException
from app.core.error_handlers import (
    gremlins_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    sqlalchemy_exception_handler,
    general_exception_handler
)
from app.middleware.monitoring import PrometheusMiddleware
from app.middleware.security_middleware import setup_security_middleware
from app.middleware.monitoring_middleware import setup_monitoring_middleware
from app.core.tracing_service import tracing_service

# Initialize settings and logging
settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager with production-ready initialization.

    Handles startup and shutdown procedures including:
    - Configuration validation
    - Logging setup
    - Service initialization
    - Security audit logging
    """
    # Startup procedures
    logger.info(
        "Application startup initiated",
        extra={
            'extra_fields': {
                'environment': settings.environment.value,
                'version': settings.app_version,
                'debug_mode': settings.debug,
                'event_type': 'application_startup'
            }
        }
    )

    try:
        # Setup structured logging
        setup_logging(
            environment=settings.environment.value,
            log_level=settings.log_level,
            enable_json_logging=not settings.is_development,
            log_file=f"./logs/gremlinsai_{settings.environment.value}.log" if not settings.is_development else None
        )

        # Validate configuration
        logger.info("Validating application configuration")
        config_dict = settings.mask_sensitive_values()
        logger.debug(
            "Configuration loaded",
            extra={
                'extra_fields': {
                    'config_summary': {
                        'environment': config_dict.get('environment'),
                        'database_type': 'sqlite' if 'sqlite' in config_dict.get('database_url', '') else 'external',
                        'secrets_backend': config_dict.get('secrets_backend'),
                        'debug_mode': config_dict.get('debug'),
                        'cors_origins_count': len(config_dict.get('cors_origins', [])),
                    },
                    'event_type': 'configuration_loaded'
                }
            }
        )

        # Ensure data directory exists
        ensure_data_directory()
        logger.info("Data directory initialized")

        # Initialize service monitoring
        from app.core.service_monitor import initialize_service_monitoring
        initialize_service_monitoring()
        logger.info("Service monitoring initialized")

        # Log security event for application start
        log_security_event(
            event_type="application_start",
            severity="low",
            environment=settings.environment.value,
            version=settings.app_version
        )

        logger.info(
            "Application startup completed successfully",
            extra={
                'extra_fields': {
                    'environment': settings.environment.value,
                    'startup_time': 'completed',
                    'event_type': 'application_ready'
                }
            }
        )

    except Exception as e:
        logger.error(
            "Application startup failed",
            extra={
                'extra_fields': {
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'event_type': 'application_startup_failed'
                }
            },
            exc_info=True
        )

        # Log critical security event
        log_security_event(
            event_type="application_startup_failure",
            severity="critical",
            error=str(e),
            environment=settings.environment.value
        )

        # Re-raise to prevent application from starting with invalid configuration
        raise

    yield

    # Shutdown procedures
    logger.info(
        "Application shutdown initiated",
        extra={
            'extra_fields': {
                'environment': settings.environment.value,
                'event_type': 'application_shutdown'
            }
        }
    )

    # Log security event for application shutdown
    log_security_event(
        event_type="application_shutdown",
        severity="low",
        environment=settings.environment.value
    )

    logger.info("Application shutdown completed")


# Create the main FastAPI application instance
app = FastAPI(
    title="gremlinsAI",
    description="API for the gremlinsAI multi-modal agentic system with advanced multi-agent architecture, RAG capabilities, asynchronous task orchestration, and real-time communication.",
    version=settings.app_version,
    lifespan=lifespan,
    debug=settings.debug
)

# Add request logging middleware (must be first to capture all requests)
app.add_middleware(RequestLoggingMiddleware)

# Add CORS middleware with environment-specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Add Prometheus monitoring middleware
app.add_middleware(PrometheusMiddleware)

# Add security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)

    # Import security headers from our security module
    from app.core.security import get_security_headers
    security_headers = get_security_headers()

    for header, value in security_headers.items():
        response.headers[header] = value

    return response

# Enhanced Global Error Handling
app.add_exception_handler(GremlinsAIException, gremlins_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Setup security middleware first
setup_security_middleware(app)

# Setup monitoring middleware
setup_monitoring_middleware(app)

# Setup distributed tracing
tracing_service.instrument_fastapi(app)

# Include the API routers from different modules
app.include_router(auth.router, prefix="/api/v1", tags=["Authentication"])  # Add auth router first
app.include_router(agent.router, prefix="/api/v1/agent", tags=["Agent"])
app.include_router(multi_agent.router, prefix="/api/v1/multi-agent", tags=["Multi-Agent"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents & RAG"])
app.include_router(chat_history.router, prefix="/api/v1/history", tags=["Chat History"])
app.include_router(orchestrator.router, prefix="/api/v1/orchestrator", tags=["Orchestrator"])
app.include_router(websocket_endpoints.router, prefix="/api/v1/ws", tags=["WebSocket"])
app.include_router(realtime.router, prefix="/api/v1/realtime", tags=["Real-time API"])
app.include_router(docs.router, prefix="/docs", tags=["Documentation"])
app.include_router(developer_portal.router, prefix="/developer-portal", tags=["Developer Portal"])
app.include_router(multimodal.router, prefix="/api/v1/multimodal", tags=["Multi-Modal"])
app.include_router(health.router, prefix="/api/v1/health", tags=["Health & Monitoring"])
app.include_router(oauth.router, prefix="/api/v1/oauth", tags=["OAuth Authentication"])
app.include_router(metrics.router, prefix="/api/v1", tags=["Monitoring"])


# Simple root health endpoint for Phase 0 acceptance
@app.get("/health", tags=["Health"])
async def health_root():
    return {"status": "ok"}

@app.get("/", tags=["Root"])
async def read_root():
    """
    A simple root endpoint to confirm the API is running.
    """
    return {
        "message": "Welcome to the gremlinsAI API!",
        "version": "9.0.0",
        "features": [
            "REST API",
            "GraphQL API",
            "WebSocket Real-time Communication",
            "Multi-Agent Workflows",
            "Document Management & RAG",
            "Asynchronous Task Orchestration",
            "Developer Tools & SDKs",
            "Interactive Documentation",
            "Developer Portal",
            "Multi-Modal Processing (Audio, Video, Image)"
        ],
        "endpoints": {
            "rest_api": "/docs",
            "graphql": "/graphql",
            "websocket": "/api/v1/ws/ws",
            "multimodal": "/api/v1/multimodal"
        }
    }


# Add GraphQL endpoint
try:
    from strawberry.fastapi import GraphQLRouter
    from app.api.v1.graphql.schema import graphql_schema

    graphql_app = GraphQLRouter(graphql_schema)
    app.include_router(graphql_app, prefix="/graphql", tags=["GraphQL"])

    import logging
    logger = logging.getLogger(__name__)
    logger.info("GraphQL endpoints successfully enabled")

except Exception as e:
    # Graceful fallback if there are any issues
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"GraphQL not available due to error: {e}")

    @app.get("/graphql", tags=["GraphQL"])
    async def graphql_unavailable():
        return {
            "error": "GraphQL not available",
            "message": f"GraphQL setup failed: {str(e)}",
            "install_command": "pip install strawberry-graphql[fastapi]"
        }
