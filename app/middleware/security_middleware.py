"""
Security Middleware for Phase 4, Task 4.1: Security Audit & Hardening

This middleware provides comprehensive security protection including:
- Request/response security headers
- Rate limiting and DDoS protection
- Input sanitization and validation
- Security event monitoring
- CORS and CSRF protection
"""

import asyncio
import time
import json
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from app.core.logging_config import log_security_event, log_suspicious_activity
from app.core.config import get_settings

settings = get_settings()


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive security middleware for request/response protection.
    
    Provides multiple layers of security including rate limiting,
    input validation, security headers, and threat detection.
    """
    
    def __init__(self, app, max_requests_per_minute: int = 60):
        """Initialize security middleware."""
        super().__init__(app)
        self.max_requests_per_minute = max_requests_per_minute
        
        # Rate limiting storage
        self.request_counts: Dict[str, List[datetime]] = defaultdict(list)
        self.blocked_ips: Set[str] = set()
        
        # Suspicious activity tracking
        self.failed_requests: Dict[str, int] = defaultdict(int)
        self.suspicious_patterns: Dict[str, int] = defaultdict(int)
        
        # Security headers
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        }
        
        # Excluded paths from rate limiting
        self.excluded_paths = {"/health", "/metrics", "/docs", "/openapi.json"}
    
    async def dispatch(self, request: Request, call_next):
        """Process request through security middleware."""
        start_time = time.time()
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "")
        
        try:
            # Check if IP is blocked
            if client_ip in self.blocked_ips:
                log_security_event(
                    event_type="blocked_ip_access_attempt",
                    severity="high",
                    ip_address=client_ip,
                    user_agent=user_agent,
                    endpoint=str(request.url.path),
                    method=request.method
                )
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "IP address blocked due to suspicious activity"}
                )
            
            # Rate limiting check
            if not self._check_rate_limit(client_ip, request.url.path):
                log_security_event(
                    event_type="rate_limit_exceeded",
                    severity="medium",
                    ip_address=client_ip,
                    user_agent=user_agent,
                    endpoint=str(request.url.path),
                    method=request.method
                )
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Rate limit exceeded"}
                )
            
            # Validate request headers
            if not self._validate_request_headers(request):
                log_security_event(
                    event_type="invalid_request_headers",
                    severity="medium",
                    ip_address=client_ip,
                    user_agent=user_agent,
                    endpoint=str(request.url.path)
                )
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid request headers"}
                )
            
            # Check for suspicious patterns
            if self._detect_suspicious_patterns(request):
                log_suspicious_activity(
                    activity_type="suspicious_request_pattern",
                    ip_address=client_ip,
                    user_agent=user_agent,
                    endpoint=str(request.url.path),
                    method=request.method
                )
                
                # Increase suspicion counter
                self.suspicious_patterns[client_ip] += 1
                
                # Block IP if too many suspicious requests
                if self.suspicious_patterns[client_ip] >= 5:
                    self.blocked_ips.add(client_ip)
                    log_security_event(
                        event_type="ip_blocked_suspicious_activity",
                        severity="high",
                        ip_address=client_ip,
                        reason="Multiple suspicious request patterns detected"
                    )
            
            # Process request
            response = await call_next(request)
            
            # Add security headers
            for header, value in self.security_headers.items():
                response.headers[header] = value
            
            # Add custom security headers
            response.headers["X-Request-ID"] = request.headers.get("X-Request-ID", "unknown")
            response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
            
            # Log successful request
            if response.status_code >= 400:
                self.failed_requests[client_ip] += 1
                
                # Log failed requests
                log_security_event(
                    event_type="request_failed",
                    severity="low" if response.status_code < 500 else "medium",
                    ip_address=client_ip,
                    user_agent=user_agent,
                    endpoint=str(request.url.path),
                    method=request.method,
                    status_code=response.status_code
                )
            
            return response
            
        except Exception as e:
            # Log security middleware errors
            log_security_event(
                event_type="security_middleware_error",
                severity="high",
                ip_address=client_ip,
                error=str(e),
                endpoint=str(request.url.path)
            )
            
            # Return generic error to avoid information disclosure
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error"}
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request."""
        # Check for forwarded headers (behind proxy/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def _check_rate_limit(self, client_ip: str, path: str) -> bool:
        """Check if request is within rate limits."""
        # Skip rate limiting for excluded paths
        if path in self.excluded_paths:
            return True
        
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=1)
        
        # Clean old requests
        self.request_counts[client_ip] = [
            req_time for req_time in self.request_counts[client_ip]
            if req_time > window_start
        ]
        
        # Check current request count
        current_requests = len(self.request_counts[client_ip])
        
        if current_requests >= self.max_requests_per_minute:
            return False
        
        # Add current request
        self.request_counts[client_ip].append(now)
        return True
    
    def _validate_request_headers(self, request: Request) -> bool:
        """Validate request headers for security."""
        # Check Content-Length for potential attacks
        content_length = request.headers.get("Content-Length")
        if content_length:
            try:
                length = int(content_length)
                if length > 10 * 1024 * 1024:  # 10MB limit
                    return False
            except ValueError:
                return False
        
        # Check for suspicious User-Agent patterns
        user_agent = request.headers.get("User-Agent", "")
        suspicious_ua_patterns = [
            "sqlmap", "nikto", "nmap", "masscan", "zap",
            "burp", "w3af", "acunetix", "nessus"
        ]
        
        if any(pattern in user_agent.lower() for pattern in suspicious_ua_patterns):
            return False
        
        return True
    
    def _detect_suspicious_patterns(self, request: Request) -> bool:
        """Detect suspicious patterns in requests."""
        # Check URL for suspicious patterns
        url_path = str(request.url.path).lower()
        query_string = str(request.url.query).lower()
        
        # SQL injection patterns
        sql_patterns = [
            "union select", "' or '1'='1", "'; drop table",
            "' or 1=1", "union all select", "' and '1'='1"
        ]
        
        # XSS patterns
        xss_patterns = [
            "<script", "javascript:", "onerror=", "onload=",
            "alert(", "document.cookie", "eval("
        ]
        
        # Path traversal patterns
        traversal_patterns = ["../", "..\\", "%2e%2e%2f", "%2e%2e%5c"]
        
        # Command injection patterns
        cmd_patterns = [";", "&&", "||", "`", "$(", "${"]
        
        all_patterns = sql_patterns + xss_patterns + traversal_patterns + cmd_patterns
        
        # Check URL path and query string
        for pattern in all_patterns:
            if pattern in url_path or pattern in query_string:
                return True
        
        # Check request headers for injection attempts
        for header_name, header_value in request.headers.items():
            if header_value:
                header_value_lower = header_value.lower()
                for pattern in all_patterns:
                    if pattern in header_value_lower:
                        return True
        
        return False
    
    async def cleanup_old_data(self):
        """Cleanup old rate limiting and tracking data."""
        now = datetime.utcnow()
        cutoff = now - timedelta(hours=1)
        
        # Clean request counts
        for ip in list(self.request_counts.keys()):
            self.request_counts[ip] = [
                req_time for req_time in self.request_counts[ip]
                if req_time > cutoff
            ]
            if not self.request_counts[ip]:
                del self.request_counts[ip]
        
        # Reset failed request counters
        self.failed_requests.clear()
        
        # Reset suspicious pattern counters (but keep blocked IPs)
        self.suspicious_patterns.clear()


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware for state-changing operations."""
    
    def __init__(self, app):
        """Initialize CSRF protection middleware."""
        super().__init__(app)
        # Exempt health/metrics and both legacy and versioned auth login paths
        self.csrf_exempt_paths = {
            "/auth/login",
            f"{settings.api_v1_prefix}/auth/login",
            "/health",
            "/metrics",
        }
        self.state_changing_methods = {"POST", "PUT", "PATCH", "DELETE"}
    
    async def dispatch(self, request: Request, call_next):
        """Process request through CSRF protection."""
        # Skip CSRF protection for exempt paths
        if request.url.path in self.csrf_exempt_paths:
            return await call_next(request)
        
        # Only check CSRF for state-changing methods
        if request.method in self.state_changing_methods:
            # Check for CSRF token in headers
            csrf_token = request.headers.get("X-CSRF-Token")
            origin = request.headers.get("Origin")
            referer = request.headers.get("Referer")
            
            # For API requests, we rely on proper CORS configuration
            # and require either Origin or Referer header
            if not origin and not referer:
                log_security_event(
                    event_type="csrf_protection_triggered",
                    severity="medium",
                    ip_address=request.client.host if request.client else "unknown",
                    endpoint=str(request.url.path),
                    method=request.method,
                    reason="Missing Origin and Referer headers"
                )
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "CSRF protection: Missing required headers"}
                )
        
        return await call_next(request)


def setup_security_middleware(app):
    """Setup all security middleware for the application."""
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "https://gremlinsai.com"],  # Configure for production
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Response-Time"]
    )
    
    # Add CSRF protection
    app.add_middleware(CSRFProtectionMiddleware)
    
    # Add main security middleware
    security_middleware = SecurityMiddleware(app, max_requests_per_minute=100)
    app.add_middleware(SecurityMiddleware, max_requests_per_minute=100)
    
    # Schedule cleanup task
    async def cleanup_task():
        while True:
            await asyncio.sleep(3600)  # Run every hour
            await security_middleware.cleanup_old_data()
    
    # Start cleanup task only if running within an event loop
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(cleanup_task())
    except RuntimeError:
        # No running loop during import-time app creation; will be scheduled on first request
        pass
