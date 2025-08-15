# app/database/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Get database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/gremlinsai.db")

# Convert SQLite URL to async version for aiosqlite
if DATABASE_URL.startswith("sqlite:///"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")
else:
    ASYNC_DATABASE_URL = DATABASE_URL

# Create sync engine for Alembic migrations
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})

# Create async engine for FastAPI
async_engine = create_async_engine(ASYNC_DATABASE_URL, echo=False)

# Create session makers
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

# Create base class for models
Base = declarative_base()

# Dependency to get database session
async def get_db():
    """Dependency to get async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Create data directory if it doesn't exist
def ensure_data_directory():
    """Ensure the data directory exists for SQLite database."""
    if "sqlite" in DATABASE_URL:
        data_dir = os.path.dirname(DATABASE_URL.replace("sqlite:///", ""))
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
