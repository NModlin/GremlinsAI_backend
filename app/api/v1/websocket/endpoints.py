# app/api/v1/websocket/endpoints.py
"""
WebSocket endpoints for real-time communication.
Provides real-time updates for conversations, tasks, and system events.
"""

import json
import logging
import uuid
from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.websocket.connection_manager import connection_manager
from app.database.database import get_db
from app.services.chat_history import ChatHistoryService
from app.core.orchestrator import enhanced_orchestrator
from app.core.security import verify_api_key, check_rate_limit, sanitize_input

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/collaborate/{document_id}")
async def collaborate_websocket_endpoint(
    websocket: WebSocket,
    document_id: str,
    user_id: str = Query(..., description="User ID for collaboration"),
    display_name: str = Query(..., description="Display name for the user"),
    api_key: str = Query(None, description="Optional API key for authentication")
):
    """
    WebSocket endpoint for real-time collaborative editing.

    This endpoint implements the collaborative editing system with:
    - Sub-200ms message latency
    - Support for 100+ concurrent users per document
    - Graceful handling of disconnections
    - Redis pub/sub for horizontal scaling

    Path Parameters:
    - document_id: ID of the document being collaboratively edited

    Query Parameters:
    - user_id: Unique identifier for the user
    - display_name: Display name for the user
    - api_key: Optional API key for authentication
    """
    from app.core.realtime_manager import realtime_manager
    from app.services.collaboration_service import CollaborationService
    from datetime import datetime

    connection_id = None
    collaboration_service = CollaborationService()

    try:
        # Establish WebSocket connection
        connection_id = await realtime_manager.handle_connection(
            websocket=websocket,
            user_id=user_id,
            connection_metadata={
                "display_name": display_name,
                "document_id": document_id,
                "api_key": api_key
            }
        )

        # Join the document room
        room_id = f"document:{document_id}"
        await realtime_manager.join_room(connection_id, room_id, document_id)

        # Initialize collaborative editing session
        await collaboration_service.join_document_session(
            document_id=document_id,
            user_id=user_id,
            connection_id=connection_id,
            display_name=display_name
        )

        # Message processing loop
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_json()

                # Process message through real-time manager
                await realtime_manager.process_message(connection_id, data)

                # Handle collaborative editing specific messages
                if data.get("type") == "document_edit":
                    await collaboration_service.handle_document_edit(
                        document_id=document_id,
                        user_id=user_id,
                        edit_data=data,
                        connection_id=connection_id
                    )

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: {connection_id}")
                break
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                await websocket.send_json({
                    "type": "error",
                    "error": "Failed to process message",
                    "timestamp": datetime.utcnow().isoformat()
                })

    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")

    finally:
        # Clean up connection
        if connection_id:
            await collaboration_service.leave_document_session(
                document_id=document_id,
                user_id=user_id,
                connection_id=connection_id
            )
            await realtime_manager._handle_disconnect(connection_id)


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: Optional[str] = Query(None),
    client_type: Optional[str] = Query("web"),
    api_key: Optional[str] = Query(None)
):
    """
    Main WebSocket endpoint for real-time communication.

    Query Parameters:
    - client_id: Optional client identifier
    - client_type: Type of client (web, mobile, etc.)
    - api_key: Optional API key for authentication
    """
    # Generate connection ID
    connection_id = client_id or str(uuid.uuid4())

    # Security check - verify API key if provided
    user_info = None
    if api_key:
        user_info = verify_api_key(api_key)
        if not user_info:
            await websocket.close(code=4001, reason="Invalid API key")
            return

    # Rate limiting check
    client_ip = websocket.client.host if websocket.client else "unknown"
    if not check_rate_limit(client_ip):
        await websocket.close(code=4029, reason="Rate limit exceeded")
        return

    # Client information
    client_info = {
        "client_type": client_type,
        "user_agent": websocket.headers.get("user-agent", ""),
        "origin": websocket.headers.get("origin", ""),
        "authenticated": user_info is not None,
        "user_id": user_info.get("user_id") if user_info else None
    }

    # Establish connection
    connected = await connection_manager.connect(websocket, connection_id, client_info)
    
    if not connected:
        await websocket.close(code=1000, reason="Failed to establish connection")
        return
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                # Sanitize input data before parsing
                sanitized_data = sanitize_input(data, max_length=10000)
                message = json.loads(sanitized_data)

                # Additional sanitization for message content
                if isinstance(message, dict):
                    for key, value in message.items():
                        if isinstance(value, str):
                            message[key] = sanitize_input(value)

                await handle_websocket_message(connection_id, message, user_info)
                
            except json.JSONDecodeError:
                await connection_manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": connection_manager.connection_metadata[connection_id]["connected_at"].isoformat()
                }, connection_id)
            
            except Exception as e:
                logger.error(f"Error handling WebSocket message from {connection_id}: {e}")
                await connection_manager.send_personal_message({
                    "type": "error",
                    "message": "Internal server error",
                    "timestamp": connection_manager.connection_metadata[connection_id]["connected_at"].isoformat()
                }, connection_id)
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket client {connection_id} disconnected")
    
    except Exception as e:
        logger.error(f"WebSocket error for {connection_id}: {e}")
    
    finally:
        connection_manager.disconnect(connection_id)


