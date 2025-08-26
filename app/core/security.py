# app/core/security.py
"""
OAuth2 Security system for GremlinsAI Backend.
Provides Google OAuth2 authentication, JWT token validation, and user authorization.
"""

import logging
import re
import hashlib
import secrets
import jwt
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import html
import os

logger = logging.getLogger(__name__)

# OAuth2 Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Security configuration
API_KEY_LENGTH = 32  # For backward compatibility
MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB
RATE_LIMIT_REQUESTS = 1000  # Increased for production
RATE_LIMIT_WINDOW = 3600  # 1 hour

# In-memory storage for demo purposes (use Redis/database in production)
_rate_limit_storage: Dict[str, List[datetime]] = {}
_google_keys_cache: Dict[str, Any] = {}
_cache_expiry: Optional[datetime] = None

security = HTTPBearer()


class SecurityError(Exception):
    """Custom security exception."""
    pass


class OAuth2Error(Exception):
    """OAuth2 specific exception."""
    pass


class User(BaseModel):
    """User model for OAuth2 authentication."""
    id: str
    email: str
    name: str
    picture: Optional[str] = None
    email_verified: bool = False
    roles: List[str] = ["user"]
    permissions: List[str] = ["read", "write"]
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True


class TokenData(BaseModel):
    """Token data model."""
    user_id: str
    email: str
    name: str
    roles: List[str]
    permissions: List[str]
    exp: datetime
    iat: datetime


async def get_google_public_keys() -> Dict[str, Any]:
    """Get Google's public keys for JWT verification."""
    global _google_keys_cache, _cache_expiry

    # Check cache validity (refresh every hour)
    if _cache_expiry and datetime.utcnow() < _cache_expiry and _google_keys_cache:
        return _google_keys_cache

    try:
        async with httpx.AsyncClient() as client:
            # Get Google's OpenID configuration
            config_response = await client.get(GOOGLE_DISCOVERY_URL)
            config_response.raise_for_status()
            config = config_response.json()

            # Get the public keys
            keys_response = await client.get(config["jwks_uri"])
            keys_response.raise_for_status()
            keys_data = keys_response.json()

            _google_keys_cache = keys_data
            _cache_expiry = datetime.utcnow() + timedelta(hours=1)

            return keys_data
    except Exception as e:
        logger.error(f"Failed to fetch Google public keys: {e}")
        raise OAuth2Error("Failed to fetch Google public keys")


def create_access_token(user: User) -> str:
    """Create a JWT access token for a user."""
    now = datetime.utcnow()
    expire = now + timedelta(hours=JWT_EXPIRATION_HOURS)

    payload = {
        "user_id": user.id,
        "email": user.email,
        "name": user.name,
        "roles": user.roles,
        "permissions": user.permissions,
        "exp": expire,
        "iat": now,
        "iss": "gremlinsai",
        "aud": "gremlinsai-api"
    }

    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    logger.info(f"Created access token for user {user.email}")
    return token


async def verify_google_token(token: str) -> Dict[str, Any]:
    """Verify a Google OAuth2 token."""
    try:
        # Decode without verification first to get the header
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        if not kid:
            raise OAuth2Error("Token missing key ID")

        # Get Google's public keys
        keys_data = await get_google_public_keys()

        # Find the correct key
        public_key = None
        for key in keys_data.get("keys", []):
            if key.get("kid") == kid:
                public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                break

        if not public_key:
            raise OAuth2Error("Public key not found")

        # Verify the token
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=GOOGLE_CLIENT_ID,
            issuer="https://accounts.google.com"
        )

        return payload
    except jwt.ExpiredSignatureError:
        raise OAuth2Error("Token has expired")
    except jwt.InvalidTokenError as e:
        raise OAuth2Error(f"Invalid token: {str(e)}")


def verify_access_token(token: str) -> TokenData:
    """Verify a GremlinsAI access token."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

        token_data = TokenData(
            user_id=payload["user_id"],
            email=payload["email"],
            name=payload["name"],
            roles=payload["roles"],
            permissions=payload["permissions"],
            exp=datetime.fromtimestamp(payload["exp"]),
            iat=datetime.fromtimestamp(payload["iat"])
        )

        # Check if token is expired
        if token_data.exp < datetime.utcnow():
            raise OAuth2Error("Token has expired")

        return token_data
    except jwt.ExpiredSignatureError:
        raise OAuth2Error("Token has expired")
    except jwt.InvalidTokenError as e:
        raise OAuth2Error(f"Invalid token: {str(e)}")
    except KeyError as e:
        raise OAuth2Error(f"Token missing required field: {str(e)}")


def sanitize_input(text: str, max_length: int = 10000) -> str:
    """Sanitize user input to prevent XSS and injection attacks."""
    if not text:
        return ""
    
    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length]
    
    # HTML escape
    text = html.escape(text)
    
    # Remove potentially dangerous patterns
    dangerous_patterns = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'vbscript:',
        r'onload\s*=',
        r'onerror\s*=',
        r'onclick\s*=',
        r'onmouseover\s*=',
    ]
    
    for pattern in dangerous_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
    
    return text.strip()


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal and command injection."""
    if not filename:
        return "unnamed_file"
    
    # Remove path separators and dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)  # Remove control characters
    
    # Remove shell command injection patterns
    dangerous_patterns = [
        r'\$\(',  # Command substitution
        r'`',     # Backticks
        r'\|',    # Pipes
        r'&',     # Background execution
        r';',     # Command separator
        r'\.\./', # Directory traversal
        r'\.\.\\', # Directory traversal (Windows)
    ]
    
    for pattern in dangerous_patterns:
        filename = re.sub(pattern, '_', filename)
    
    # Ensure filename is not empty and has reasonable length
    filename = filename.strip()
    if not filename or filename in ['.', '..']:
        filename = "sanitized_file"
    
    if len(filename) > 255:
        filename = filename[:255]
    
    return filename


