# app/main.py
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from app.api.v1.endpoints import agent, chat_history, orchestrator, multi_agent, documents, realtime, docs, developer_portal, multimodal, health, websocket as websocket_realtime, auth, simple_chat, simple_docs, document_upload
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    ensure_data_directory()

    # Initialize service monitoring
    from app.core.service_monitor import initialize_service_monitoring
    initialize_service_monitoring()

    # Check and log LLM status on startup
    try:
        from app.core.llm_config import get_llm_info, get_llm_health_status
        import logging

        logger = logging.getLogger(__name__)
        llm_info = get_llm_info()
        health_status = get_llm_health_status()

        logger.info(f"🧙‍♂️ GremlinsAI starting with LLM provider: {llm_info['provider']}")
        logger.info(f"Model: {llm_info['model_name']}")
        logger.info(f"LLM Available: {llm_info['available']}")
        logger.info(f"Health Status: {health_status['status']} (Score: {health_status['health_score']}/100)")

        if not llm_info['available']:
            logger.warning("⚠️  No real LLM configured - using mock responses")
            logger.warning("💡 Configure LLM: python scripts/setup_local_llm.py")
        elif health_status['status'] == 'unhealthy':
            logger.warning("⚠️  LLM health issues detected")
            for issue in health_status.get('issues', []):
                logger.warning(f"   - {issue}")
        else:
            logger.info("✅ LLM system ready!")

    except Exception as e:
        logger.error(f"Failed to check LLM status on startup: {e}")

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
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(agent.router, prefix="/api/v1/agent", tags=["Agent"])
app.include_router(simple_chat.router, prefix="/api/v1/agent", tags=["Simple Chat"])
app.include_router(simple_docs.router, prefix="/api/v1", tags=["Simple Documentation"])
app.include_router(multi_agent.router, prefix="/api/v1/multi-agent", tags=["Multi-Agent"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents & RAG"])
app.include_router(document_upload.router, prefix="/api/v1/upload", tags=["Document Upload & RAG"])
app.include_router(chat_history.router, prefix="/api/v1/history", tags=["Chat History"])
app.include_router(orchestrator.router, prefix="/api/v1/orchestrator", tags=["Orchestrator"])
app.include_router(websocket_endpoints.router, prefix="/api/v1/ws", tags=["WebSocket"])
app.include_router(websocket_realtime.router, prefix="/api/v1/realtime-ws", tags=["Real-time WebSocket"])
app.include_router(realtime.router, prefix="/api/v1/realtime", tags=["Real-time API"])
app.include_router(docs.router, prefix="/docs", tags=["Documentation"])
app.include_router(developer_portal.router, prefix="/api/v1/developer-portal", tags=["Developer Portal"])
app.include_router(multimodal.router, prefix="/api/v1/multimodal", tags=["Multi-Modal"])
app.include_router(health.router, prefix="/api/v1/health", tags=["Health & Monitoring"])

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

except ImportError:
    # Graceful fallback if strawberry is not installed
    import logging
    logger = logging.getLogger(__name__)
    logger.warning("Strawberry GraphQL not available. GraphQL endpoints disabled.")

    @app.get("/graphql", tags=["GraphQL"])
    async def graphql_unavailable():
        return {
            "error": "GraphQL not available",
            "message": "Install strawberry-graphql[fastapi] to enable GraphQL endpoints",
            "install_command": "pip install strawberry-graphql[fastapi]"
        }
