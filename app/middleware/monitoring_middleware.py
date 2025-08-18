"""
Monitoring Middleware for Phase 4, Task 4.2: Monitoring & Observability

This middleware provides comprehensive request/response monitoring by intercepting
every API request to record metrics for Prometheus. It tracks latency, status codes,
request/response sizes, and other operational metrics.

Features:
- Request latency measurement
- HTTP status code tracking
- Request/response size monitoring
- Endpoint-specific metrics
- Error rate calculation
- Performance bottleneck identification
"""

import time
import sys
from typing import Dict, Optional, Callable
from urllib.parse import urlparse

from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse

from app.core.metrics_service import metrics_service
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class MonitoringMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive monitoring middleware for request/response metrics collection.
    
    Intercepts all HTTP requests to collect performance metrics, error rates,
    and operational data for Prometheus monitoring and alerting.
    """
    
    def __init__(self, app, exclude_paths: Optional[list] = None):
        """
        Initialize monitoring middleware.
        
        Args:
            app: FastAPI application instance
            exclude_paths: List of paths to exclude from monitoring
        """
        super().__init__(app)
        
        # Default paths to exclude from detailed monitoring
        self.exclude_paths = exclude_paths or [
            '/metrics',
            '/health',
            '/docs',
            '/openapi.json',
            '/favicon.ico'
        ]
        
        # Track active requests
        self.active_requests: Dict[str, float] = {}
        
        logger.info("MonitoringMiddleware initialized")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request through monitoring middleware.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain
            
        Returns:
            HTTP response with monitoring data collected
        """
        # Record request start time
        start_time = time.time()
        request_id = id(request)
        
        # Extract request information
        method = request.method
        path = request.url.path
        
        # Normalize endpoint path for metrics (remove IDs, etc.)
        normalized_endpoint = self._normalize_endpoint(path)
        
        # Skip monitoring for excluded paths
        if path in self.exclude_paths:
            return await call_next(request)
        
        # Track active request
        self.active_requests[str(request_id)] = start_time
        
        # Get request size
        request_size = self._get_request_size(request)
        
        # Initialize response variables
        response = None
        status_code = 500  # Default to error in case of exception
        response_size = 0
        
        try:
            # Process request
            response = await call_next(request)
            status_code = response.status_code
            
            # Get response size
            response_size = self._get_response_size(response)
            
        except Exception as e:
            # Log exception and set error status
            logger.error(f"Request processing error: {e}")
            status_code = 500
            
            # Create error response if none exists
            if response is None:
                from fastapi.responses import JSONResponse
                response = JSONResponse(
                    status_code=500,
                    content={"detail": "Internal server error"}
                )
        
        finally:
            # Calculate request duration
            duration = time.time() - start_time
            
            # Remove from active requests
            self.active_requests.pop(str(request_id), None)
            
            # Record metrics
            self._record_request_metrics(
                method=method,
                endpoint=normalized_endpoint,
                status_code=status_code,
                duration=duration,
                request_size=request_size,
                response_size=response_size
            )
            
            # Update active connections count
            metrics_service.set_active_connections('http', len(self.active_requests))
        
        return response
    
    def _normalize_endpoint(self, path: str) -> str:
        """
        Normalize endpoint path for consistent metrics.
        
        Replaces dynamic path parameters with placeholders to avoid
        high cardinality in metrics.
        
        Args:
            path: Original request path
            
        Returns:
            Normalized path for metrics
        """
        # Common API path patterns to normalize
        normalizations = [
            # Replace UUIDs
            (r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/{id}'),
            # Replace numeric IDs
            (r'/\d+', '/{id}'),
            # Replace conversation IDs
            (r'/conversations/[^/]+', '/conversations/{id}'),
            # Replace document IDs
            (r'/documents/[^/]+', '/documents/{id}'),
            # Replace user IDs
            (r'/users/[^/]+', '/users/{id}'),
        ]
        
        import re
        normalized_path = path
        
        for pattern, replacement in normalizations:
            normalized_path = re.sub(pattern, replacement, normalized_path)
        
        return normalized_path
    
    def _get_request_size(self, request: Request) -> int:
        """
        Get request content size in bytes.
        
        Args:
            request: HTTP request
            
        Returns:
            Request size in bytes
        """
        try:
            # Get content-length header
            content_length = request.headers.get('content-length')
            if content_length:
                return int(content_length)
            
            # Estimate size from headers and URL
            header_size = sum(len(k) + len(v) for k, v in request.headers.items())
            url_size = len(str(request.url))
            
            return header_size + url_size
            
        except Exception as e:
            logger.debug(f"Error calculating request size: {e}")
            return 0
    
    def _get_response_size(self, response: Response) -> int:
        """
        Get response content size in bytes.
        
        Args:
            response: HTTP response
            
        Returns:
            Response size in bytes
        """
        try:
            # Check content-length header
            content_length = response.headers.get('content-length')
            if content_length:
                return int(content_length)
            
            # For streaming responses, estimate from headers
            if isinstance(response, StreamingResponse):
                header_size = sum(len(k) + len(v) for k, v in response.headers.items())
                return header_size
            
            # Try to get body size
            if hasattr(response, 'body') and response.body:
                return len(response.body)
            
            # Estimate from headers
            header_size = sum(len(k) + len(v) for k, v in response.headers.items())
            return header_size
            
        except Exception as e:
            logger.debug(f"Error calculating response size: {e}")
            return 0
    
    def _record_request_metrics(self, method: str, endpoint: str, status_code: int,
                              duration: float, request_size: int, response_size: int):
        """
        Record request metrics to Prometheus.
        
        Args:
            method: HTTP method
            endpoint: Normalized endpoint path
            status_code: HTTP status code
            duration: Request duration in seconds
            request_size: Request size in bytes
            response_size: Response size in bytes
        """
        try:
            # Record HTTP request metrics
            metrics_service.record_http_request(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
                duration=duration,
                request_size=request_size,
                response_size=response_size
            )
            
            # Log slow requests
            if duration > 2.0:  # Log requests slower than 2 seconds
                logger.warning(
                    f"Slow request detected: {method} {endpoint} "
                    f"took {duration:.2f}s (status: {status_code})"
                )
            
            # Log error responses
            if status_code >= 400:
                logger.info(
                    f"Error response: {method} {endpoint} "
                    f"returned {status_code} in {duration:.3f}s"
                )
        
        except Exception as e:
            logger.error(f"Error recording request metrics: {e}")


class WebSocketMonitoringMixin:
    """
    Mixin class for WebSocket connection monitoring.
    
    Provides methods to track WebSocket connections and messages
    for operational visibility.
    """
    
    def __init__(self):
        """Initialize WebSocket monitoring."""
        self.active_websocket_connections: Dict[str, int] = {}
    
    def track_websocket_connection(self, endpoint: str, connected: bool = True):
        """
        Track WebSocket connection state.
        
        Args:
            endpoint: WebSocket endpoint
            connected: True if connecting, False if disconnecting
        """
        try:
            current_count = self.active_websocket_connections.get(endpoint, 0)
            
            if connected:
                new_count = current_count + 1
            else:
                new_count = max(0, current_count - 1)
            
            self.active_websocket_connections[endpoint] = new_count
            
            # Update metrics
            metrics_service.set_websocket_connections(endpoint, new_count)
            
            # Update total active connections
            total_ws_connections = sum(self.active_websocket_connections.values())
            metrics_service.set_active_connections('websocket', total_ws_connections)
            
            logger.debug(f"WebSocket connections for {endpoint}: {new_count}")
            
        except Exception as e:
            logger.error(f"Error tracking WebSocket connection: {e}")
    
    def track_websocket_message(self, endpoint: str, direction: str):
        """
        Track WebSocket message.
        
        Args:
            endpoint: WebSocket endpoint
            direction: 'inbound' or 'outbound'
        """
        try:
            metrics_service.record_websocket_message(endpoint, direction)
            
        except Exception as e:
            logger.error(f"Error tracking WebSocket message: {e}")


class HealthCheckMiddleware(BaseHTTPMiddleware):
    """
    Health check middleware for monitoring system health.
    
    Provides basic health status and readiness checks for
    load balancers and monitoring systems.
    """
    
    def __init__(self, app):
        """Initialize health check middleware."""
        super().__init__(app)
        self.start_time = time.time()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process health check requests."""
        path = request.url.path
        
        # Handle health check endpoints
        if path == '/health':
            return await self._health_check()
        elif path == '/ready':
            return await self._readiness_check()
        elif path == '/metrics':
            return await self._metrics_endpoint()
        
        # Continue with normal request processing
        return await call_next(request)
    
    async def _health_check(self) -> Response:
        """Basic health check endpoint."""
        from fastapi.responses import JSONResponse
        
        uptime = time.time() - self.start_time
        
        health_data = {
            "status": "healthy",
            "timestamp": time.time(),
            "uptime_seconds": uptime,
            "version": "1.0.0"
        }
        
        return JSONResponse(content=health_data)
    
    async def _readiness_check(self) -> Response:
        """Readiness check for Kubernetes."""
        from fastapi.responses import JSONResponse
        
        # Check if application is ready to serve traffic
        # This could include database connectivity, external service checks, etc.
        
        ready_data = {
            "status": "ready",
            "timestamp": time.time(),
            "checks": {
                "database": "ok",  # Would check actual database connectivity
                "external_services": "ok"  # Would check LLM providers, etc.
            }
        }
        
        return JSONResponse(content=ready_data)
    
    async def _metrics_endpoint(self) -> Response:
        """Prometheus metrics endpoint."""
        from fastapi.responses import Response as FastAPIResponse
        
        try:
            metrics_data = metrics_service.get_metrics()
            content_type = metrics_service.get_content_type()
            
            return FastAPIResponse(
                content=metrics_data,
                media_type=content_type
            )
        
        except Exception as e:
            logger.error(f"Error generating metrics: {e}")
            return FastAPIResponse(
                content="# Error generating metrics\n",
                status_code=500,
                media_type="text/plain"
            )


def setup_monitoring_middleware(app):
    """
    Setup all monitoring middleware for the application.
    
    Args:
        app: FastAPI application instance
    """
    # Add health check middleware first
    app.add_middleware(HealthCheckMiddleware)
    
    # Add monitoring middleware
    app.add_middleware(MonitoringMiddleware)
    
    logger.info("Monitoring middleware setup completed")


# Global WebSocket monitoring instance
websocket_monitor = WebSocketMonitoringMixin()