def check_rate_limit(client_id: str, limit: int = RATE_LIMIT_REQUESTS, 
                    window: int = RATE_LIMIT_WINDOW) -> bool:
    """Check if client has exceeded rate limit."""
    now = datetime.utcnow()
    cutoff = now - timedelta(seconds=window)
    
    # Clean old entries
    if client_id in _rate_limit_storage:
        _rate_limit_storage[client_id] = [
            req_time for req_time in _rate_limit_storage[client_id] 
            if req_time > cutoff
        ]
    else:
        _rate_limit_storage[client_id] = []
    
    # Check limit
    if len(_rate_limit_storage[client_id]) >= limit:
        return False
    
    # Record this request
    _rate_limit_storage[client_id].append(now)
    return True


def get_security_headers() -> Dict[str, str]:
    """Get security headers for HTTP responses."""
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
    }


def get_cors_headers() -> Dict[str, str]:
    """Get CORS headers for cross-origin requests."""
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-API-Key",
        "Access-Control-Max-Age": "86400"
    }


async def authenticate_request(request: Request) -> Optional[User]:
    """Authenticate a request using OAuth2 Bearer token."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header[7:]  # Remove "Bearer " prefix

    try:
        # First try to verify as GremlinsAI access token
        token_data = verify_access_token(token)

        # Create user object from token data
        user = User(
            id=token_data.user_id,
            email=token_data.email,
            name=token_data.name,
            roles=token_data.roles,
            permissions=token_data.permissions,
            created_at=token_data.iat,
            last_login=datetime.utcnow(),
            is_active=True
        )

        return user

    except OAuth2Error:
        # If GremlinsAI token fails, try Google token
        try:
            google_payload = await verify_google_token(token)

            # Create user from Google token
            user = User(
                id=google_payload["sub"],
                email=google_payload["email"],
                name=google_payload.get("name", ""),
                picture=google_payload.get("picture"),
                email_verified=google_payload.get("email_verified", False),
                roles=["user"],  # Default role for Google users
                permissions=["read", "write"],  # Default permissions
                created_at=datetime.utcnow(),
                last_login=datetime.utcnow(),
                is_active=True
            )

            return user

        except OAuth2Error:
            return None


def require_authentication(user: Optional[User]) -> User:
    """Require authentication and raise exception if not authenticated."""
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please provide a valid OAuth2 token.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user


def require_permission(user: User, required_permission: str) -> None:
    """Require specific permission and raise exception if not authorized."""
    if required_permission not in user.permissions and "admin" not in user.roles:
        raise HTTPException(
            status_code=403,
            detail=f"Permission '{required_permission}' required"
        )


def require_role(user: User, required_role: str) -> None:
    """Require specific role and raise exception if not authorized."""
    if required_role not in user.roles and "admin" not in user.roles:
        raise HTTPException(
            status_code=403,
            detail=f"Role '{required_role}' required"
        )


# FastAPI Dependencies for authentication
async def get_current_user(request: Request) -> User:
    """FastAPI dependency to get current authenticated user (required)."""
    user = await authenticate_request(request)
    return require_authentication(user)


async def get_current_user_optional(request: Request) -> Optional[User]:
    """FastAPI dependency to get current user (optional authentication)."""
    return await authenticate_request(request)


# User management functions
def create_user_from_google(google_payload: Dict[str, Any]) -> User:
    """Create a User object from Google OAuth2 payload."""
    return User(
        id=google_payload["sub"],
        email=google_payload["email"],
        name=google_payload.get("name", ""),
        picture=google_payload.get("picture"),
        email_verified=google_payload.get("email_verified", False),
        roles=["user"],  # Default role for new users
        permissions=["read", "write"],  # Default permissions
        created_at=datetime.utcnow(),
        last_login=datetime.utcnow(),
        is_active=True
    )


def get_user_permissions(user: User) -> List[str]:
    """Get all permissions for a user based on their roles."""
    permissions = set(user.permissions)

    # Add role-based permissions
    for role in user.roles:
        if role == "admin":
            permissions.update(["read", "write", "delete", "admin", "manage_users"])
        elif role == "moderator":
            permissions.update(["read", "write", "moderate"])
        elif role == "user":
            permissions.update(["read", "write"])

    return list(permissions)


def check_user_access(user: User, resource_owner_id: str) -> bool:
    """Check if user can access a resource owned by another user."""
    # Users can always access their own resources
    if user.id == resource_owner_id:
        return True

    # Admins can access all resources
    if "admin" in user.roles:
        return True

    # Moderators can access user resources but not admin resources
    if "moderator" in user.roles:
        return True

    return False


# OAuth2 Configuration validation
def validate_oauth2_config():
    """Validate OAuth2 configuration on startup."""
    if not GOOGLE_CLIENT_ID:
        logger.warning("GOOGLE_CLIENT_ID not set. OAuth2 authentication will not work.")

    if not GOOGLE_CLIENT_SECRET:
        logger.warning("GOOGLE_CLIENT_SECRET not set. OAuth2 authentication will not work.")

    if not JWT_SECRET_KEY:
        logger.warning("JWT_SECRET_KEY not set. Using generated key (not suitable for production).")

    logger.info("OAuth2 security system initialized")


# Initialize OAuth2 system when module is imported
validate_oauth2_config()
