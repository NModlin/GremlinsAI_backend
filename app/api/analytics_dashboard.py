# app/api/analytics_dashboard.py
"""
Analytics Dashboard API Endpoints

This module provides REST API endpoints for the GremlinsAI analytics dashboard,
delivering real-time insights into AI performance metrics, tool usage patterns,
and user behavior analytics.

Features:
- Real-time analytics data with <5 minute latency
- Tool usage statistics and optimization insights
- Query trend analysis and user behavior patterns
- Performance metrics and benchmarking
- Interactive dashboard data endpoints
- Comprehensive business intelligence APIs
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from app.services.analytics_service import analytics_service, TimeWindow, MetricType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


# Pydantic models for API responses
class ToolUsageResponse(BaseModel):
    """Response model for tool usage analytics."""
    tool_name: str
    usage_count: int
    success_rate: float = Field(..., ge=0.0, le=1.0)
    avg_execution_time: float = Field(..., ge=0.0)
    unique_users: int = Field(..., ge=0)
    efficiency_score: Optional[float] = None


class QueryTrendResponse(BaseModel):
    """Response model for query trend analytics."""
    keyword: Optional[str] = None
    category: Optional[str] = None
    frequency: int = Field(..., ge=0)
    trend_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    percentage: Optional[float] = Field(None, ge=0.0, le=1.0)


class PerformanceMetricResponse(BaseModel):
    """Response model for performance metrics."""
    agent_type: str
    avg_response_time: float = Field(..., ge=0.0)
    success_rate: float = Field(..., ge=0.0, le=1.0)
    total_interactions: int = Field(..., ge=0)
    avg_reasoning_steps: float = Field(..., ge=0.0)
    avg_token_usage: float = Field(..., ge=0.0)
    performance_grade: Optional[str] = None


class AnalyticsSummaryResponse(BaseModel):
    """Response model for analytics summary."""
    total_interactions: int
    active_users: int
    top_performing_agent: str
    most_used_tool: str
    avg_response_time: float
    overall_success_rate: float
    time_window: str
    last_updated: str


class DashboardMetricsResponse(BaseModel):
    """Comprehensive dashboard metrics response."""
    summary: AnalyticsSummaryResponse
    tool_usage: List[ToolUsageResponse]
    query_trends: List[QueryTrendResponse]
    performance_metrics: List[PerformanceMetricResponse]
    processing_status: Dict[str, Any]


def get_time_window_param(
    time_window: str = Query("24h", description="Time window for analytics (1h, 24h, 7d, 30d)")
) -> TimeWindow:
    """Parse and validate time window parameter."""
    try:
        return TimeWindow(time_window)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid time window: {time_window}. Must be one of: 1h, 24h, 7d, 30d"
        )


@router.get("/tool_usage", response_model=List[ToolUsageResponse])
async def get_tool_usage_analytics(
    time_window: TimeWindow = Depends(get_time_window_param),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of tools to return")
):
    """
    Get tool usage analytics and optimization insights.
    
    Returns the most frequently used tools with success rates, execution times,
    and usage patterns to help optimize tool selection and performance.
    
    Args:
        time_window: Time window for analytics (1h, 24h, 7d, 30d)
        limit: Maximum number of tools to return
        
    Returns:
        List of tool usage metrics sorted by usage frequency
    """
    try:
        logger.info(f"Fetching tool usage analytics for {time_window.value} window")
        
        # Get tool usage metrics from analytics service
        tool_metrics = await analytics_service.get_tool_usage_metrics(time_window)
        
        # Process and enhance metrics
        enhanced_metrics = []
        for metric in tool_metrics[:limit]:
            # Calculate efficiency score (success rate weighted by execution time)
            efficiency_score = (
                metric["success_rate"] * (1.0 / max(metric["avg_execution_time"], 0.1))
            ) if metric["avg_execution_time"] > 0 else metric["success_rate"]
            
            enhanced_metric = ToolUsageResponse(
                tool_name=metric["tool_name"],
                usage_count=metric["usage_count"],
                success_rate=metric["success_rate"],
                avg_execution_time=metric["avg_execution_time"],
                unique_users=metric["unique_users"],
                efficiency_score=min(efficiency_score, 10.0)  # Cap at 10.0
            )
            enhanced_metrics.append(enhanced_metric)
        
        logger.info(f"Returning {len(enhanced_metrics)} tool usage metrics")
        return enhanced_metrics
        
    except Exception as e:
        logger.error(f"Error fetching tool usage analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch tool usage analytics")


@router.get("/query_trends", response_model=List[QueryTrendResponse])
async def get_query_trend_analytics(
    time_window: TimeWindow = Depends(get_time_window_param),
    limit: int = Query(30, ge=1, le=100, description="Maximum number of trends to return"),
    category: Optional[str] = Query(None, description="Filter by query category")
):
    """
    Get query trend analytics and user behavior patterns.
    
    Returns common topics, keywords, and query patterns to understand
    user behavior and optimize content and responses.
    
    Args:
        time_window: Time window for analytics (1h, 24h, 7d, 30d)
        limit: Maximum number of trends to return
        category: Optional category filter
        
    Returns:
        List of query trend metrics sorted by frequency
    """
    try:
        logger.info(f"Fetching query trend analytics for {time_window.value} window")
        
        # Get query trend metrics from analytics service
        trend_metrics = await analytics_service.get_query_trend_metrics(time_window)
        
        # Filter by category if specified
        if category:
            trend_metrics = [m for m in trend_metrics if m.get("category") == category]
        
        # Convert to response models
        response_metrics = []
        for metric in trend_metrics[:limit]:
            response_metric = QueryTrendResponse(
                keyword=metric.get("keyword"),
                category=metric.get("category"),
                frequency=metric["frequency"],
                trend_score=metric.get("trend_score"),
                percentage=metric.get("percentage")
            )
            response_metrics.append(response_metric)
        
        logger.info(f"Returning {len(response_metrics)} query trend metrics")
        return response_metrics
        
    except Exception as e:
        logger.error(f"Error fetching query trend analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch query trend analytics")


@router.get("/performance_metrics", response_model=List[PerformanceMetricResponse])
async def get_performance_analytics(
    time_window: TimeWindow = Depends(get_time_window_param),
    agent_type: Optional[str] = Query(None, description="Filter by agent type")
):
    """
    Get agent performance metrics and benchmarking data.
    
    Returns average response times, success rates, and performance
    benchmarks for different agent types to optimize system performance.
    
    Args:
        time_window: Time window for analytics (1h, 24h, 7d, 30d)
        agent_type: Optional agent type filter
        
    Returns:
        List of performance metrics by agent type
    """
    try:
        logger.info(f"Fetching performance analytics for {time_window.value} window")
        
        # Get performance metrics from analytics service
        performance_metrics = await analytics_service.get_performance_metrics(time_window)
        
        # Filter by agent type if specified
        if agent_type:
            performance_metrics = [m for m in performance_metrics if m["agent_type"] == agent_type]
        
        # Process and enhance metrics
        enhanced_metrics = []
        for metric in performance_metrics:
            # Calculate performance grade based on success rate and response time
            success_rate = metric["success_rate"]
            response_time = metric["avg_response_time"]
            
            if success_rate >= 0.95 and response_time <= 2.0:
                grade = "A"
            elif success_rate >= 0.90 and response_time <= 3.0:
                grade = "B"
            elif success_rate >= 0.85 and response_time <= 5.0:
                grade = "C"
            elif success_rate >= 0.80:
                grade = "D"
            else:
                grade = "F"
            
            enhanced_metric = PerformanceMetricResponse(
                agent_type=metric["agent_type"],
                avg_response_time=metric["avg_response_time"],
                success_rate=metric["success_rate"],
                total_interactions=metric["total_interactions"],
                avg_reasoning_steps=metric["avg_reasoning_steps"],
                avg_token_usage=metric["avg_token_usage"],
                performance_grade=grade
            )
            enhanced_metrics.append(enhanced_metric)
        
        logger.info(f"Returning {len(enhanced_metrics)} performance metrics")
        return enhanced_metrics
        
    except Exception as e:
        logger.error(f"Error fetching performance analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch performance analytics")


@router.get("/summary", response_model=AnalyticsSummaryResponse)
async def get_analytics_summary(
    time_window: TimeWindow = Depends(get_time_window_param)
):
    """
    Get high-level analytics summary for dashboard overview.
    
    Returns key performance indicators and summary statistics
    for quick system health assessment.
    
    Args:
        time_window: Time window for analytics (1h, 24h, 7d, 30d)
        
    Returns:
        Analytics summary with key metrics
    """
    try:
        logger.info(f"Fetching analytics summary for {time_window.value} window")
        
        # Get all metrics
        tool_metrics = await analytics_service.get_tool_usage_metrics(time_window)
        performance_metrics = await analytics_service.get_performance_metrics(time_window)
        
        # Calculate summary statistics
        total_interactions = sum(m["total_interactions"] for m in performance_metrics)
        active_users = sum(m["unique_users"] for m in tool_metrics)
        
        # Find top performing agent
        top_agent = max(performance_metrics, key=lambda x: x["success_rate"])["agent_type"] if performance_metrics else "unknown"
        
        # Find most used tool
        most_used_tool = tool_metrics[0]["tool_name"] if tool_metrics else "unknown"
        
        # Calculate overall averages
        avg_response_time = sum(m["avg_response_time"] * m["total_interactions"] for m in performance_metrics) / max(total_interactions, 1)
        overall_success_rate = sum(m["success_rate"] * m["total_interactions"] for m in performance_metrics) / max(total_interactions, 1)
        
        summary = AnalyticsSummaryResponse(
            total_interactions=total_interactions,
            active_users=active_users,
            top_performing_agent=top_agent,
            most_used_tool=most_used_tool,
            avg_response_time=avg_response_time,
            overall_success_rate=overall_success_rate,
            time_window=time_window.value,
            last_updated=datetime.utcnow().isoformat()
        )
        
        logger.info("Analytics summary generated successfully")
        return summary
        
    except Exception as e:
        logger.error(f"Error generating analytics summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate analytics summary")


@router.get("/dashboard", response_model=DashboardMetricsResponse)
async def get_dashboard_metrics(
    time_window: TimeWindow = Depends(get_time_window_param)
):
    """
    Get comprehensive dashboard metrics in a single request.
    
    Returns all analytics data needed for the dashboard including
    summary, tool usage, query trends, and performance metrics.
    
    Args:
        time_window: Time window for analytics (1h, 24h, 7d, 30d)
        
    Returns:
        Complete dashboard metrics bundle
    """
    try:
        logger.info(f"Fetching comprehensive dashboard metrics for {time_window.value} window")
        
        # Fetch all metrics concurrently
        import asyncio
        
        summary_task = get_analytics_summary(time_window)
        tool_usage_task = get_tool_usage_analytics(time_window, limit=10)
        query_trends_task = get_query_trend_analytics(time_window, limit=15)
        performance_task = get_performance_analytics(time_window)
        
        summary, tool_usage, query_trends, performance_metrics = await asyncio.gather(
            summary_task, tool_usage_task, query_trends_task, performance_task
        )
        
        # Get processing status
        processing_status = analytics_service.get_processing_status()
        
        dashboard_response = DashboardMetricsResponse(
            summary=summary,
            tool_usage=tool_usage,
            query_trends=query_trends,
            performance_metrics=performance_metrics,
            processing_status=processing_status
        )
        
        logger.info("Dashboard metrics bundle generated successfully")
        return dashboard_response
        
    except Exception as e:
        logger.error(f"Error fetching dashboard metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard metrics")


@router.post("/process")
async def trigger_analytics_processing(
    time_window: TimeWindow = Depends(get_time_window_param)
):
    """
    Manually trigger analytics data processing.
    
    This endpoint allows manual triggering of the analytics processing
    pipeline for testing or immediate data refresh.
    
    Args:
        time_window: Time window for processing (1h, 24h, 7d, 30d)
        
    Returns:
        Processing results and metrics
    """
    try:
        logger.info(f"Manually triggering analytics processing for {time_window.value} window")
        
        # Trigger processing
        result = await analytics_service.process_interaction_data(time_window)
        
        return {
            "status": "success",
            "message": "Analytics processing completed",
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error triggering analytics processing: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger analytics processing")


@router.get("/status")
async def get_analytics_status():
    """
    Get analytics service status and health information.
    
    Returns:
        Service status, processing metrics, and health indicators
    """
    try:
        status = analytics_service.get_processing_status()
        
        return {
            "service": "analytics",
            "status": "healthy",
            "version": "1.0.0",
            "capabilities": [
                "real_time_processing",
                "tool_usage_analytics", 
                "query_trend_analysis",
                "performance_metrics",
                "dashboard_apis"
            ],
            "processing_status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting analytics status: {e}")
        return {
            "service": "analytics",
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
