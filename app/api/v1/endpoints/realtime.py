# app/api/v1/endpoints/realtime.py
"""
Enhanced REST API endpoints for real-time communication features.
Phase 6: API Modernization & Real-time Communication
"""

import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.realtime import (
    RealTimeAPIInfo,
    ConnectionInfo,
    SystemStatus,
    APICapabilities,
    ModernAPIResponse
)
from app.api.v1.websocket.connection_manager import connection_manager
from app.core.orchestrator import enhanced_orchestrator
from app.database.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/info", response_model=RealTimeAPIInfo, summary="Get Real-time API Information")
async def get_realtime_api_info():
    """
    Get information about the real-time API capabilities and current status.
    
    Returns:
        RealTimeAPIInfo: Information about WebSocket endpoints and capabilities
    """
    try:
        return RealTimeAPIInfo(
            websocket_endpoint="/api/v1/ws/ws",
            supported_message_types=[
                "subscribe",
                "unsubscribe", 
                "ping",
                "get_status"
            ],
            supported_subscriptions=[
                "conversation",
                "system",
                "task"
            ],
            connection_count=connection_manager.get_connection_count()
        )
    except Exception as e:
        logger.error(f"Error getting real-time API info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get API information")


@router.get("/connections", response_model=List[ConnectionInfo], summary="Get Active Connections")
async def get_active_connections():
    """
    Get information about all active WebSocket connections.
    
    Returns:
        List[ConnectionInfo]: List of active connection information
    """
    try:
        connections_data = connection_manager.get_all_connections_info()
        
        connections = []
        for connection_id, info in connections_data.items():
            connections.append(ConnectionInfo(
                connection_id=connection_id,
                connected_at=info["connected_at"],
                client_info=info["client_info"],
                subscriptions=info["subscriptions"]
            ))
        
        return connections
    except Exception as e:
        logger.error(f"Error getting active connections: {e}")
        raise HTTPException(status_code=500, detail="Failed to get connection information")


