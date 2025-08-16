# app/api/v1/endpoints/health.py
"""
Health check endpoints for monitoring LLM system status and performance.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging
import time

from app.core.llm_config import (
    get_llm_health_status,
    get_llm_metrics,
    get_llm_info,
    get_pool_stats,
    reset_llm_metrics
)

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/health", response_model=Dict[str, Any])
async def get_health_status():
    """
    Get comprehensive health status of the LLM system.
    
    Returns:
        Dictionary with health status, metrics, and system information
    """
    try:
        health_status = get_llm_health_status()
        return health_status
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@router.get("/health/metrics", response_model=Dict[str, Any])
async def get_metrics():
    """
    Get detailed LLM usage metrics.
    
    Returns:
        Dictionary with usage statistics and performance metrics
    """
    try:
        metrics = get_llm_metrics()
        return {
            "status": "success",
            "metrics": metrics
        }
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")

@router.post("/health/metrics/reset")
async def reset_metrics():
    """
    Reset LLM usage metrics.
    
    Returns:
        Confirmation of metrics reset
    """
    try:
        reset_llm_metrics()
        return {
            "status": "success",
            "message": "LLM metrics have been reset"
        }
    except Exception as e:
        logger.error(f"Failed to reset metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset metrics: {str(e)}")

@router.get("/health/llm", response_model=Dict[str, Any])
async def get_llm_status():
    """
    Get detailed LLM configuration and status information.
    
    Returns:
        Dictionary with LLM configuration, cache status, and pool information
    """
    try:
        llm_info = get_llm_info()
        return {
            "status": "success",
            "llm_info": llm_info
        }
    except Exception as e:
        logger.error(f"Failed to get LLM status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get LLM status: {str(e)}")

@router.get("/health/pools", response_model=Dict[str, Any])
async def get_pool_status():
    """
    Get connection pool status and statistics.
    
    Returns:
        Dictionary with pool statistics for all active pools
    """
    try:
        pool_stats = get_pool_stats()
        return {
            "status": "success",
            "pools": pool_stats
        }
    except Exception as e:
        logger.error(f"Failed to get pool status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get pool status: {str(e)}")

@router.get("/health/detailed", response_model=Dict[str, Any])
async def get_detailed_health():
    """
    Get comprehensive system health information including all subsystems.
    
    Returns:
        Dictionary with complete health status, metrics, LLM info, and pool stats
    """
    try:
        health_status = get_llm_health_status()
        metrics = get_llm_metrics()
        llm_info = get_llm_info()
        pool_stats = get_pool_stats()
        
        return {
            "status": health_status["status"],
            "health_score": health_status["health_score"],
            "timestamp": health_status["timestamp"],
            "health_details": health_status,
            "metrics": metrics,
            "llm_info": llm_info,
            "pool_stats": pool_stats
        }
    except Exception as e:
        logger.error(f"Failed to get detailed health: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get detailed health: {str(e)}")

@router.get("/health/quick", response_model=Dict[str, Any])
async def get_quick_health():
    """
    Get quick health check for monitoring systems.
    
    Returns:
        Simple health status for monitoring and alerting
    """
    try:
        health_status = get_llm_health_status()
        
        return {
            "status": health_status["status"],
            "health_score": health_status["health_score"],
            "llm_available": health_status["llm_available"],
            "provider": health_status["provider"],
            "model": health_status["model"],
            "timestamp": health_status["timestamp"],
            "issues": health_status.get("issues", [])
        }
    except Exception as e:
        logger.error(f"Quick health check failed: {e}")
        return {
            "status": "error",
            "health_score": 0,
            "error": str(e),
            "timestamp": time.time()
        }
