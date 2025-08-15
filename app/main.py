# app/main.py
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager

from app.api.v1.endpoints import agent, chat_history, orchestrator, multi_agent, documents, realtime, docs, developer_portal
from app.api.v1.websocket import endpoints as websocket_endpoints
from app.database.database import ensure_data_directory


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    ensure_data_directory()
    yield
    # Shutdown
    pass


# Create the main FastAPI application instance
app = FastAPI(
    title="gremlinsAI",
    description="API for the gremlinsAI multi-modal agentic system with advanced multi-agent architecture, RAG capabilities, asynchronous task orchestration, and real-time communication.",
    version="8.0.0",  # Updated for Phase 8
    lifespan=lifespan
)

# Global Error Handling
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"code": "VALIDATION_ERROR", "message": "Input validation failed", "details": exc.errors()},
    )

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

@app.get("/", tags=["Root"])
async def read_root():
    """
    A simple root endpoint to confirm the API is running.
    """
    return {
        "message": "Welcome to the gremlinsAI API!",
        "version": "8.0.0",
        "features": [
            "REST API",
            "GraphQL API",
            "WebSocket Real-time Communication",
            "Multi-Agent Workflows",
            "Document Management & RAG",
            "Asynchronous Task Orchestration",
            "Developer Tools & SDKs",
            "Interactive Documentation",
            "Developer Portal"
        ],
        "endpoints": {
            "rest_api": "/docs",
            "graphql": "/graphql",
            "websocket": "/api/v1/ws/ws"
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
