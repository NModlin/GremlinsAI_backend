"""
Middleware package for GremlinsAI Backend.

This package provides middleware components for:
- Request monitoring and metrics collection
- Performance tracking
- System health monitoring
"""

from .monitoring import PrometheusMiddleware, system_metrics

__all__ = [
    'PrometheusMiddleware',
    'system_metrics'
]
