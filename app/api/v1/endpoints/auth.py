# app/api/v1/endpoints/auth.py
"""
OAuth2 Authentication endpoints for GremlinsAI Backend.
Handles Google OAuth2 login, token exchange, and user management.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    verify_google_token, 
    create_access_token, 
    create_user_from_google,
    get_current_user,
    get_current_user_optional,
    User,
    GOOGLE_CLIENT_ID,
    OAuth2Error
)
from app.database.database import get_db
from app.database.models import User as UserModel
from sqlalchemy import select
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()


class TokenRequest(BaseModel):
    """Request model for token exchange."""
    google_token: str


class TokenResponse(BaseModel):
    """Response model for token exchange."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400  # 24 hours
    user: Dict[str, Any]


class UserResponse(BaseModel):
    """Response model for user information."""
    id: str
    email: str
    name: str
    picture: str = None
    email_verified: bool
    roles: list
    permissions: list
    created_at: str
    last_login: str = None
    is_active: bool


@router.get("/config")
async def get_auth_config():
    """Get OAuth2 configuration for frontend."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=500,
            detail="OAuth2 not configured. Please set GOOGLE_CLIENT_ID environment variable."
        )
    
    return {
        "google_client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": "http://localhost:3000/auth/callback",  # Frontend callback
        "scopes": ["openid", "email", "profile"]
    }


@router.post("/token", response_model=TokenResponse)
async def exchange_token(
    token_request: TokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """Exchange Google OAuth2 token for GremlinsAI access token."""
    try:
        # Verify Google token
        google_payload = await verify_google_token(token_request.google_token)
        
        # Check if user exists in database
        stmt = select(UserModel).where(UserModel.id == google_payload["sub"])
        result = await db.execute(stmt)
        db_user = result.scalar_one_or_none()
        
        if db_user:
            # Update existing user
            db_user.last_login = datetime.utcnow()
            db_user.name = google_payload.get("name", db_user.name)
            db_user.picture = google_payload.get("picture", db_user.picture)
            db_user.email_verified = google_payload.get("email_verified", db_user.email_verified)
            await db.commit()
            
            user = User(
                id=db_user.id,
                email=db_user.email,
                name=db_user.name,
                picture=db_user.picture,
                email_verified=db_user.email_verified,
                roles=db_user.roles,
                permissions=db_user.permissions,
                created_at=db_user.created_at,
                last_login=db_user.last_login,
                is_active=db_user.is_active
            )
        else:
            # Create new user
            user = create_user_from_google(google_payload)
            
            db_user = UserModel(
                id=user.id,
                email=user.email,
                name=user.name,
                picture=user.picture,
                email_verified=user.email_verified,
                roles=user.roles,
                permissions=user.permissions,
                provider="google",
                provider_id=user.id,
                created_at=user.created_at,
                last_login=user.last_login,
                is_active=user.is_active,
                is_verified=user.email_verified
            )
            
            db.add(db_user)
            await db.commit()
            await db.refresh(db_user)
        
        # Create access token
        access_token = create_access_token(user)
        
        return TokenResponse(
            access_token=access_token,
            user={
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "picture": user.picture,
                "email_verified": user.email_verified,
                "roles": user.roles,
                "permissions": user.permissions,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "is_active": user.is_active
            }
        )
        
    except OAuth2Error as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"Token exchange failed: {e}")
        raise HTTPException(status_code=500, detail="Token exchange failed")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        picture=current_user.picture,
        email_verified=current_user.email_verified,
        roles=current_user.roles,
        permissions=current_user.permissions,
        created_at=current_user.created_at.isoformat(),
        last_login=current_user.last_login.isoformat() if current_user.last_login else None,
        is_active=current_user.is_active
    )


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Logout current user (invalidate token on client side)."""
    # In a stateless JWT system, logout is handled client-side by removing the token
    # For enhanced security, you could maintain a token blacklist in Redis
    logger.info(f"User {current_user.email} logged out")
    return {"message": "Successfully logged out"}


@router.get("/verify")
async def verify_token(current_user: User = Depends(get_current_user_optional)):
    """Verify if the current token is valid."""
    if current_user:
        return {
            "valid": True,
            "user": {
                "id": current_user.id,
                "email": current_user.email,
                "name": current_user.name
            }
        }
    else:
        return {"valid": False}
