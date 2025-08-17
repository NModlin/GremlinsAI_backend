# app/api/v1/endpoints/oauth.py
"""
OAuth authentication endpoints for GremlinsAI backend.

This module provides OAuth authentication endpoints for Google and future Azure integration,
including login initiation, callback handling, and user management.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db
from app.services.oauth_service import OAuthService
from app.core.config import settings, oauth_config
from app.core.oauth_providers import OAuthProvider, is_provider_supported

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/providers")
async def get_oauth_providers():
    """
    Get list of available OAuth providers.
    
    Returns:
        List of enabled OAuth providers with their configuration status
    """
    providers = []
    
    if oauth_config.google_enabled:
        providers.append({
            "name": "google",
            "display_name": "Google",
            "enabled": True,
            "login_url": "/api/v1/oauth/google/login"
        })
    
    if oauth_config.azure_enabled:
        providers.append({
            "name": "azure",
            "display_name": "Microsoft",
            "enabled": True,
            "login_url": "/api/v1/oauth/azure/login"
        })
    
    return {
        "providers": providers,
        "total_enabled": len(providers)
    }


@router.get("/google/login")
async def google_oauth_login(
    request: Request,
    redirect_url: Optional[str] = Query(None, description="URL to redirect after successful authentication"),
    db: AsyncSession = Depends(get_db)
):
    """
    Initiate Google OAuth login flow.
    
    Args:
        redirect_url: Optional URL to redirect to after successful authentication
        db: Database session
        
    Returns:
        Redirect to Google OAuth authorization URL
    """
    try:
        oauth_service = OAuthService(db)
        
        # Generate state parameter for CSRF protection
        # In production, store this in session or cache
        state = f"google_{redirect_url or 'default'}"
        
        # Get Google authorization URL
        auth_url = await oauth_service.get_google_authorization_url(state=state)
        
        logger.info("Redirecting to Google OAuth authorization")
        return RedirectResponse(url=auth_url)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google OAuth login error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to initiate Google OAuth login"
        )


@router.get("/google/callback")
async def google_oauth_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: Optional[str] = Query(None, description="State parameter for CSRF protection"),
    error: Optional[str] = Query(None, description="Error from OAuth provider"),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Google OAuth callback.
    
    Args:
        code: Authorization code from Google
        state: State parameter for CSRF protection
        error: Error parameter if OAuth failed
        db: Database session
        
    Returns:
        User information and API key for successful authentication
    """
    try:
        # Check for OAuth errors
        if error:
            logger.warning(f"Google OAuth error: {error}")
            raise HTTPException(
                status_code=400,
                detail=f"OAuth authentication failed: {error}"
            )
        
        if not code:
            raise HTTPException(
                status_code=400,
                detail="Authorization code is required"
            )
        
        oauth_service = OAuthService(db)
        
        # Exchange code for token
        token_data = await oauth_service.exchange_google_code_for_token(code, state)
        access_token = token_data.get("access_token")
        
        if not access_token:
            raise HTTPException(
                status_code=400,
                detail="Failed to obtain access token"
            )
        
        # Get user information
        user_info = await oauth_service.get_google_user_info(access_token)
        
        # Create or update user
        oauth_user = await oauth_service.create_or_update_user("google", user_info)
        
        # Parse redirect URL from state
        redirect_url = None
        if state and state.startswith("google_") and state != "google_default":
            redirect_url = state[7:]  # Remove "google_" prefix
        
        response_data = {
            "success": True,
            "message": "Authentication successful",
            "user": oauth_user.to_dict(),
            "api_key": oauth_user.api_key,
            "provider": "google",
            "redirect_url": redirect_url
        }
        
        logger.info(f"Google OAuth callback successful for user: {oauth_user.email}")
        
        # In a real application, you might want to redirect to frontend with token
        # For API-first approach, return JSON response
        return JSONResponse(content=response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google OAuth callback error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="OAuth callback processing failed"
        )


@router.get("/azure/login")
async def azure_oauth_login(
    request: Request,
    redirect_url: Optional[str] = Query(None, description="URL to redirect after successful authentication"),
    db: AsyncSession = Depends(get_db)
):
    """
    Initiate Microsoft Azure OAuth login flow.
    
    Args:
        redirect_url: Optional URL to redirect to after successful authentication
        db: Database session
        
    Returns:
        Redirect to Azure OAuth authorization URL
    """
    if not oauth_config.azure_enabled:
        raise HTTPException(
            status_code=400,
            detail="Azure OAuth is not configured"
        )
    
    # Placeholder for future Azure OAuth implementation
    return JSONResponse(content={
        "message": "Azure OAuth not yet implemented",
        "status": "coming_soon",
        "provider": "azure"
    })


@router.get("/azure/callback")
async def azure_oauth_callback(
    code: str = Query(..., description="Authorization code from Azure"),
    state: Optional[str] = Query(None, description="State parameter for CSRF protection"),
    error: Optional[str] = Query(None, description="Error from OAuth provider"),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Microsoft Azure OAuth callback.

    Args:
        code: Authorization code from Azure
        state: State parameter for CSRF protection
        error: Error parameter if OAuth failed
        db: Database session

    Returns:
        User information and API key for successful authentication
    """
    if not oauth_config.azure_enabled:
        raise HTTPException(
            status_code=400,
            detail="Azure OAuth is not configured"
        )

    # Placeholder for future Azure OAuth implementation
    return JSONResponse(content={
        "message": "Azure OAuth callback not yet implemented",
        "status": "coming_soon",
        "provider": "azure"
    })


@router.post("/google/exchange")
async def exchange_google_token(
    request: Request,
    token_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """
    Exchange Google OAuth token for GremlinsAI API key.

    This endpoint is used by NextAuth to exchange OAuth tokens
    for GremlinsAI backend API keys.

    Args:
        token_data: Token and user information from NextAuth
        db: Database session

    Returns:
        User information and GremlinsAI API key
    """
    try:
        oauth_service = OAuthService(db)

        # Extract user info from token data
        user_info = token_data.get("user_info", {})
        provider = token_data.get("provider", "google")

        if not user_info or not user_info.get("email"):
            raise HTTPException(
                status_code=400,
                detail="Invalid user information provided"
            )

        # Create or update OAuth user
        oauth_user = await oauth_service.create_or_update_user(provider, user_info)

        return {
            "success": True,
            "user": oauth_user.to_dict(),
            "api_key": oauth_user.api_key,
            "provider": provider
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token exchange error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Token exchange failed"
        )


@router.post("/revoke")
async def revoke_oauth_access(
    request: Request,
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Revoke OAuth access for a user.
    
    Args:
        user_id: ID of the user to revoke access for
        db: Database session
        
    Returns:
        Success status
    """
    try:
        oauth_service = OAuthService(db)
        success = await oauth_service.revoke_user_access(user_id)
        
        if success:
            return {
                "success": True,
                "message": "User access revoked successfully"
            }
        else:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth revoke error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to revoke user access"
        )


@router.get("/status")
async def oauth_status():
    """
    Get OAuth system status and configuration.
    
    Returns:
        OAuth system status and enabled providers
    """
    return {
        "oauth_enabled": True,
        "providers": {
            "google": {
                "enabled": oauth_config.google_enabled,
                "configured": bool(settings.google_client_id and settings.google_client_secret)
            },
            "azure": {
                "enabled": oauth_config.azure_enabled,
                "configured": bool(
                    settings.azure_client_id and 
                    settings.azure_client_secret and 
                    settings.azure_tenant_id
                )
            }
        },
        "redirect_url": settings.oauth_redirect_url,
        "api_version": settings.app_version
    }