async def handle_websocket_message(connection_id: str, message: Dict[str, Any], user_info: Optional[Dict[str, Any]] = None):
    """Handle incoming WebSocket messages."""
    message_type = message.get("type")
    
    if message_type == "subscribe":
        await handle_subscribe_message(connection_id, message)
    
    elif message_type == "unsubscribe":
        await handle_unsubscribe_message(connection_id, message)
    
    elif message_type == "ping":
        await connection_manager.send_personal_message({
            "type": "pong",
            "timestamp": connection_manager.connection_metadata[connection_id]["connected_at"].isoformat()
        }, connection_id)
    
    elif message_type == "get_status":
        await handle_status_request(connection_id, message)
    
    else:
        await connection_manager.send_personal_message({
            "type": "error",
            "message": f"Unknown message type: {message_type}",
            "supported_types": ["subscribe", "unsubscribe", "ping", "get_status"]
        }, connection_id)


async def handle_subscribe_message(connection_id: str, message: Dict[str, Any]):
    """Handle subscription requests."""
    subscription_type = message.get("subscription_type")
    
    if subscription_type == "conversation":
        conversation_id = message.get("conversation_id")
        if conversation_id:
            success = connection_manager.subscribe_to_conversation(connection_id, conversation_id)
            await connection_manager.send_personal_message({
                "type": "subscription_confirmed",
                "subscription_type": "conversation",
                "conversation_id": conversation_id,
                "success": success
            }, connection_id)
        else:
            await connection_manager.send_personal_message({
                "type": "error",
                "message": "conversation_id required for conversation subscription"
            }, connection_id)
    
    elif subscription_type == "system":
        success = connection_manager.subscribe_to_system(connection_id)
        await connection_manager.send_personal_message({
            "type": "subscription_confirmed",
            "subscription_type": "system",
            "success": success
        }, connection_id)
    
    elif subscription_type == "task":
        task_id = message.get("task_id")
        if task_id:
            success = connection_manager.subscribe_to_task(connection_id, task_id)
            await connection_manager.send_personal_message({
                "type": "subscription_confirmed",
                "subscription_type": "task",
                "task_id": task_id,
                "success": success
            }, connection_id)
        else:
            await connection_manager.send_personal_message({
                "type": "error",
                "message": "task_id required for task subscription"
            }, connection_id)
    
    else:
        await connection_manager.send_personal_message({
            "type": "error",
            "message": f"Unknown subscription type: {subscription_type}",
            "supported_types": ["conversation", "system", "task"]
        }, connection_id)


async def handle_unsubscribe_message(connection_id: str, message: Dict[str, Any]):
    """Handle unsubscription requests."""
    subscription_type = message.get("subscription_type")
    
    if subscription_type == "conversation":
        conversation_id = message.get("conversation_id")
        if conversation_id:
            connection_manager.unsubscribe_from_conversation(connection_id, conversation_id)
            await connection_manager.send_personal_message({
                "type": "unsubscription_confirmed",
                "subscription_type": "conversation",
                "conversation_id": conversation_id
            }, connection_id)
    
    elif subscription_type == "system":
        connection_manager.unsubscribe_from_system(connection_id)
        await connection_manager.send_personal_message({
            "type": "unsubscription_confirmed",
            "subscription_type": "system"
        }, connection_id)
    
    elif subscription_type == "task":
        task_id = message.get("task_id")
        if task_id:
            connection_manager.unsubscribe_from_task(connection_id, task_id)
            await connection_manager.send_personal_message({
                "type": "unsubscription_confirmed",
                "subscription_type": "task",
                "task_id": task_id
            }, connection_id)


async def handle_status_request(connection_id: str, message: Dict[str, Any]):
    """Handle status requests."""
    status_type = message.get("status_type", "connection")
    
    if status_type == "connection":
        connection_info = connection_manager.get_connection_info(connection_id)
        await connection_manager.send_personal_message({
            "type": "status_response",
            "status_type": "connection",
            "data": connection_info
        }, connection_id)
    
    elif status_type == "system":
        try:
            capabilities = enhanced_orchestrator.get_capabilities()
            await connection_manager.send_personal_message({
                "type": "status_response",
                "status_type": "system",
                "data": {
                    "version": capabilities.get("version", "unknown"),
                    "active_connections": connection_manager.get_connection_count(),
                    "components": {
                        "database": True,
                        "vector_store": capabilities.get("vector_store_available", False),
                        "multi_agent": capabilities.get("multi_agent_available", False),
                        "orchestrator": True
                    }
                }
            }, connection_id)
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            await connection_manager.send_personal_message({
                "type": "error",
                "message": "Failed to get system status"
            }, connection_id)


# WebSocket utility functions for broadcasting updates

async def broadcast_conversation_update(conversation_id: str, update_type: str, data: Dict[str, Any]):
    """Broadcast a conversation update to all subscribers."""
    message = {
        "type": "conversation_update",
        "update_type": update_type,
        "data": data
    }
    await connection_manager.broadcast_to_conversation(conversation_id, message)


async def broadcast_new_message(conversation_id: str, message_data: Dict[str, Any]):
    """Broadcast a new message to conversation subscribers."""
    await broadcast_conversation_update(conversation_id, "new_message", message_data)


async def broadcast_task_progress(task_id: str, progress: float, status: str, result: Optional[str] = None):
    """Broadcast task progress to task subscribers."""
    message = {
        "progress": progress,
        "status": status,
        "result": result
    }
    await connection_manager.broadcast_task_update(task_id, message)


async def broadcast_system_event(event_type: str, data: Dict[str, Any]):
    """Broadcast a system event to all system subscribers."""
    message = {
        "event_type": event_type,
        "data": data
    }
    await connection_manager.broadcast_system_message(message)
