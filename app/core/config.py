# app/core/config.py
"""
Configuration management for GremlinsAI backend.

This module provides centralized configuration management for the application,
including OAuth2 settings, database configuration, and other environment variables.
"""

import os
import logging
from typing import Optional, List
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import field_validator

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Core Application Settings
    app_name: str = "GremlinsAI Backend"
    app_version: str = "9.0.0"
    debug: bool = False
    log_level: str = "INFO"
    
    # Database Configuration
    database_url: str = "sqlite:///./data/gremlinsai.db"
    
    # Security Settings
    secret_key: str = "your-secret-key-change-in-production"
    access_token_expire_minutes: int = 30
    
    # Google OAuth2 Configuration
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    oauth_redirect_url: str = "http://localhost:8000/api/v1/oauth/google/callback"
    
    # Microsoft Azure OAuth2 Configuration (for future use)
    azure_client_id: Optional[str] = None
    azure_client_secret: Optional[str] = None
    azure_tenant_id: Optional[str] = None
    
    # External Services
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection_name: str = "gremlinsai_collection"
    
    redis_url: str = "redis://localhost:6379"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    
    # LLM Configuration
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 2048

    # Hugging Face Configuration
    use_huggingface: bool = False
    hf_model: str = "microsoft/DialoGPT-medium"

    # LlamaCpp Configuration
    llamacpp_model_path: str = "./models/llama-2-7b-chat.gguf"

    # MinIO Configuration
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"

    # Kafka Configuration
    kafka_broker_urls: str = "localhost:9092"

    # Embedding Configuration
    embedding_model: str = "all-MiniLM-L6-v2"
    qdrant_collection: str = "gremlins_documents"

    # Multi-Modal Configuration
    multimodal_storage_path: str = "./data/multimodal"
    enable_multimodal_processing: bool = True

    # Development Settings
    testing: bool = False
    
    # API Configuration
    api_v1_prefix: str = "/api/v1"
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000"
    ]
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        """Parse CORS origins from environment variable."""
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False
    }


class OAuthConfig:
    """OAuth provider configuration."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
    
    @property
    def google_enabled(self) -> bool:
        """Check if Google OAuth is enabled."""
        return bool(self.settings.google_client_id and self.settings.google_client_secret)
    
    @property
    def azure_enabled(self) -> bool:
        """Check if Azure OAuth is enabled."""
        return bool(
            self.settings.azure_client_id and 
            self.settings.azure_client_secret and 
            self.settings.azure_tenant_id
        )
    
    @property
    def enabled_providers(self) -> List[str]:
        """Get list of enabled OAuth providers."""
        providers = []
        if self.google_enabled:
            providers.append("google")
        if self.azure_enabled:
            providers.append("azure")
        return providers
    
    def get_google_config(self) -> dict:
        """Get Google OAuth configuration."""
        if not self.google_enabled:
            raise ValueError("Google OAuth is not configured")
        
        return {
            "client_id": self.settings.google_client_id,
            "client_secret": self.settings.google_client_secret,
            "redirect_uri": self.settings.oauth_redirect_url,
            "scope": "openid email profile"
        }
    
    def get_azure_config(self) -> dict:
        """Get Azure OAuth configuration."""
        if not self.azure_enabled:
            raise ValueError("Azure OAuth is not configured")
        
        return {
            "client_id": self.settings.azure_client_id,
            "client_secret": self.settings.azure_client_secret,
            "tenant_id": self.settings.azure_tenant_id,
            "redirect_uri": self.settings.oauth_redirect_url.replace("/google/", "/azure/"),
            "scope": "openid email profile"
        }


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


@lru_cache()
def get_oauth_config() -> OAuthConfig:
    """Get cached OAuth configuration."""
    return OAuthConfig(get_settings())


# Global settings instance
settings = get_settings()
oauth_config = get_oauth_config()