@router.get("/connections/{connection_id}", response_model=ConnectionInfo, summary="Get Connection Info")
async def get_connection_info(connection_id: str):
    """
    Get information about a specific WebSocket connection.
    
    Args:
        connection_id: The unique connection identifier
        
    Returns:
        ConnectionInfo: Connection information
    """
    try:
        info = connection_manager.get_connection_info(connection_id)
        
        if not info:
            raise HTTPException(status_code=404, detail="Connection not found")
        
        return ConnectionInfo(
            connection_id=connection_id,
            connected_at=info["connected_at"],
            client_info=info["client_info"],
            subscriptions=info["subscriptions"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting connection info for {connection_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get connection information")


@router.get("/system/status", response_model=SystemStatus, summary="Get System Status")
async def get_system_status():
    """
    Get current system status including component availability and performance metrics.
    
    Returns:
        SystemStatus: Current system status
    """
    try:
        capabilities = enhanced_orchestrator.get_capabilities()
        
        return SystemStatus(
            version=capabilities.get("version", "6.0.0"),
            active_connections=connection_manager.get_connection_count(),
            components={
                "database": True,
                "vector_store": capabilities.get("vector_store_available", False),
                "multi_agent": capabilities.get("multi_agent_available", False),
                "orchestrator": True,
                "websocket": True,
                "graphql": True
            },
            uptime=0.0  # Would be calculated from application startup time
        )
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system status")


@router.get("/capabilities", response_model=APICapabilities, summary="Get API Capabilities")
async def get_api_capabilities():
    """
    Get information about available API capabilities and features.
    
    Returns:
        APICapabilities: Available API capabilities
    """
    try:
        # Check if GraphQL is available
        graphql_available = True
        try:
            import strawberry
        except ImportError:
            graphql_available = False
        
        return APICapabilities(
            rest_api=True,
            graphql_api=graphql_available,
            websocket_api=True,
            real_time_subscriptions=True,
            supported_features=[
                "REST API",
                "GraphQL API" if graphql_available else "GraphQL API (disabled)",
                "WebSocket Real-time Communication",
                "Multi-Agent Workflows",
                "Document Management & RAG",
                "Asynchronous Task Orchestration",
                "Real-time Subscriptions",
                "Cross-API Integration"
            ]
        )
    except Exception as e:
        logger.error(f"Error getting API capabilities: {e}")
        raise HTTPException(status_code=500, detail="Failed to get API capabilities")


@router.post("/broadcast/conversation/{conversation_id}", summary="Broadcast to Conversation")
async def broadcast_to_conversation(
    conversation_id: str,
    message: Dict[str, Any],
    update_type: str = Query("custom", description="Type of update to broadcast")
):
    """
    Broadcast a message to all subscribers of a specific conversation.
    
    Args:
        conversation_id: The conversation ID to broadcast to
        message: The message data to broadcast
        update_type: Type of update (new_message, status_change, etc.)
        
    Returns:
        Dict: Broadcast result
    """
    try:
        from app.api.v1.websocket.endpoints import broadcast_conversation_update
        
        await broadcast_conversation_update(conversation_id, update_type, message)
        
        return ModernAPIResponse(
            data={
                "success": True,
                "conversation_id": conversation_id,
                "update_type": update_type,
                "subscribers_notified": len(connection_manager.conversation_subscribers.get(conversation_id, set()))
            },
            metadata={
                "action": "broadcast_conversation_update",
                "conversation_id": conversation_id
            },
            timestamp=logger.info(f"Broadcasted message to conversation {conversation_id}")
        )
    except Exception as e:
        logger.error(f"Error broadcasting to conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to broadcast message")


@router.post("/broadcast/system", summary="Broadcast System Message")
async def broadcast_system_message(
    message: Dict[str, Any],
    event_type: str = Query("custom", description="Type of system event")
):
    """
    Broadcast a system message to all system subscribers.
    
    Args:
        message: The message data to broadcast
        event_type: Type of system event
        
    Returns:
        Dict: Broadcast result
    """
    try:
        from app.api.v1.websocket.endpoints import broadcast_system_event
        
        await broadcast_system_event(event_type, message)
        
        return ModernAPIResponse(
            data={
                "success": True,
                "event_type": event_type,
                "subscribers_notified": len(connection_manager.system_subscribers)
            },
            metadata={
                "action": "broadcast_system_message",
                "event_type": event_type
            },
            timestamp=logger.info(f"Broadcasted system message: {event_type}")
        )
    except Exception as e:
        logger.error(f"Error broadcasting system message: {e}")
        raise HTTPException(status_code=500, detail="Failed to broadcast system message")


@router.post("/broadcast/task/{task_id}", summary="Broadcast Task Update")
async def broadcast_task_update(
    task_id: str,
    progress: float = Query(..., description="Task progress (0.0 to 1.0)"),
    status: str = Query(..., description="Task status"),
    result: str = Query(None, description="Task result if completed")
):
    """
    Broadcast a task update to all subscribers of a specific task.
    
    Args:
        task_id: The task ID to broadcast to
        progress: Task progress (0.0 to 1.0)
        status: Task status
        result: Task result if completed
        
    Returns:
        Dict: Broadcast result
    """
    try:
        from app.api.v1.websocket.endpoints import broadcast_task_progress
        
        await broadcast_task_progress(task_id, progress, status, result)
        
        return ModernAPIResponse(
            data={
                "success": True,
                "task_id": task_id,
                "progress": progress,
                "status": status,
                "subscribers_notified": len(connection_manager.task_subscribers.get(task_id, set()))
            },
            metadata={
                "action": "broadcast_task_update",
                "task_id": task_id
            },
            timestamp=logger.info(f"Broadcasted task update for {task_id}")
        )
    except Exception as e:
        logger.error(f"Error broadcasting task update for {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to broadcast task update")


@router.get("/health", summary="Real-time API Health Check")
async def realtime_health_check():
    """
    Health check endpoint for real-time API components.
    
    Returns:
        Dict: Health status of real-time components
    """
    try:
        # Check WebSocket manager
        websocket_healthy = connection_manager is not None
        
        # Check GraphQL availability
        graphql_healthy = True
        try:
            import strawberry
            from app.api.v1.graphql.schema import graphql_schema
        except ImportError:
            graphql_healthy = False
        
        health_status = {
            "status": "healthy" if websocket_healthy and graphql_healthy else "degraded",
            "components": {
                "websocket_manager": websocket_healthy,
                "graphql": graphql_healthy,
                "connection_count": connection_manager.get_connection_count() if websocket_healthy else 0
            },
            "timestamp": logger.info("Real-time API health check completed")
        }
        
        return health_status
    except Exception as e:
        logger.error(f"Error in real-time health check: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": logger.error("Real-time API health check failed")
        }
