# tests/test_oauth.py
"""
Basic tests for OAuth authentication system.

Tests OAuth service functionality, API endpoints, and user management.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.main import app
from app.database.models import OAuthUser
from app.services.oauth_service import OAuthService
from app.core.config import settings, oauth_config
from app.core.security import hash_api_key


class TestOAuthService:
    """Test OAuth service functionality."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def oauth_service(self, mock_db_session):
        """OAuth service instance with mocked database."""
        return OAuthService(mock_db_session)
    
    def test_generate_oauth_api_key(self, oauth_service):
        """Test OAuth API key generation."""
        api_key = oauth_service._generate_oauth_api_key()
        
        assert api_key.startswith("gai_")
        assert len(api_key) > 10  # Should be longer than just the prefix
        
        # Test uniqueness
        api_key2 = oauth_service._generate_oauth_api_key()
        assert api_key != api_key2
    
    @pytest.mark.asyncio
    async def test_get_google_authorization_url(self, oauth_service):
        """Test Google authorization URL generation."""
        with patch.object(oauth_config, 'google_enabled', True):
            with patch.object(oauth_config, 'get_google_config') as mock_config:
                mock_config.return_value = {
                    "client_id": "test_client_id",
                    "client_secret": "test_client_secret",
                    "redirect_uri": "http://localhost:8000/api/v1/oauth/google/callback",
                    "scope": "openid email profile"
                }
                
                auth_url = await oauth_service.get_google_authorization_url("test_state")
                
                assert "accounts.google.com" in auth_url
                assert "client_id=test_client_id" in auth_url
                assert "state=test_state" in auth_url
                assert "scope=openid+email+profile" in auth_url
    
    @pytest.mark.asyncio
    async def test_create_new_oauth_user(self, oauth_service, mock_db_session):
        """Test creating a new OAuth user."""
        user_info = {
            "id": "google_123",
            "email": "test@example.com",
            "name": "Test User",
            "picture": "https://example.com/avatar.jpg"
        }
        
        # Mock database query to return no existing user
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
        
        # Mock the new user creation
        mock_user = Mock(spec=OAuthUser)
        mock_user.id = "user_123"
        mock_user.email = "test@example.com"
        mock_user.name = "Test User"
        mock_user.provider = "google"
        mock_user.api_key = "gai_test_key"
        
        mock_db_session.refresh = AsyncMock()
        mock_db_session.commit = AsyncMock()
        
        with patch('app.services.oauth_service.OAuthUser') as mock_oauth_user_class:
            mock_oauth_user_class.return_value = mock_user
            
            result = await oauth_service.create_or_update_user("google", user_info)
            
            assert result == mock_user
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_existing_oauth_user(self, oauth_service, mock_db_session):
        """Test updating an existing OAuth user."""
        user_info = {
            "id": "google_123",
            "email": "test@example.com",
            "name": "Updated Name",
            "picture": "https://example.com/new_avatar.jpg"
        }
        
        # Mock existing user
        existing_user = Mock(spec=OAuthUser)
        existing_user.email = "test@example.com"
        existing_user.name = "Old Name"
        existing_user.provider = "google"
        
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = existing_user
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()
        
        result = await oauth_service.create_or_update_user("google", user_info)
        
        assert result == existing_user
        assert existing_user.name == "Updated Name"
        mock_db_session.commit.assert_called_once()


class TestOAuthEndpoints:
    """Test OAuth API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Test client."""
        return TestClient(app)
    
    def test_get_oauth_providers(self, client):
        """Test getting available OAuth providers."""
        response = client.get("/api/v1/oauth/providers")
        
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert "total_enabled" in data
        assert isinstance(data["providers"], list)
    
    def test_oauth_status(self, client):
        """Test OAuth status endpoint."""
        response = client.get("/api/v1/oauth/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "oauth_enabled" in data
        assert "providers" in data
        assert "google" in data["providers"]
        assert "azure" in data["providers"]
    
    def test_google_login_redirect(self, client):
        """Test Google OAuth login redirect."""
        with patch.object(oauth_config, 'google_enabled', True):
            with patch.object(oauth_config, 'get_google_config') as mock_config:
                mock_config.return_value = {
                    "client_id": "test_client_id",
                    "client_secret": "test_client_secret",
                    "redirect_uri": "http://localhost:8000/api/v1/oauth/google/callback",
                    "scope": "openid email profile"
                }
                
                response = client.get("/api/v1/oauth/google/login", allow_redirects=False)
                
                assert response.status_code == 307  # Redirect
                assert "accounts.google.com" in response.headers["location"]
    
    def test_google_callback_missing_code(self, client):
        """Test Google OAuth callback without authorization code."""
        response = client.get("/api/v1/oauth/google/callback")
        
        assert response.status_code == 422  # Validation error for missing required parameter
    
    def test_google_callback_with_error(self, client):
        """Test Google OAuth callback with error parameter."""
        response = client.get("/api/v1/oauth/google/callback?error=access_denied")
        
        assert response.status_code == 400
        data = response.json()
        assert "OAuth authentication failed" in data["detail"]
    
    def test_azure_login_not_configured(self, client):
        """Test Azure OAuth login when not configured."""
        with patch.object(oauth_config, 'azure_enabled', False):
            response = client.get("/api/v1/oauth/azure/login")
            
            assert response.status_code == 200  # Returns coming soon message
            data = response.json()
            assert data["status"] == "coming_soon"
            assert data["provider"] == "azure"


class TestOAuthSecurity:
    """Test OAuth security integration."""
    
    def test_oauth_api_key_format(self):
        """Test OAuth API key format validation."""
        from app.services.oauth_service import OAuthService
        
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        service = OAuthService(mock_db)
        
        api_key = service._generate_oauth_api_key()
        
        # Should start with gai_ prefix
        assert api_key.startswith("gai_")
        
        # Should be long enough to be secure
        assert len(api_key) >= 32
    
    def test_api_key_hash_consistency(self):
        """Test API key hashing consistency."""
        api_key = "gai_test_key_12345"
        
        hash1 = hash_api_key(api_key)
        hash2 = hash_api_key(api_key)
        
        # Same key should produce same hash
        assert hash1 == hash2
        
        # Different keys should produce different hashes
        different_key = "gai_different_key_67890"
        hash3 = hash_api_key(different_key)
        assert hash1 != hash3


class TestOAuthConfiguration:
    """Test OAuth configuration management."""
    
    def test_oauth_config_google_enabled(self):
        """Test Google OAuth configuration detection."""
        with patch.object(settings, 'google_client_id', 'test_id'):
            with patch.object(settings, 'google_client_secret', 'test_secret'):
                assert oauth_config.google_enabled
    
    def test_oauth_config_google_disabled(self):
        """Test Google OAuth disabled when not configured."""
        with patch.object(settings, 'google_client_id', None):
            with patch.object(settings, 'google_client_secret', None):
                assert not oauth_config.google_enabled
    
    def test_oauth_config_azure_enabled(self):
        """Test Azure OAuth configuration detection."""
        with patch.object(settings, 'azure_client_id', 'test_id'):
            with patch.object(settings, 'azure_client_secret', 'test_secret'):
                with patch.object(settings, 'azure_tenant_id', 'test_tenant'):
                    assert oauth_config.azure_enabled
    
    def test_oauth_config_azure_disabled(self):
        """Test Azure OAuth disabled when not configured."""
        with patch.object(settings, 'azure_client_id', None):
            with patch.object(settings, 'azure_client_secret', None):
                with patch.object(settings, 'azure_tenant_id', None):
                    assert not oauth_config.azure_enabled


if __name__ == "__main__":
    pytest.main([__file__])
