# app/main.py
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager

from app.api.v1.endpoints import agent, chat_history, orchestrator
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
    description="API for the gremlinsAI multi-modal agentic system.",
    version="2.0.0",  # Updated for Phase 2
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
app.include_router(chat_history.router, prefix="/api/v1/history", tags=["Chat History"])
app.include_router(orchestrator.router, prefix="/api/v1/orchestrator", tags=["Orchestrator"])

@app.get("/", tags=["Root"])
async def read_root():
    """
    A simple root endpoint to confirm the API is running.
    """
    return {"message": "Welcome to the gremlinsAI API!"}
