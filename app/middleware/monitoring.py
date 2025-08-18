"""
Monitoring Middleware for GremlinsAI Backend - Task T3.4

This module provides middleware for automatic instrumentation of API requests
with Prometheus metrics collection.

Features:
- Automatic API request monitoring
- Response time tracking
- Error rate monitoring
- Custom metric collection
"""

import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.monitoring.metrics import metrics

logger = logging.getLogger(__name__)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically collect Prometheus metrics for all API requests.
    
    This middleware instruments every HTTP request with:
    - Request duration
    - Request count by method, endpoint, and status code
    - Error count tracking
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        logger.info("Prometheus monitoring middleware initialized")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and collect metrics.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware or endpoint handler
            
        Returns:
            Response: The HTTP response
        """
        # Skip metrics collection for the metrics endpoint itself to avoid recursion
        if request.url.path == "/api/v1/metrics":
            return await call_next(request)
        
        # Record start time
        start_time = time.time()
        
        # Extract request information
        method = request.method
        path = request.url.path
        
        # Normalize path for metrics (remove dynamic segments)
        normalized_path = self._normalize_path(path)
        
        # Initialize response variables
        status_code = 500  # Default to error in case of exception
        response = None
        
        try:
            # Process the request
            response = await call_next(request)
            status_code = response.status_code
            
        except Exception as e:
            logger.error(f"Request processing error: {e}")
            status_code = 500
            raise
        
        finally:
            # Calculate duration
            duration = time.time() - start_time
            
            # Record metrics
            try:
                metrics.record_api_request(
                    method=method,
                    endpoint=normalized_path,
                    status_code=status_code,
                    duration=duration
                )
                
                # Log slow requests
                if duration > 5.0:  # Log requests taking more than 5 seconds
                    logger.warning(
                        f"Slow request detected: {method} {path} "
                        f"took {duration:.2f}s (status: {status_code})"
                    )
                
            except Exception as e:
                logger.error(f"Error recording metrics: {e}")
        
        return response
    
    def _normalize_path(self, path: str) -> str:
        """
        Normalize URL path for metrics collection.
        
        This method removes dynamic segments (like IDs) from paths to avoid
        creating too many unique metric labels.
        
        Args:
            path: The original URL path
            
        Returns:
            str: Normalized path suitable for metrics
        """
        # Common patterns to normalize
        normalizations = [
            # Replace UUIDs with placeholder
            (r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/{id}'),
            # Replace numeric IDs with placeholder
            (r'/\d+', '/{id}'),
            # Replace conversation IDs
            (r'/conversations/[^/]+', '/conversations/{id}'),
            # Replace task IDs
            (r'/tasks/[^/]+', '/tasks/{id}'),
            # Replace document IDs
            (r'/documents/[^/]+', '/documents/{id}'),
        ]
        
        import re
        normalized = path
        
        for pattern, replacement in normalizations:
            normalized = re.sub(pattern, replacement, normalized)
        
        return normalized


class SystemMetricsCollector:
    """
    Collector for system-level metrics that need periodic updates.
    
    This class provides methods to collect and update system metrics
    like active connections, memory usage, etc.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def collect_system_metrics(self):
        """Collect and update system-level metrics."""
        try:
            # Update memory usage (simplified example)
            import psutil
            import os
            
            # Get current process
            process = psutil.Process(os.getpid())
            
            # Memory usage
            memory_info = process.memory_info()
            metrics.update_memory_usage("application", memory_info.rss)
            
            # CPU usage could be added here
            # Database connection counts could be added here
            
        except ImportError:
            # psutil not available, skip system metrics
            pass
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
    
    async def update_conversation_metrics(self, active_count: int):
        """Update active conversation count."""
        try:
            metrics.update_active_conversations(active_count)
        except Exception as e:
            self.logger.error(f"Error updating conversation metrics: {e}")
    
    async def update_database_metrics(self, pool_name: str, connection_count: int):
        """Update database connection metrics."""
        try:
            metrics.update_database_connections(pool_name, connection_count)
        except Exception as e:
            self.logger.error(f"Error updating database metrics: {e}")


# Global system metrics collector instance
system_metrics = SystemMetricsCollector()
