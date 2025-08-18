# app/core/config.py
"""
Production Configuration Management for GremlinsAI backend.

This module provides secure, environment-aware configuration management with:
- Environment-specific settings (dev/staging/prod)
- Secrets management integration
- Validation and security controls
- No hardcoded sensitive values

Supports multiple secrets backends:
- HashiCorp Vault
- AWS Secrets Manager
- Google Secret Manager
- Azure Key Vault
- Environment variables (development fallback)
"""

import os
import json
import logging
from enum import Enum
from typing import Optional, List, Dict, Any, Union
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Environment(str, Enum):
    """Application environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class SecretsBackend(str, Enum):
    """Supported secrets management backends."""
    ENVIRONMENT = "environment"  # Environment variables (dev fallback)
    VAULT = "vault"              # HashiCorp Vault
    AWS_SECRETS = "aws_secrets"  # AWS Secrets Manager
    GCP_SECRETS = "gcp_secrets"  # Google Secret Manager
    AZURE_KEYVAULT = "azure_keyvault"  # Azure Key Vault


class SecretsManager:
    """
    Secrets management integration for multiple backends.

    Setup Instructions:

    1. HashiCorp Vault:
       - Set VAULT_URL and VAULT_TOKEN environment variables
       - Ensure vault is accessible and token has read permissions

    2. AWS Secrets Manager:
       - Configure AWS credentials (IAM role, access keys, or instance profile)
       - Set AWS_REGION environment variable

    3. Google Secret Manager:
       - Set GOOGLE_APPLICATION_CREDENTIALS to service account key file
       - Ensure service account has Secret Manager Secret Accessor role

    4. Azure Key Vault:
       - Set AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID
       - Or use managed identity in Azure environments
    """

    def __init__(self, backend: SecretsBackend, config: Dict[str, Any] = None):
        self.backend = backend
        self.config = config or {}
        self._client = None

    def get_secret(self, secret_name: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieve a secret from the configured backend."""
        try:
            if self.backend == SecretsBackend.ENVIRONMENT:
                return os.getenv(secret_name, default)

            elif self.backend == SecretsBackend.VAULT:
                return self._get_vault_secret(secret_name, default)

            elif self.backend == SecretsBackend.AWS_SECRETS:
                return self._get_aws_secret(secret_name, default)

            elif self.backend == SecretsBackend.GCP_SECRETS:
                return self._get_gcp_secret(secret_name, default)

            elif self.backend == SecretsBackend.AZURE_KEYVAULT:
                return self._get_azure_secret(secret_name, default)

            else:
                logger.warning(f"Unknown secrets backend: {self.backend}")
                return default

        except Exception as e:
            logger.error(f"Failed to retrieve secret '{secret_name}': {e}")
            return default

    def _get_vault_secret(self, secret_name: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieve secret from HashiCorp Vault."""
        try:
            import hvac

            if not self._client:
                vault_url = os.getenv("VAULT_URL", "http://localhost:8200")
                vault_token = os.getenv("VAULT_TOKEN")

                if not vault_token:
                    logger.warning("VAULT_TOKEN not set, falling back to default")
                    return default

                self._client = hvac.Client(url=vault_url, token=vault_token)

            # Read from KV v2 secrets engine
            secret_path = f"secret/data/{secret_name}"
            response = self._client.secrets.kv.v2.read_secret_version(path=secret_name)

            if response and 'data' in response and 'data' in response['data']:
                return response['data']['data'].get('value', default)

            return default

        except ImportError:
            logger.warning("hvac library not installed, install with: pip install hvac")
            return default
        except Exception as e:
            logger.error(f"Vault secret retrieval failed: {e}")
            return default

    def _get_aws_secret(self, secret_name: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieve secret from AWS Secrets Manager."""
        try:
            import boto3
            from botocore.exceptions import ClientError

            if not self._client:
                region = os.getenv("AWS_REGION", "us-east-1")
                self._client = boto3.client("secretsmanager", region_name=region)

            response = self._client.get_secret_value(SecretId=secret_name)
            return response.get("SecretString", default)

        except ImportError:
            logger.warning("boto3 library not installed, install with: pip install boto3")
            return default
        except ClientError as e:
            logger.error(f"AWS Secrets Manager retrieval failed: {e}")
            return default
        except Exception as e:
            logger.error(f"AWS secret retrieval failed: {e}")
            return default

    def _get_gcp_secret(self, secret_name: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieve secret from Google Secret Manager."""
        try:
            from google.cloud import secretmanager

            if not self._client:
                self._client = secretmanager.SecretManagerServiceClient()

            project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
            if not project_id:
                logger.warning("GOOGLE_CLOUD_PROJECT not set")
                return default

            name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
            response = self._client.access_secret_version(request={"name": name})

            return response.payload.data.decode("UTF-8")

        except ImportError:
            logger.warning("google-cloud-secret-manager not installed, install with: pip install google-cloud-secret-manager")
            return default
        except Exception as e:
            logger.error(f"GCP Secret Manager retrieval failed: {e}")
            return default

    def _get_azure_secret(self, secret_name: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieve secret from Azure Key Vault."""
        try:
            from azure.keyvault.secrets import SecretClient
            from azure.identity import DefaultAzureCredential

            if not self._client:
                vault_url = os.getenv("AZURE_KEY_VAULT_URL")
                if not vault_url:
                    logger.warning("AZURE_KEY_VAULT_URL not set")
                    return default

                credential = DefaultAzureCredential()
                self._client = SecretClient(vault_url=vault_url, credential=credential)

            secret = self._client.get_secret(secret_name)
            return secret.value

        except ImportError:
            logger.warning("azure-keyvault-secrets not installed, install with: pip install azure-keyvault-secrets azure-identity")
            return default
        except Exception as e:
            logger.error(f"Azure Key Vault retrieval failed: {e}")
            return default


class Settings(BaseSettings):
    """
    Production-ready application settings with environment-specific configuration
    and secure secrets management.

    Environment Variables Required:
    - ENVIRONMENT: development|staging|production|testing
    - SECRETS_BACKEND: environment|vault|aws_secrets|gcp_secrets|azure_keyvault

    All sensitive values are retrieved from the configured secrets backend.
    """

    # ===== CORE APPLICATION SETTINGS =====
    app_name: str = Field(default="GremlinsAI Backend", description="Application name")
    app_version: str = Field(default="9.0.0", description="Application version")
    environment: Environment = Field(default=Environment.DEVELOPMENT, description="Deployment environment")
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    # ===== SECRETS MANAGEMENT =====
    secrets_backend: SecretsBackend = Field(default=SecretsBackend.ENVIRONMENT, description="Secrets management backend")

    # ===== DATABASE CONFIGURATION =====
    database_url: str = Field(default="sqlite:///./data/gremlinsai.db", description="Database connection URL")
    database_pool_size: int = Field(default=10, description="Database connection pool size")
    database_max_overflow: int = Field(default=20, description="Database max overflow connections")

    # ===== SECURITY SETTINGS =====
    # These will be loaded from secrets manager
    secret_key: Optional[str] = Field(default=None, description="JWT secret key (from secrets manager)")
    access_token_expire_minutes: int = Field(default=30, description="JWT token expiration time")
    refresh_token_expire_days: int = Field(default=7, description="Refresh token expiration time")

    # ===== OAUTH2 CONFIGURATION =====
    # OAuth secrets loaded from secrets manager
    google_client_id: Optional[str] = Field(default=None, description="Google OAuth client ID")
    google_client_secret: Optional[str] = Field(default=None, description="Google OAuth client secret (from secrets)")
    oauth_redirect_url: str = Field(default="http://localhost:8000/api/v1/oauth/google/callback", description="OAuth redirect URL")

    # Microsoft Azure OAuth2
    azure_client_id: Optional[str] = Field(default=None, description="Azure OAuth client ID")
    azure_client_secret: Optional[str] = Field(default=None, description="Azure OAuth client secret (from secrets)")
    azure_tenant_id: Optional[str] = Field(default=None, description="Azure tenant ID")

    # ===== LLM PROVIDER CONFIGURATION =====
    # API keys loaded from secrets manager
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key (from secrets)")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key (from secrets)")
    huggingface_api_key: Optional[str] = Field(default=None, description="Hugging Face API key (from secrets)")

    # Ollama Configuration
    ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama server URL")
    ollama_model: str = Field(default="llama3.2:3b", description="Default Ollama model")

    # LLM Settings
    llm_temperature: float = Field(default=0.1, ge=0.0, le=2.0, description="LLM temperature")
    llm_max_tokens: int = Field(default=2048, ge=1, le=32000, description="Maximum tokens per request")
    llm_timeout: int = Field(default=60, description="LLM request timeout in seconds")

    # Hugging Face Configuration
    use_huggingface: bool = Field(default=False, description="Enable Hugging Face models")
    hf_model: str = Field(default="microsoft/DialoGPT-medium", description="Default HF model")

    # LlamaCpp Configuration
    llamacpp_model_path: str = Field(default="./models/llama-2-7b-chat.gguf", description="LlamaCpp model path")

    # ===== VECTOR DATABASE CONFIGURATION =====
    # Weaviate Configuration
    weaviate_url: str = Field(default="http://localhost:8080", description="Weaviate server URL")
    weaviate_api_key: Optional[str] = Field(default=None, description="Weaviate API key (from secrets)")
    weaviate_timeout: int = Field(default=30, description="Weaviate request timeout")

    # Qdrant Configuration (legacy support)
    qdrant_host: str = Field(default="localhost", description="Qdrant host")
    qdrant_port: int = Field(default=6333, description="Qdrant port")
    qdrant_collection_name: str = Field(default="gremlinsai_collection", description="Qdrant collection name")
    qdrant_api_key: Optional[str] = Field(default=None, description="Qdrant API key (from secrets)")

    # ===== CACHE AND MESSAGE BROKER =====
    redis_url: str = Field(default="redis://localhost:6379", description="Redis connection URL")
    redis_password: Optional[str] = Field(default=None, description="Redis password (from secrets)")
    redis_timeout: int = Field(default=5, description="Redis connection timeout")

    # Celery Configuration
    celery_broker_url: str = Field(default="redis://localhost:6379/0", description="Celery broker URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/0", description="Celery result backend")

    # ===== OBJECT STORAGE =====
    # MinIO/S3 Configuration
    minio_endpoint: str = Field(default="localhost:9000", description="MinIO/S3 endpoint")
    minio_access_key: Optional[str] = Field(default=None, description="MinIO access key (from secrets)")
    minio_secret_key: Optional[str] = Field(default=None, description="MinIO secret key (from secrets)")
    minio_bucket: str = Field(default="gremlinsai", description="Default storage bucket")
    minio_secure: bool = Field(default=False, description="Use HTTPS for MinIO")

    # ===== MESSAGE STREAMING =====
    kafka_broker_urls: str = Field(default="localhost:9092", description="Kafka broker URLs")
    kafka_username: Optional[str] = Field(default=None, description="Kafka username")
    kafka_password: Optional[str] = Field(default=None, description="Kafka password (from secrets)")

    # ===== EMBEDDING AND SEARCH =====
    embedding_model: str = Field(default="all-MiniLM-L6-v2", description="Default embedding model")
    embedding_dimension: int = Field(default=384, description="Embedding vector dimension")

    # ===== MULTIMODAL PROCESSING =====
    multimodal_storage_path: str = Field(default="./data/multimodal", description="Multimodal files storage path")
    enable_multimodal_processing: bool = Field(default=True, description="Enable multimodal processing")
    max_file_size_mb: int = Field(default=100, description="Maximum file size in MB")

    # ===== API CONFIGURATION =====
    api_v1_prefix: str = Field(default="/api/v1", description="API v1 prefix")
    api_rate_limit: int = Field(default=100, description="API rate limit per minute")
    api_timeout: int = Field(default=30, description="API request timeout")

    # CORS Configuration
    cors_origins: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:8000",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000"
        ],
        description="Allowed CORS origins"
    )

    # ===== MONITORING AND OBSERVABILITY =====
    enable_metrics: bool = Field(default=True, description="Enable Prometheus metrics")
    metrics_port: int = Field(default=8001, description="Metrics server port")
    enable_tracing: bool = Field(default=False, description="Enable distributed tracing")
    jaeger_endpoint: Optional[str] = Field(default=None, description="Jaeger tracing endpoint")

    # Health Check Configuration
    health_check_interval: int = Field(default=30, description="Health check interval in seconds")

    # ===== DEVELOPMENT AND TESTING =====
    testing: bool = Field(default=False, description="Testing mode flag")
    mock_external_services: bool = Field(default=False, description="Mock external services for testing")

    # ===== MIGRATION SETTINGS =====
    dual_write_enabled: bool = Field(default=False, description="Enable dual-write to both SQLite and Weaviate")
    migration_mode: str = Field(default="sqlite_only", description="Migration mode: sqlite_only, dual_write, weaviate_primary")
    weaviate_primary: bool = Field(default=False, description="Use Weaviate as primary read source")
    
    # ===== PYDANTIC CONFIGURATION =====
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid",  # Prevent unknown fields
        validate_assignment=True,  # Validate on assignment
        use_enum_values=True,  # Use enum values in serialization
    )

    # ===== SECRETS MANAGER INSTANCE =====
    _secrets_manager: Optional[SecretsManager] = None

    def __init__(self, **kwargs):
        """Initialize settings and set up secrets manager."""
        super().__init__(**kwargs)
        self._setup_secrets_manager()
        self._load_secrets()

    def _setup_secrets_manager(self):
        """Initialize the secrets manager based on configuration."""
        self._secrets_manager = SecretsManager(
            backend=self.secrets_backend,
            config={}
        )

    def _load_secrets(self):
        """Load sensitive values from secrets manager."""
        if not self._secrets_manager:
            return

        # Load security secrets
        if not self.secret_key:
            self.secret_key = self._secrets_manager.get_secret("SECRET_KEY")

        # Load OAuth secrets
        if not self.google_client_secret:
            self.google_client_secret = self._secrets_manager.get_secret("GOOGLE_CLIENT_SECRET")

        if not self.azure_client_secret:
            self.azure_client_secret = self._secrets_manager.get_secret("AZURE_CLIENT_SECRET")

        # Load LLM API keys
        if not self.openai_api_key:
            self.openai_api_key = self._secrets_manager.get_secret("OPENAI_API_KEY")

        if not self.anthropic_api_key:
            self.anthropic_api_key = self._secrets_manager.get_secret("ANTHROPIC_API_KEY")

        if not self.huggingface_api_key:
            self.huggingface_api_key = self._secrets_manager.get_secret("HUGGINGFACE_API_KEY")

        # Load database and service secrets
        if not self.weaviate_api_key:
            self.weaviate_api_key = self._secrets_manager.get_secret("WEAVIATE_API_KEY")

        if not self.qdrant_api_key:
            self.qdrant_api_key = self._secrets_manager.get_secret("QDRANT_API_KEY")

        if not self.redis_password:
            self.redis_password = self._secrets_manager.get_secret("REDIS_PASSWORD")

        # Load storage secrets
        if not self.minio_access_key:
            self.minio_access_key = self._secrets_manager.get_secret("MINIO_ACCESS_KEY")

        if not self.minio_secret_key:
            self.minio_secret_key = self._secrets_manager.get_secret("MINIO_SECRET_KEY")

        # Load Kafka secrets
        if not self.kafka_password:
            self.kafka_password = self._secrets_manager.get_secret("KAFKA_PASSWORD")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        """Parse CORS origins from environment variable."""
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v

    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'log_level must be one of {valid_levels}')
        return v.upper()

    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v):
        """Validate environment setting."""
        if isinstance(v, str):
            try:
                return Environment(v.lower())
            except ValueError:
                valid_envs = [e.value for e in Environment]
                raise ValueError(f'environment must be one of {valid_envs}')
        return v

    @model_validator(mode='after')
    def validate_production_settings(self):
        """Validate production-specific requirements."""
        if self.environment == Environment.PRODUCTION:
            # Ensure critical secrets are set in production
            if not self.secret_key or self.secret_key == "your-secret-key-change-in-production":
                raise ValueError("SECRET_KEY must be set to a secure value in production")

            if self.debug:
                raise ValueError("Debug mode must be disabled in production")

            if self.log_level == "DEBUG":
                logger.warning("DEBUG logging enabled in production - consider using INFO or WARNING")

        return self

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == Environment.DEVELOPMENT

    @property
    def is_staging(self) -> bool:
        """Check if running in staging environment."""
        return self.environment == Environment.STAGING

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PRODUCTION

    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment == Environment.TESTING

    def get_database_url(self) -> str:
        """Get environment-specific database URL."""
        if self.is_testing:
            return "sqlite:///./test.db"
        elif self.is_development:
            return self.database_url
        else:
            # For staging/production, ensure we have a proper database URL
            if "sqlite" in self.database_url and not self.is_development:
                logger.warning("SQLite database detected in non-development environment")
            return self.database_url

    def get_redis_url(self) -> str:
        """Get Redis URL with password if configured."""
        if self.redis_password:
            # Parse URL and add password
            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(self.redis_url)
            if not parsed.password:
                # Add password to URL
                netloc = f":{self.redis_password}@{parsed.hostname}"
                if parsed.port:
                    netloc += f":{parsed.port}"
                parsed = parsed._replace(netloc=netloc)
                return urlunparse(parsed)
        return self.redis_url

    def get_cors_origins(self) -> List[str]:
        """Get environment-specific CORS origins."""
        if self.is_production:
            # Filter out localhost origins in production
            return [origin for origin in self.cors_origins if "localhost" not in origin and "127.0.0.1" not in origin]
        return self.cors_origins

    def mask_sensitive_values(self) -> Dict[str, Any]:
        """Get configuration dict with sensitive values masked for logging."""
        config_dict = self.model_dump()

        # List of sensitive fields to mask
        sensitive_fields = [
            'secret_key', 'google_client_secret', 'azure_client_secret',
            'openai_api_key', 'anthropic_api_key', 'huggingface_api_key',
            'weaviate_api_key', 'qdrant_api_key', 'redis_password',
            'minio_access_key', 'minio_secret_key', 'kafka_password'
        ]

        for field in sensitive_fields:
            if field in config_dict and config_dict[field]:
                config_dict[field] = "***MASKED***"

        return config_dict


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
