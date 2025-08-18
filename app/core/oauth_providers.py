# app/core/oauth_providers.py
"""
OAuth provider configurations for GremlinsAI backend.

This module contains OAuth provider configurations and endpoints for
Google OAuth2 and future Microsoft Azure OAuth2 integration.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum


class OAuthProvider(str, Enum):
    """Supported OAuth providers."""
    GOOGLE = "google"
    AZURE = "azure"


@dataclass
class GoogleOAuthConfig:
    """Google OAuth2 configuration and endpoints."""
    
    # OAuth endpoints
    authorization_url: str = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url: str = "https://oauth2.googleapis.com/token"
    userinfo_url: str = "https://www.googleapis.com/oauth2/v2/userinfo"
    revoke_url: str = "https://oauth2.googleapis.com/revoke"
    
    # OAuth scopes
    scopes: List[str] = None
    
    # OAuth parameters
    response_type: str = "code"
    access_type: str = "offline"
    prompt: str = "consent"
    
    def __post_init__(self):
        """Initialize default scopes if not provided."""
        if self.scopes is None:
            self.scopes = [
                "openid",
                "email", 
                "profile"
            ]
    
    def get_authorization_params(self, client_id: str, redirect_uri: str, state: str) -> Dict[str, str]:
        """Get authorization URL parameters."""
        return {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(self.scopes),
            "response_type": self.response_type,
            "access_type": self.access_type,
            "prompt": self.prompt,
            "state": state
        }
    
    def get_token_params(self, client_id: str, client_secret: str, 
                        redirect_uri: str, code: str) -> Dict[str, str]:
        """Get token exchange parameters."""
        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "code": code,
            "grant_type": "authorization_code"
        }


@dataclass
class AzureOAuthConfig:
    """Microsoft Azure OAuth2 configuration and endpoints."""
    
    # Base URLs (will be formatted with tenant_id)
    base_url: str = "https://login.microsoftonline.com"
    
    # OAuth scopes
    scopes: List[str] = None
    
    # OAuth parameters
    response_type: str = "code"
    response_mode: str = "query"
    
    def __post_init__(self):
        """Initialize default scopes if not provided."""
        if self.scopes is None:
            self.scopes = [
                "openid",
                "email",
                "profile",
                "User.Read"
            ]
    
    def get_authorization_url(self, tenant_id: str) -> str:
        """Get authorization URL for specific tenant."""
        return f"{self.base_url}/{tenant_id}/oauth2/v2.0/authorize"
    
    def get_token_url(self, tenant_id: str) -> str:
        """Get token URL for specific tenant."""
        return f"{self.base_url}/{tenant_id}/oauth2/v2.0/token"
    
    def get_userinfo_url(self) -> str:
        """Get user info URL."""
        return "https://graph.microsoft.com/v1.0/me"
    
    def get_authorization_params(self, client_id: str, redirect_uri: str, 
                               state: str) -> Dict[str, str]:
        """Get authorization URL parameters."""
        return {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(self.scopes),
            "response_type": self.response_type,
            "response_mode": self.response_mode,
            "state": state
        }
    
    def get_token_params(self, client_id: str, client_secret: str,
                        redirect_uri: str, code: str) -> Dict[str, str]:
        """Get token exchange parameters."""
        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "code": code,
            "grant_type": "authorization_code"
        }


class OAuthProviderFactory:
    """Factory for creating OAuth provider configurations."""
    
    @staticmethod
    def get_google_config() -> GoogleOAuthConfig:
        """Get Google OAuth configuration."""
        return GoogleOAuthConfig()
    
    @staticmethod
    def get_azure_config() -> AzureOAuthConfig:
        """Get Azure OAuth configuration."""
        return AzureOAuthConfig()
    
    @staticmethod
    def get_provider_config(provider: OAuthProvider):
        """Get configuration for specified provider."""
        if provider == OAuthProvider.GOOGLE:
            return OAuthProviderFactory.get_google_config()
        elif provider == OAuthProvider.AZURE:
            return OAuthProviderFactory.get_azure_config()
        else:
            raise ValueError(f"Unsupported OAuth provider: {provider}")


# Provider configurations
GOOGLE_OAUTH_CONFIG = GoogleOAuthConfig()
AZURE_OAUTH_CONFIG = AzureOAuthConfig()

# Provider mapping
OAUTH_PROVIDERS = {
    OAuthProvider.GOOGLE: GOOGLE_OAUTH_CONFIG,
    OAuthProvider.AZURE: AZURE_OAUTH_CONFIG
}


def get_oauth_provider_config(provider: str):
    """Get OAuth provider configuration by name."""
    try:
        provider_enum = OAuthProvider(provider.lower())
        return OAUTH_PROVIDERS[provider_enum]
    except (ValueError, KeyError):
        raise ValueError(f"Unsupported OAuth provider: {provider}")


def get_supported_providers() -> List[str]:
    """Get list of supported OAuth providers."""
    return [provider.value for provider in OAuthProvider]


def is_provider_supported(provider: str) -> bool:
    """Check if OAuth provider is supported."""
    return provider.lower() in [p.value for p in OAuthProvider]
