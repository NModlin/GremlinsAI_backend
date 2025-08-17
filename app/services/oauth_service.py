# app/services/oauth_service.py
"""
OAuth service for GremlinsAI backend.

This service handles OAuth authentication flows for Google and future Azure integration,
including user creation, API key generation, and token management.
"""

import logging
import secrets
import hashlib
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlencode
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.core.config import settings, oauth_config
from app.core.oauth_providers import (
    OAuthProvider, 
    GoogleOAuthConfig, 
    AzureOAuthConfig,
    get_oauth_provider_config
)
from app.database.models import OAuthUser
from app.core.security import hash_api_key

logger = logging.getLogger(__name__)


class OAuthService:
    """Service for handling OAuth authentication flows."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.google_config = GoogleOAuthConfig()
        self.azure_config = AzureOAuthConfig()
    
    async def get_google_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Generate Google OAuth authorization URL.
        
        Args:
            state: Optional state parameter for CSRF protection
            
        Returns:
            Authorization URL for Google OAuth
        """
        if not oauth_config.google_enabled:
            raise HTTPException(
                status_code=400, 
                detail="Google OAuth is not configured"
            )
        
        # Generate state if not provided
        if not state:
            state = secrets.token_urlsafe(32)
        
        # Get Google OAuth configuration
        google_settings = oauth_config.get_google_config()
        
        # Build authorization parameters
        params = self.google_config.get_authorization_params(
            client_id=google_settings["client_id"],
            redirect_uri=google_settings["redirect_uri"],
            state=state
        )
        
        # Build authorization URL
        auth_url = f"{self.google_config.authorization_url}?{urlencode(params)}"
        
        logger.info(f"Generated Google OAuth authorization URL with state: {state[:8]}...")
        return auth_url
    
    async def exchange_google_code_for_token(self, code: str, state: Optional[str] = None) -> Dict[str, Any]:
        """
        Exchange Google OAuth authorization code for access token.
        
        Args:
            code: Authorization code from Google
            state: State parameter for verification
            
        Returns:
            Token response from Google
        """
        if not oauth_config.google_enabled:
            raise HTTPException(
                status_code=400,
                detail="Google OAuth is not configured"
            )
        
        google_settings = oauth_config.get_google_config()
        
        # Prepare token exchange parameters
        token_params = self.google_config.get_token_params(
            client_id=google_settings["client_id"],
            client_secret=google_settings["client_secret"],
            redirect_uri=google_settings["redirect_uri"],
            code=code
        )
        
        # Exchange code for token
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.google_config.token_url,
                    data=token_params,
                    headers={"Accept": "application/json"}
                )
                response.raise_for_status()
                
                token_data = response.json()
                logger.info("Successfully exchanged Google OAuth code for token")
                return token_data
                
            except httpx.HTTPStatusError as e:
                logger.error(f"Google token exchange failed: {e.response.text}")
                raise HTTPException(
                    status_code=400,
                    detail="Failed to exchange authorization code for token"
                )
            except Exception as e:
                logger.error(f"Google token exchange error: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail="OAuth token exchange failed"
                )
    
    async def get_google_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Get user information from Google using access token.
        
        Args:
            access_token: Google access token
            
        Returns:
            User information from Google
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    self.google_config.userinfo_url,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/json"
                    }
                )
                response.raise_for_status()
                
                user_info = response.json()
                logger.info(f"Retrieved Google user info for: {user_info.get('email', 'unknown')}")
                return user_info
                
            except httpx.HTTPStatusError as e:
                logger.error(f"Google user info request failed: {e.response.text}")
                raise HTTPException(
                    status_code=400,
                    detail="Failed to retrieve user information"
                )
            except Exception as e:
                logger.error(f"Google user info error: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to retrieve user information"
                )
    
    def _generate_oauth_api_key(self) -> str:
        """Generate API key for OAuth users with gai_ prefix."""
        # Generate 32 character token
        token = secrets.token_urlsafe(24)  # 24 bytes = 32 base64 chars
        return f"gai_{token}"
    
    async def create_or_update_user(self, provider: str, user_info: Dict[str, Any]) -> OAuthUser:
        """
        Create or update OAuth user in database.
        
        Args:
            provider: OAuth provider name (google, azure)
            user_info: User information from OAuth provider
            
        Returns:
            OAuthUser instance
        """
        try:
            # Extract user information
            email = user_info.get("email")
            provider_id = user_info.get("id") or user_info.get("sub")
            name = user_info.get("name")
            avatar_url = user_info.get("picture")
            
            if not email or not provider_id:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid user information from OAuth provider"
                )
            
            # Check if user already exists
            stmt = select(OAuthUser).where(
                OAuthUser.email == email,
                OAuthUser.provider == provider
            )
            result = await self.db.execute(stmt)
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                # Update existing user
                existing_user.name = name
                existing_user.avatar_url = avatar_url
                existing_user.last_login = datetime.utcnow()
                existing_user.is_active = True
                
                await self.db.commit()
                await self.db.refresh(existing_user)
                
                logger.info(f"Updated existing OAuth user: {email}")
                return existing_user
            
            else:
                # Create new user
                api_key = self._generate_oauth_api_key()
                api_key_hash = hash_api_key(api_key)
                
                new_user = OAuthUser(
                    email=email,
                    provider=provider,
                    provider_id=provider_id,
                    name=name,
                    avatar_url=avatar_url,
                    api_key=api_key,  # Store encrypted in production
                    api_key_hash=api_key_hash,
                    permissions=["read", "write"],  # Default permissions
                    is_active=True,
                    last_login=datetime.utcnow()
                )
                
                self.db.add(new_user)
                await self.db.commit()
                await self.db.refresh(new_user)
                
                logger.info(f"Created new OAuth user: {email}")
                return new_user
                
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create/update OAuth user: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to create or update user"
            )
    
    async def get_user_by_api_key_hash(self, api_key_hash: str) -> Optional[OAuthUser]:
        """Get OAuth user by API key hash."""
        try:
            stmt = select(OAuthUser).where(
                OAuthUser.api_key_hash == api_key_hash,
                OAuthUser.is_active == True
            )
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get user by API key hash: {str(e)}")
            return None
    
    async def revoke_user_access(self, user_id: str) -> bool:
        """Revoke access for OAuth user."""
        try:
            stmt = select(OAuthUser).where(OAuthUser.id == user_id)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                user.is_active = False
                await self.db.commit()
                logger.info(f"Revoked access for OAuth user: {user.email}")
                return True
            
            return False
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to revoke user access: {str(e)}")
            return False
