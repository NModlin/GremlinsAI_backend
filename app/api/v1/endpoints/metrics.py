"""
Prometheus Metrics Endpoint - Task T3.4

This module provides the /metrics endpoint for Prometheus to scrape
application metrics and monitoring data.

Features:
- Prometheus metrics exposition
- Health check integration
- Custom AI metrics exposure
- Performance monitoring data
"""

from fastapi import APIRouter, Response
from fastapi.responses import PlainTextResponse
import logging

from app.monitoring.metrics import metrics, CONTENT_TYPE_LATEST

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/metrics", response_class=PlainTextResponse)
async def get_prometheus_metrics():
    """
    Expose Prometheus metrics for scraping.
    
    This endpoint provides all application metrics in Prometheus format,
    including custom AI metrics for monitoring system performance.
    
    Returns:
        PlainTextResponse: Prometheus metrics in text format
    """
    try:
        # Get metrics from the global metrics instance
        metrics_data = metrics.get_metrics()
        
        # Return metrics with proper content type
        return Response(
            content=metrics_data,
            media_type=CONTENT_TYPE_LATEST
        )
    
    except Exception as e:
        logger.error(f"Error generating Prometheus metrics: {e}")
        # Return empty metrics on error to avoid breaking Prometheus scraping
        return Response(
            content="# Error generating metrics\n",
            media_type=CONTENT_TYPE_LATEST
        )


@router.get("/metrics/health")
async def metrics_health():
    """
    Health check endpoint for metrics system.
    
    Returns:
        dict: Health status of the metrics system
    """
    try:
        # Test metrics generation
        metrics_data = metrics.get_metrics()
        
        return {
            "status": "healthy",
            "metrics_available": True,
            "metrics_size_bytes": len(metrics_data),
            "message": "Metrics system is operational"
        }
    
    except Exception as e:
        logger.error(f"Metrics health check failed: {e}")
        return {
            "status": "unhealthy",
            "metrics_available": False,
            "error": str(e),
            "message": "Metrics system is experiencing issues"
        }
