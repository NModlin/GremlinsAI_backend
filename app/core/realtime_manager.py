"""
Real-time Manager for Phase 3, Task 3.3: Real-time Collaboration Features

This module provides the central RealTimeManager class responsible for handling
WebSocket connection lifecycle, room management, and Redis pub/sub broadcasting
for scalable real-time collaboration with sub-200ms latency.

Features:
- WebSocket connection management with graceful disconnection handling
- Room-based message broadcasting with Redis pub/sub for horizontal scaling
- Connection state management resilient to network issues
- Support for 100+ concurrent users per room
- Sub-200ms message latency for collaborative editing
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, Set, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from fastapi import WebSocket, WebSocketDisconnect

# Redis imports with fallback
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from app.core.config import get_settings
from app.core.logging_config import get_logger, log_performance, log_security_event

logger = get_logger(__name__)
settings = get_settings()


class ConnectionState(str, Enum):
    """WebSocket connection states."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class MessageType(str, Enum):
    """Real-time message types."""
    JOIN_ROOM = "join_room"
    LEAVE_ROOM = "leave_room"
    DOCUMENT_EDIT = "document_edit"
    CURSOR_POSITION = "cursor_position"
    USER_PRESENCE = "user_presence"
    SYSTEM_MESSAGE = "system_message"
    HEARTBEAT = "heartbeat"
    ERROR = "error"


