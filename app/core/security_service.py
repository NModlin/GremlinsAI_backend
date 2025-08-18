"""
Security Service for Phase 4, Task 4.1: Security Audit & Hardening

This module provides comprehensive security services for GremlinsAI including:
- OAuth2 with JWT token authentication
- Role-based access control (RBAC)
- Input validation and sanitization
- Security event logging and monitoring
- Rate limiting and abuse prevention
- Secure session management

Implements enterprise-grade security for production deployment.
"""

import asyncio
import hashlib
import secrets
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from enum import Enum

import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, validator
import redis.asyncio as redis

from app.core.config import get_settings
from app.core.logging_config import get_logger, log_security_event

logger = get_logger(__name__)
settings = get_settings()

# Security configuration
SECRET_KEY = settings.secret_key if hasattr(settings, 'secret_key') else secrets.token_urlsafe(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token scheme
security = HTTPBearer()


class UserRole(str, Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"
    SERVICE = "service"


class Permission(str, Enum):
    """System permissions."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    UPLOAD = "upload"
    MULTIMODAL = "multimodal"
    COLLABORATION = "collaboration"


@dataclass
class SecurityContext:
    """Security context for authenticated requests."""
    user_id: str
    username: str
    email: Optional[str]
    roles: List[UserRole]
    permissions: List[Permission]
    session_id: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    authenticated_at: datetime
    expires_at: datetime


class TokenData(BaseModel):
    """JWT token data structure."""
    sub: str = Field(..., description="Subject (user ID)")
    username: str = Field(..., description="Username")
    email: Optional[str] = Field(None, description="User email")
    roles: List[str] = Field(default_factory=list, description="User roles")
    permissions: List[str] = Field(default_factory=list, description="User permissions")
    session_id: str = Field(..., description="Session ID")
    exp: int = Field(..., description="Expiration timestamp")
    iat: int = Field(..., description="Issued at timestamp")
    jti: str = Field(..., description="JWT ID")


class LoginRequest(BaseModel):
    """Login request schema."""
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=8, max_length=128, description="Password")
    
    @validator('username')
    def validate_username(cls, v):
        """Validate username format."""
        if not v.replace('_', '').replace('-', '').replace('.', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, hyphens, underscores, and dots')
        return v.lower()


class TokenResponse(BaseModel):
    """Token response schema."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")


class SecurityService:
    """
    Comprehensive security service for authentication, authorization, and monitoring.
    
    Provides OAuth2 with JWT tokens, RBAC, input validation, and security monitoring
    for enterprise-grade security in production environments.
    """
    
    def __init__(self):
        """Initialize security service."""
        self.redis_client: Optional[redis.Redis] = None
        self.active_sessions: Dict[str, SecurityContext] = {}
        self.failed_login_attempts: Dict[str, List[datetime]] = {}
        self.blocked_ips: Set[str] = set()
        
        # Role-permission mapping
        self.role_permissions = {
            UserRole.ADMIN: [Permission.READ, Permission.WRITE, Permission.DELETE, Permission.ADMIN, 
                           Permission.UPLOAD, Permission.MULTIMODAL, Permission.COLLABORATION],
            UserRole.USER: [Permission.READ, Permission.WRITE, Permission.UPLOAD, 
                          Permission.MULTIMODAL, Permission.COLLABORATION],
            UserRole.READONLY: [Permission.READ],
            UserRole.SERVICE: [Permission.READ, Permission.WRITE, Permission.UPLOAD]
        }
        
        # Initialize Redis for session storage
        self._initialize_redis()
        
        logger.info("SecurityService initialized with JWT authentication")
    
    def _initialize_redis(self):
        """Initialize Redis client for session storage."""
        try:
            self.redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            logger.info("Redis session storage initialized")
        except Exception as e:
            logger.warning(f"Redis initialization failed: {e}")
            self.redis_client = None
    
    def hash_password(self, password: str) -> str:
        """Hash a password securely."""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": str(uuid.uuid4())
        })
        
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def create_refresh_token(self, user_id: str, session_id: str) -> str:
        """Create a JWT refresh token."""
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        to_encode = {
            "sub": user_id,
            "session_id": session_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": str(uuid.uuid4()),
            "type": "refresh"
        }
        
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    async def verify_token(self, token: str) -> Optional[TokenData]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # Validate required fields
            user_id = payload.get("sub")
            if user_id is None:
                return None
            
            # Check if token is blacklisted
            jti = payload.get("jti")
            if jti and await self._is_token_blacklisted(jti):
                return None
            
            token_data = TokenData(
                sub=user_id,
                username=payload.get("username", ""),
                email=payload.get("email"),
                roles=payload.get("roles", []),
                permissions=payload.get("permissions", []),
                session_id=payload.get("session_id", ""),
                exp=payload.get("exp", 0),
                iat=payload.get("iat", 0),
                jti=jti or ""
            )
            
            return token_data
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.JWTError as e:
            logger.warning(f"JWT validation error: {e}")
            return None
    
    async def authenticate_user(self, username: str, password: str, ip_address: str) -> Optional[SecurityContext]:
        """Authenticate a user with username and password."""
        # Check for IP blocking
        if ip_address in self.blocked_ips:
            log_security_event(
                event_type="authentication_blocked",
                user_id=username,
                ip_address=ip_address,
                details={"reason": "IP blocked due to suspicious activity"}
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="IP address temporarily blocked due to suspicious activity"
            )
        
        # Check for rate limiting
        if not await self._check_login_rate_limit(username, ip_address):
            log_security_event(
                event_type="authentication_rate_limited",
                user_id=username,
                ip_address=ip_address,
                details={"reason": "Too many failed login attempts"}
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Please try again later."
            )
        
        # TODO: Replace with actual user database lookup
        # For now, using demo users
        demo_users = {
            "admin": {
                "password_hash": self.hash_password("admin123"),
                "email": "admin@gremlinsai.com",
                "roles": [UserRole.ADMIN]
            },
            "user": {
                "password_hash": self.hash_password("user123"),
                "email": "user@gremlinsai.com",
                "roles": [UserRole.USER]
            },
            "readonly": {
                "password_hash": self.hash_password("readonly123"),
                "email": "readonly@gremlinsai.com",
                "roles": [UserRole.READONLY]
            }
        }
        
        user_data = demo_users.get(username)
        if not user_data or not self.verify_password(password, user_data["password_hash"]):
            await self._record_failed_login(username, ip_address)
            log_security_event(
                event_type="authentication_failed",
                user_id=username,
                ip_address=ip_address,
                details={"reason": "Invalid credentials"}
            )
            return None
        
        # Create security context
        session_id = str(uuid.uuid4())
        permissions = []
        for role in user_data["roles"]:
            permissions.extend(self.role_permissions.get(role, []))
        
        security_context = SecurityContext(
            user_id=username,
            username=username,
            email=user_data["email"],
            roles=user_data["roles"],
            permissions=list(set(permissions)),  # Remove duplicates
            session_id=session_id,
            ip_address=ip_address,
            user_agent=None,
            authenticated_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        # Store session
        await self._store_session(security_context)
        
        log_security_event(
            event_type="authentication_success",
            user_id=username,
            ip_address=ip_address,
            details={
                "session_id": session_id,
                "roles": [role.value for role in user_data["roles"]]
            }
        )
        
        return security_context
    
    async def login(self, login_request: LoginRequest, ip_address: str) -> TokenResponse:
        """Login user and return JWT tokens."""
        security_context = await self.authenticate_user(
            login_request.username, 
            login_request.password, 
            ip_address
        )
        
        if not security_context:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create tokens
        token_data = {
            "sub": security_context.user_id,
            "username": security_context.username,
            "email": security_context.email,
            "roles": [role.value for role in security_context.roles],
            "permissions": [perm.value for perm in security_context.permissions],
            "session_id": security_context.session_id
        }
        
        access_token = self.create_access_token(token_data)
        refresh_token = self.create_refresh_token(security_context.user_id, security_context.session_id)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    
    async def logout(self, token: str) -> bool:
        """Logout user and blacklist token."""
        token_data = await self.verify_token(token)
        if not token_data:
            return False
        
        # Blacklist the token
        await self._blacklist_token(token_data.jti, token_data.exp)
        
        # Remove session
        await self._remove_session(token_data.session_id)
        
        log_security_event(
            event_type="logout",
            user_id=token_data.sub,
            details={"session_id": token_data.session_id}
        )
        
        return True
    
    def check_permission(self, security_context: SecurityContext, required_permission: Permission) -> bool:
        """Check if user has required permission."""
        return required_permission in security_context.permissions
    
    def require_permission(self, security_context: SecurityContext, required_permission: Permission):
        """Require user to have specific permission."""
        if not self.check_permission(security_context, required_permission):
            log_security_event(
                event_type="authorization_denied",
                user_id=security_context.user_id,
                details={
                    "required_permission": required_permission.value,
                    "user_permissions": [p.value for p in security_context.permissions]
                }
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {required_permission.value}"
            )
    
    async def _check_login_rate_limit(self, username: str, ip_address: str) -> bool:
        """Check if login attempts are within rate limits."""
        now = datetime.utcnow()
        window = timedelta(minutes=15)  # 15-minute window
        max_attempts = 5
        
        # Clean old attempts
        key = f"{username}:{ip_address}"
        if key in self.failed_login_attempts:
            self.failed_login_attempts[key] = [
                attempt for attempt in self.failed_login_attempts[key]
                if now - attempt < window
            ]
        
        # Check current attempts
        attempts = len(self.failed_login_attempts.get(key, []))
        return attempts < max_attempts
    
    async def _record_failed_login(self, username: str, ip_address: str):
        """Record a failed login attempt."""
        key = f"{username}:{ip_address}"
        if key not in self.failed_login_attempts:
            self.failed_login_attempts[key] = []
        
        self.failed_login_attempts[key].append(datetime.utcnow())
        
        # Block IP if too many failures
        if len(self.failed_login_attempts[key]) >= 10:  # Block after 10 failures
            self.blocked_ips.add(ip_address)
            logger.warning(f"IP {ip_address} blocked due to excessive failed login attempts")
    
    async def _store_session(self, security_context: SecurityContext):
        """Store session in Redis or memory."""
        session_data = {
            "user_id": security_context.user_id,
            "username": security_context.username,
            "email": security_context.email,
            "roles": [role.value for role in security_context.roles],
            "permissions": [perm.value for perm in security_context.permissions],
            "ip_address": security_context.ip_address,
            "authenticated_at": security_context.authenticated_at.isoformat(),
            "expires_at": security_context.expires_at.isoformat()
        }
        
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    f"session:{security_context.session_id}",
                    ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                    str(session_data)
                )
            except Exception as e:
                logger.error(f"Failed to store session in Redis: {e}")
                self.active_sessions[security_context.session_id] = security_context
        else:
            self.active_sessions[security_context.session_id] = security_context
    
    async def _remove_session(self, session_id: str):
        """Remove session from storage."""
        if self.redis_client:
            try:
                await self.redis_client.delete(f"session:{session_id}")
            except Exception as e:
                logger.error(f"Failed to remove session from Redis: {e}")
        
        self.active_sessions.pop(session_id, None)
    
    async def _blacklist_token(self, jti: str, exp: int):
        """Blacklist a JWT token."""
        if self.redis_client:
            try:
                # Store until token expires
                ttl = max(0, exp - int(time.time()))
                await self.redis_client.setex(f"blacklist:{jti}", ttl, "1")
            except Exception as e:
                logger.error(f"Failed to blacklist token: {e}")
    
    async def _is_token_blacklisted(self, jti: str) -> bool:
        """Check if token is blacklisted."""
        if self.redis_client:
            try:
                result = await self.redis_client.get(f"blacklist:{jti}")
                return result is not None
            except Exception as e:
                logger.error(f"Failed to check token blacklist: {e}")
        
        return False


