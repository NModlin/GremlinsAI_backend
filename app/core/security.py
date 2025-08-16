# app/core/security.py
"""
Security utilities for authentication, authorization, and input validation.
Provides API key verification, input sanitization, and security headers.
"""

import logging
import re
import hashlib
import secrets
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import html

logger = logging.getLogger(__name__)

# Security configuration
API_KEY_LENGTH = 32
MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB
RATE_LIMIT_REQUESTS = 100
RATE_LIMIT_WINDOW = 3600  # 1 hour

# In-memory storage for demo purposes (use Redis/database in production)
_api_keys: Dict[str, Dict[str, Any]] = {}
_rate_limit_storage: Dict[str, List[datetime]] = {}

security = HTTPBearer()


class SecurityError(Exception):
    """Custom security exception."""
    pass


def generate_api_key() -> str:
    """Generate a secure API key."""
    return secrets.token_urlsafe(API_KEY_LENGTH)


def hash_api_key(api_key: str) -> str:
    """Hash an API key for secure storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def create_api_key(user_id: str, permissions: List[str] = None) -> str:
    """Create a new API key for a user."""
    api_key = generate_api_key()
    key_hash = hash_api_key(api_key)
    
    _api_keys[key_hash] = {
        "user_id": user_id,
        "permissions": permissions or ["read", "write"],
        "created_at": datetime.utcnow(),
        "last_used": None,
        "is_active": True
    }
    
    logger.info(f"Created API key for user {user_id}")
    return api_key


def verify_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    """Verify an API key and return user information."""
    if not api_key:
        return None
    
    key_hash = hash_api_key(api_key)
    key_info = _api_keys.get(key_hash)
    
    if not key_info or not key_info.get("is_active"):
        return None
    
    # Update last used timestamp
    key_info["last_used"] = datetime.utcnow()
    
    return {
        "user_id": key_info["user_id"],
        "permissions": key_info["permissions"],
        "api_key_hash": key_hash
    }


def revoke_api_key(api_key: str) -> bool:
    """Revoke an API key."""
    key_hash = hash_api_key(api_key)
    if key_hash in _api_keys:
        _api_keys[key_hash]["is_active"] = False
        logger.info(f"Revoked API key {key_hash[:8]}...")
        return True
    return False


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


async def authenticate_request(request: Request) -> Optional[Dict[str, Any]]:
    """Authenticate a request using API key."""
    # Try Authorization header first
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        api_key = auth_header[7:]  # Remove "Bearer " prefix
        return verify_api_key(api_key)
    
    # Try X-API-Key header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return verify_api_key(api_key)
    
    return None


def require_authentication(user_info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Require authentication and raise exception if not authenticated."""
    if not user_info:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user_info


def require_permission(user_info: Dict[str, Any], required_permission: str) -> None:
    """Require specific permission and raise exception if not authorized."""
    permissions = user_info.get("permissions", [])
    if required_permission not in permissions and "admin" not in permissions:
        raise HTTPException(
            status_code=403,
            detail=f"Permission '{required_permission}' required"
        )


# Initialize some demo API keys for testing
def initialize_demo_keys():
    """Initialize demo API keys for testing."""
    demo_keys = [
        ("test-user-1", ["read", "write"]),
        ("test-user-2", ["read"]),
        ("admin-user", ["admin", "read", "write"])
    ]
    
    for user_id, permissions in demo_keys:
        api_key = create_api_key(user_id, permissions)
        logger.info(f"Demo API key for {user_id}: {api_key}")


# Initialize demo keys when module is imported
initialize_demo_keys()