@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection."""
    websocket: WebSocket
    user_id: str
    connection_id: str
    state: ConnectionState
    rooms: Set[str] = field(default_factory=set)
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoomInfo:
    """Information about a collaboration room."""
    room_id: str
    document_id: Optional[str]
    participants: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class RealTimeManager:
    """
    Central manager for real-time WebSocket connections and collaborative features.
    
    This class implements the technical architecture specified in prometheus.md
    for handling WebSocket connections, room management, and Redis pub/sub
    broadcasting for scalable real-time collaboration.
    """
    
    def __init__(self):
        """Initialize the real-time manager."""
        # Connection management
        self.connections: Dict[str, ConnectionInfo] = {}
        self.user_connections: Dict[str, str] = {}  # user_id -> connection_id
        
        # Room management
        self.rooms: Dict[str, RoomInfo] = {}
        self.room_participants: Dict[str, Set[str]] = {}  # room_id -> connection_ids
        
        # Redis pub/sub for horizontal scaling
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub = None
        self.redis_listener_task = None
        
        # Performance tracking
        self.message_count = 0
        self.connection_count = 0
        self.room_count = 0
        
        # Initialize Redis
        self._initialize_redis()
        
        logger.info("RealTimeManager initialized")
    
    def _initialize_redis(self):
        """Initialize Redis client for pub/sub broadcasting."""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available - real-time features will be limited to single server")
            return
        
        try:
            self.redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            
            # Start Redis listener
            asyncio.create_task(self._start_redis_listener())
            
            logger.info("Redis pub/sub initialized for real-time broadcasting")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
            self.redis_client = None
    
    async def _start_redis_listener(self):
        """Start Redis pub/sub listener for cross-server message broadcasting."""
        if not self.redis_client:
            return
        
        try:
            self.pubsub = self.redis_client.pubsub()
            await self.pubsub.subscribe("realtime:broadcast")
            
            logger.info("Redis pub/sub listener started")
            
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        await self._handle_redis_message(data)
                    except Exception as e:
                        logger.error(f"Error processing Redis message: {e}")
                        
        except Exception as e:
            logger.error(f"Redis listener error: {e}")
    
    async def handle_connection(self, websocket: WebSocket, user_id: str, connection_metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Handle a new WebSocket connection.
        
        Args:
            websocket: WebSocket instance
            user_id: Unique user identifier
            connection_metadata: Optional metadata for the connection
            
        Returns:
            Connection ID for the established connection
        """
        connection_id = str(uuid.uuid4())
        
        try:
            # Accept WebSocket connection
            await websocket.accept()
            
            # Create connection info
            connection_info = ConnectionInfo(
                websocket=websocket,
                user_id=user_id,
                connection_id=connection_id,
                state=ConnectionState.CONNECTED,
                metadata=connection_metadata or {}
            )
            
            # Store connection
            self.connections[connection_id] = connection_info
            self.user_connections[user_id] = connection_id
            self.connection_count += 1
            
            # Send welcome message
            await self._send_to_connection(connection_id, {
                "type": MessageType.SYSTEM_MESSAGE,
                "message": "Connected to GremlinsAI real-time collaboration",
                "connection_id": connection_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Start heartbeat monitoring
            asyncio.create_task(self._monitor_connection_heartbeat(connection_id))
            
            logger.info(f"WebSocket connection established: {connection_id} for user {user_id}")
            
            # Log performance
            log_performance(
                operation="websocket_connection_established",
                duration_ms=0,
                success=True,
                connection_id=connection_id,
                user_id=user_id
            )
            
            return connection_id
            
        except Exception as e:
            logger.error(f"Error establishing WebSocket connection: {e}")
            await self._handle_disconnect(connection_id)
            raise
    
    async def _handle_disconnect(self, connection_id: str):
        """Handle WebSocket disconnection."""
        if connection_id not in self.connections:
            return
        
        connection_info = self.connections[connection_id]
        user_id = connection_info.user_id
        
        try:
            # Remove from all rooms
            for room_id in connection_info.rooms.copy():
                await self._leave_room(connection_id, room_id)
            
            # Clean up connection
            del self.connections[connection_id]
            if user_id in self.user_connections and self.user_connections[user_id] == connection_id:
                del self.user_connections[user_id]
            
            self.connection_count -= 1
            
            logger.info(f"WebSocket connection disconnected: {connection_id} for user {user_id}")
            
            # Log performance
            log_performance(
                operation="websocket_connection_disconnected",
                duration_ms=0,
                success=True,
                connection_id=connection_id,
                user_id=user_id
            )
            
        except Exception as e:
            logger.error(f"Error handling disconnect for {connection_id}: {e}")
    
    async def join_room(self, connection_id: str, room_id: str, document_id: Optional[str] = None) -> bool:
        """
        Add a connection to a collaboration room.
        
        Args:
            connection_id: Connection identifier
            room_id: Room identifier
            document_id: Optional document identifier for the room
            
        Returns:
            True if successfully joined, False otherwise
        """
        if connection_id not in self.connections:
            return False
        
        connection_info = self.connections[connection_id]
        
        try:
            # Create room if it doesn't exist
            if room_id not in self.rooms:
                self.rooms[room_id] = RoomInfo(
                    room_id=room_id,
                    document_id=document_id
                )
                self.room_participants[room_id] = set()
                self.room_count += 1
            
            # Add connection to room
            self.room_participants[room_id].add(connection_id)
            connection_info.rooms.add(room_id)
            self.rooms[room_id].participants.add(connection_info.user_id)
            self.rooms[room_id].last_activity = datetime.utcnow()
            
            # Notify room participants
            await self.broadcast_to_room(room_id, {
                "type": MessageType.USER_PRESENCE,
                "action": "joined",
                "user_id": connection_info.user_id,
                "room_id": room_id,
                "timestamp": datetime.utcnow().isoformat()
            }, exclude_connection=connection_id)
            
            # Send room info to the joining user
            await self._send_to_connection(connection_id, {
                "type": MessageType.SYSTEM_MESSAGE,
                "message": f"Joined room {room_id}",
                "room_id": room_id,
                "participants": list(self.rooms[room_id].participants),
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Connection {connection_id} joined room {room_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error joining room {room_id}: {e}")
            return False
    
    async def _leave_room(self, connection_id: str, room_id: str):
        """Remove a connection from a room."""
        if connection_id not in self.connections or room_id not in self.rooms:
            return
        
        connection_info = self.connections[connection_id]
        
        try:
            # Remove from room
            if room_id in self.room_participants:
                self.room_participants[room_id].discard(connection_id)
            
            connection_info.rooms.discard(room_id)
            self.rooms[room_id].participants.discard(connection_info.user_id)
            
            # Notify remaining participants
            await self.broadcast_to_room(room_id, {
                "type": MessageType.USER_PRESENCE,
                "action": "left",
                "user_id": connection_info.user_id,
                "room_id": room_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Clean up empty room
            if not self.room_participants.get(room_id):
                del self.rooms[room_id]
                del self.room_participants[room_id]
                self.room_count -= 1
                logger.info(f"Room {room_id} cleaned up (empty)")
            
            logger.info(f"Connection {connection_id} left room {room_id}")
            
        except Exception as e:
            logger.error(f"Error leaving room {room_id}: {e}")

    async def broadcast_to_room(self, room_id: str, message: Dict[str, Any], exclude_connection: Optional[str] = None):
        """
        Broadcast a message to all participants in a room.

        Args:
            room_id: Room identifier
            message: Message to broadcast
            exclude_connection: Optional connection ID to exclude from broadcast
        """
        start_time = time.time()

        try:
            if room_id not in self.room_participants:
                return

            # Add message metadata
            message.update({
                "room_id": room_id,
                "broadcast_id": str(uuid.uuid4()),
                "server_timestamp": datetime.utcnow().isoformat()
            })

            # Broadcast to local connections
            participants = self.room_participants[room_id].copy()
            if exclude_connection:
                participants.discard(exclude_connection)

            broadcast_tasks = []
            for connection_id in participants:
                if connection_id in self.connections:
                    task = asyncio.create_task(self._send_to_connection(connection_id, message))
                    broadcast_tasks.append(task)

            # Wait for all local broadcasts
            if broadcast_tasks:
                await asyncio.gather(*broadcast_tasks, return_exceptions=True)

            # Broadcast via Redis for horizontal scaling
            if self.redis_client:
                redis_message = {
                    "type": "room_broadcast",
                    "room_id": room_id,
                    "message": message,
                    "exclude_connection": exclude_connection,
                    "origin_server": "current"  # Could be server ID in production
                }
                await self.redis_client.publish("realtime:broadcast", json.dumps(redis_message))

            # Log performance
            broadcast_time = (time.time() - start_time) * 1000
            log_performance(
                operation="room_broadcast",
                duration_ms=broadcast_time,
                success=True,
                room_id=room_id,
                participant_count=len(participants),
                message_type=message.get("type")
            )

            # Ensure sub-200ms latency requirement
            if broadcast_time > 200:
                logger.warning(f"Room broadcast exceeded 200ms latency: {broadcast_time:.2f}ms")

            self.message_count += 1

        except Exception as e:
            logger.error(f"Error broadcasting to room {room_id}: {e}")

    async def _send_to_connection(self, connection_id: str, message: Dict[str, Any]):
        """Send a message to a specific connection."""
        if connection_id not in self.connections:
            return

        connection_info = self.connections[connection_id]

        try:
            await connection_info.websocket.send_json(message)

        except WebSocketDisconnect:
            await self._handle_disconnect(connection_id)
        except Exception as e:
            logger.error(f"Error sending message to connection {connection_id}: {e}")
            await self._handle_disconnect(connection_id)

    async def _handle_redis_message(self, data: Dict[str, Any]):
        """Handle messages received from Redis pub/sub."""
        try:
            message_type = data.get("type")

            if message_type == "room_broadcast":
                room_id = data.get("room_id")
                message = data.get("message")
                exclude_connection = data.get("exclude_connection")

                # Only broadcast to local connections (avoid infinite loop)
                if room_id in self.room_participants:
                    participants = self.room_participants[room_id].copy()
                    if exclude_connection:
                        participants.discard(exclude_connection)

                    for connection_id in participants:
                        if connection_id in self.connections:
                            await self._send_to_connection(connection_id, message)

        except Exception as e:
            logger.error(f"Error handling Redis message: {e}")

    async def _monitor_connection_heartbeat(self, connection_id: str):
        """Monitor connection heartbeat and handle timeouts."""
        while connection_id in self.connections:
            try:
                connection_info = self.connections[connection_id]

                # Check if heartbeat is overdue
                time_since_heartbeat = datetime.utcnow() - connection_info.last_heartbeat
                if time_since_heartbeat > timedelta(seconds=60):  # 60 second timeout
                    logger.warning(f"Connection {connection_id} heartbeat timeout")
                    await self._handle_disconnect(connection_id)
                    break

                # Wait before next check
                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Error monitoring heartbeat for {connection_id}: {e}")
                break

    async def process_message(self, connection_id: str, message: Dict[str, Any]):
        """
        Process incoming WebSocket message.

        Args:
            connection_id: Connection identifier
            message: Incoming message data
        """
        if connection_id not in self.connections:
            return

        connection_info = self.connections[connection_id]
        message_type = message.get("type")

        try:
            # Update heartbeat
            connection_info.last_heartbeat = datetime.utcnow()

            # Process message based on type
            if message_type == MessageType.JOIN_ROOM:
                room_id = message.get("room_id")
                document_id = message.get("document_id")
                if room_id:
                    await self.join_room(connection_id, room_id, document_id)

            elif message_type == MessageType.LEAVE_ROOM:
                room_id = message.get("room_id")
                if room_id:
                    await self._leave_room(connection_id, room_id)

            elif message_type == MessageType.DOCUMENT_EDIT:
                room_id = message.get("room_id")
                if room_id and room_id in connection_info.rooms:
                    # Add sender information
                    message["sender_id"] = connection_info.user_id
                    message["sender_connection"] = connection_id

                    # Broadcast edit to room
                    await self.broadcast_to_room(room_id, message, exclude_connection=connection_id)

            elif message_type == MessageType.CURSOR_POSITION:
                room_id = message.get("room_id")
                if room_id and room_id in connection_info.rooms:
                    # Add sender information
                    message["sender_id"] = connection_info.user_id

                    # Broadcast cursor position to room
                    await self.broadcast_to_room(room_id, message, exclude_connection=connection_id)

            elif message_type == MessageType.HEARTBEAT:
                # Send heartbeat response
                await self._send_to_connection(connection_id, {
                    "type": MessageType.HEARTBEAT,
                    "timestamp": datetime.utcnow().isoformat()
                })

            else:
                logger.warning(f"Unknown message type: {message_type}")
                await self._send_to_connection(connection_id, {
                    "type": MessageType.ERROR,
                    "error": f"Unknown message type: {message_type}",
                    "timestamp": datetime.utcnow().isoformat()
                })

        except Exception as e:
            logger.error(f"Error processing message from {connection_id}: {e}")
            await self._send_to_connection(connection_id, {
                "type": MessageType.ERROR,
                "error": "Failed to process message",
                "timestamp": datetime.utcnow().isoformat()
            })

    def get_stats(self) -> Dict[str, Any]:
        """Get real-time manager statistics."""
        return {
            "connections": self.connection_count,
            "rooms": self.room_count,
            "messages_processed": self.message_count,
            "redis_available": self.redis_client is not None,
            "active_rooms": [
                {
                    "room_id": room_id,
                    "participants": len(room_info.participants),
                    "document_id": room_info.document_id,
                    "created_at": room_info.created_at.isoformat(),
                    "last_activity": room_info.last_activity.isoformat()
                }
                for room_id, room_info in self.rooms.items()
            ]
        }

    async def cleanup(self):
        """Cleanup resources."""
        try:
            # Close all connections
            for connection_id in list(self.connections.keys()):
                await self._handle_disconnect(connection_id)

            # Close Redis connections
            if self.pubsub:
                await self.pubsub.close()
            if self.redis_client:
                await self.redis_client.close()

            logger.info("RealTimeManager cleanup completed")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


# Global real-time manager instance
realtime_manager = RealTimeManager()