# Global security service instance
security_service = SecurityService()


# FastAPI Dependencies
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    request: Request = None
) -> SecurityContext:
    """FastAPI dependency to get current authenticated user."""
    token = credentials.credentials
    token_data = await security_service.verify_token(token)
    
    if token_data is None:
        log_security_event(
            event_type="invalid_token",
            ip_address=request.client.host if request else None,
            details={"token_prefix": token[:10] if token else ""}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create security context from token data
    security_context = SecurityContext(
        user_id=token_data.sub,
        username=token_data.username,
        email=token_data.email,
        roles=[UserRole(role) for role in token_data.roles],
        permissions=[Permission(perm) for perm in token_data.permissions],
        session_id=token_data.session_id,
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("User-Agent") if request else None,
        authenticated_at=datetime.fromtimestamp(token_data.iat),
        expires_at=datetime.fromtimestamp(token_data.exp)
    )
    
    return security_context


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[SecurityContext]:
    """FastAPI dependency to get current user (optional authentication)."""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, request)
    except HTTPException:
        return None


def require_permission(permission: Permission):
    """Decorator to require specific permission."""
    def permission_dependency(current_user: SecurityContext = Depends(get_current_user)):
        security_service.require_permission(current_user, permission)
        return current_user
    
    return permission_dependency


def require_role(role: UserRole):
    """Decorator to require specific role."""
    def role_dependency(current_user: SecurityContext = Depends(get_current_user)):
        if role not in current_user.roles:
            log_security_event(
                event_type="authorization_denied",
                user_id=current_user.user_id,
                details={
                    "required_role": role.value,
                    "user_roles": [r.value for r in current_user.roles]
                }
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient role. Required: {role.value}"
            )
        return current_user
    
    return role_dependency
