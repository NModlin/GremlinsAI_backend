# app/main.py
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.endpoints import agent, chat_history, orchestrator, multi_agent, documents, realtime, docs, developer_portal, multimodal, health, oauth, metrics
from app.api.v1.websocket import endpoints as websocket_endpoints
from app.database.database import ensure_data_directory
from app.core.exceptions import GremlinsAIException
from app.core.error_handlers import (
    gremlins_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    sqlalchemy_exception_handler,
    general_exception_handler
)
from app.middleware.monitoring import PrometheusMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    ensure_data_directory()

    # Initialize service monitoring
    from app.core.service_monitor import initialize_service_monitoring
    initialize_service_monitoring()

    yield
    # Shutdown
    pass


# Create the main FastAPI application instance
app = FastAPI(
    title="gremlinsAI",
    description="API for the gremlinsAI multi-modal agentic system with advanced multi-agent architecture, RAG capabilities, asynchronous task orchestration, and real-time communication.",
    version="9.0.0",  # Updated for Phase 8
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
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

# Include the API routers from different modules
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
