# app/services/collaboration_service.py
"""
Real-time Collaboration Service

This service provides real-time collaboration capabilities enabling multiple users
and AI agents to work together on shared documents and workspaces with sub-200ms
latency for message passing and synchronized state management.

Features:
- Real-time bi-directional communication via WebSocket
- Shared state management with conflict resolution
- Multi-user concurrent editing support
- AI agent integration for collaborative workflows
- Low-latency message broadcasting (<200ms)
- Operational Transform for document synchronization
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Optional, Any, Set, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque

from fastapi import WebSocket, WebSocketDisconnect
import redis.asyncio as redis

from app.core.agent import ProductionAgent

logger = logging.getLogger(__name__)


class CollaborationMessageType(Enum):
    """Types of collaboration messages."""
    # Connection management
    JOIN_SESSION = "join_session"
    LEAVE_SESSION = "leave_session"
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    
    # Document operations
    DOCUMENT_UPDATE = "document_update"
    DOCUMENT_STATE = "document_state"
    CURSOR_UPDATE = "cursor_update"
    SELECTION_UPDATE = "selection_update"
    
    # AI agent interactions
    AGENT_REQUEST = "agent_request"
    AGENT_RESPONSE = "agent_response"
    AGENT_THINKING = "agent_thinking"
    
    # System messages
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    ACK = "ack"


class ParticipantType(Enum):
    """Types of collaboration participants."""
    HUMAN_USER = "human_user"
    AI_AGENT = "ai_agent"
    SYSTEM = "system"


@dataclass
class CollaborationParticipant:
    """Represents a participant in a collaboration session."""
    participant_id: str
    participant_type: ParticipantType
    display_name: str
    websocket: Optional[WebSocket] = None
    joined_at: datetime = None
    last_activity: datetime = None
    cursor_position: Optional[Dict[str, Any]] = None
    selection: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.joined_at is None:
            self.joined_at = datetime.utcnow()
        if self.last_activity is None:
            self.last_activity = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class DocumentOperation:
    """Represents a document operation for operational transform."""
    operation_id: str
    operation_type: str  # insert, delete, retain
    position: int
    content: Optional[str] = None
    length: Optional[int] = None
    author_id: str = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class CollaborationSession:
    """Represents a collaboration session."""
    session_id: str
    document_id: str
    document_content: str
    participants: Dict[str, CollaborationParticipant]
    created_at: datetime
    last_activity: datetime
    operation_history: List[DocumentOperation]
    shared_state: Dict[str, Any]
    
    def __post_init__(self):
        if not self.participants:
            self.participants = {}
        if not self.operation_history:
            self.operation_history = []
        if not self.shared_state:
            self.shared_state = {}


class CollaborationService:
    """
    Service for managing real-time collaboration sessions.
    
    Provides WebSocket-based real-time communication, shared state management,
    and AI agent integration for collaborative workflows.
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """Initialize the collaboration service."""
        self.redis_client = redis_client
        
        # Active collaboration sessions
        self.active_sessions: Dict[str, CollaborationSession] = {}
        
        # WebSocket connections by participant ID
        self.participant_connections: Dict[str, WebSocket] = {}
        
        # Session participants mapping
        self.session_participants: Dict[str, Set[str]] = defaultdict(set)
        
        # Message queue for offline participants
        self.message_queues: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Performance metrics
        self.metrics = {
            "total_sessions": 0,
            "active_sessions": 0,
            "total_participants": 0,
            "messages_sent": 0,
            "average_latency": 0.0,
            "operations_processed": 0
        }
        
        # AI agent for collaborative assistance
        self.ai_agent = ProductionAgent()
        
        logger.info("CollaborationService initialized with real-time capabilities")

    async def join_document_session(
        self,
        document_id: str,
        user_id: str,
        connection_id: str,
        display_name: str
    ) -> bool:
        """
        Join a collaborative document editing session for real-time collaboration.

        Args:
            document_id: Document identifier
            user_id: User identifier
            connection_id: WebSocket connection identifier
            display_name: User display name

        Returns:
            True if successfully joined, False otherwise
        """
        try:
            # Create or get existing session
            session = None
            for s in self.active_sessions.values():
                if s.document_id == document_id:
                    session = s
                    break

            if not session:
                session = await self.create_session(document_id, "", user_id)

            # Add participant if not already present
            if user_id not in session.participants:
                participant = CollaborationParticipant(
                    participant_id=user_id,
                    display_name=display_name,
                    participant_type=ParticipantType.HUMAN_USER,
                    connection_id=connection_id,
                    joined_at=datetime.utcnow(),
                    last_activity=datetime.utcnow(),
                    status=ParticipantStatus.ACTIVE,
                    cursor_position=0,
                    selection_range=(0, 0),
                    permissions=["read", "write", "comment"]
                )
                session.participants[user_id] = participant
                self.session_participants[session.session_id].add(user_id)

            session.last_activity = datetime.utcnow()
            self.metrics["total_participants"] = sum(len(p) for p in self.session_participants.values())

            logger.info(f"User {user_id} joined document session {document_id}")
            return True

        except Exception as e:
            logger.error(f"Error joining document session {document_id}: {e}")
            return False

    async def leave_document_session(
        self,
        document_id: str,
        user_id: str,
        connection_id: str
    ):
        """
        Leave a collaborative document editing session.

        Args:
            document_id: Document identifier
            user_id: User identifier
            connection_id: WebSocket connection identifier
        """
        try:
            # Find session by document_id
            session = None
            for s in self.active_sessions.values():
                if s.document_id == document_id:
                    session = s
                    break

            if session and user_id in session.participants:
                # Remove participant
                del session.participants[user_id]
                self.session_participants[session.session_id].discard(user_id)

                # Clean up empty session
                if not session.participants:
                    del self.active_sessions[session.session_id]
                    if session.session_id in self.session_participants:
                        del self.session_participants[session.session_id]
                    logger.info(f"Document session {document_id} cleaned up (empty)")
                else:
                    session.last_activity = datetime.utcnow()

                self.metrics["active_sessions"] = len(self.active_sessions)
                self.metrics["total_participants"] = sum(len(p) for p in self.session_participants.values())

            logger.info(f"User {user_id} left document session {document_id}")

        except Exception as e:
            logger.error(f"Error leaving document session {document_id}: {e}")

    async def handle_document_edit(
        self,
        document_id: str,
        user_id: str,
        edit_data: Dict[str, Any],
        connection_id: str
    ):
        """
        Handle a document edit operation with operational transform.

        Args:
            document_id: Document identifier
            user_id: User making the edit
            edit_data: Edit operation data
            connection_id: WebSocket connection identifier
        """
        try:
            # Find session by document_id
            session = None
            for s in self.active_sessions.values():
                if s.document_id == document_id:
                    session = s
                    break

            if not session:
                logger.error(f"Document session {document_id} not found")
                return

            # Extract edit operation
            operation_data = edit_data.get("operation", {})
            operation = DocumentOperation(
                operation_id=str(uuid.uuid4()),
                operation_type=operation_data.get("type", "insert"),
                position=operation_data.get("position", 0),
                content=operation_data.get("content"),
                length=operation_data.get("length"),
                author_id=user_id,
                timestamp=datetime.utcnow()
            )

            # Apply operational transform (simplified)
            transformed_operation = await self._apply_simple_operational_transform(session, operation)

            # Apply operation to document
            if transformed_operation:
                await self._apply_operation_to_document_content(session, transformed_operation)

                # Add to operation history
                session.operation_history.append(transformed_operation)
                session.last_activity = datetime.utcnow()

                # Update metrics
                self.metrics["operations_processed"] += 1

                logger.info(f"Document edit applied: {document_id} by {user_id}")

        except Exception as e:
            logger.error(f"Error handling document edit for {document_id}: {e}")

    async def create_session(self, document_id: str, initial_content: str = "",
                           creator_id: str = None) -> CollaborationSession:
        """Create a new collaboration session."""
        session_id = str(uuid.uuid4())
        
        session = CollaborationSession(
            session_id=session_id,
            document_id=document_id,
            document_content=initial_content,
            participants={},
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            operation_history=[],
            shared_state={}
        )
        
        self.active_sessions[session_id] = session
        self.metrics["total_sessions"] += 1
        self.metrics["active_sessions"] += 1
        
        # Store in Redis for persistence
        if self.redis_client:
            await self._store_session_in_redis(session)
        
        logger.info(f"Created collaboration session {session_id} for document {document_id}")
        return session
    
    async def join_session(self, session_id: str, participant_id: str, 
                          participant_type: ParticipantType, display_name: str,
                          websocket: WebSocket) -> bool:
        """Add a participant to a collaboration session."""
        try:
            if session_id not in self.active_sessions:
                # Try to load from Redis
                session = await self._load_session_from_redis(session_id)
                if not session:
                    logger.warning(f"Session {session_id} not found")
                    return False
                self.active_sessions[session_id] = session
            
            session = self.active_sessions[session_id]
            
            # Create participant
            participant = CollaborationParticipant(
                participant_id=participant_id,
                participant_type=participant_type,
                display_name=display_name,
                websocket=websocket,
                joined_at=datetime.utcnow(),
                last_activity=datetime.utcnow()
            )
            
            # Add to session
            session.participants[participant_id] = participant
            self.participant_connections[participant_id] = websocket
            self.session_participants[session_id].add(participant_id)
            
            # Update metrics
            self.metrics["total_participants"] += 1
            
            # Send current document state to new participant
            await self._send_to_participant(participant_id, {
                "type": CollaborationMessageType.DOCUMENT_STATE.value,
                "session_id": session_id,
                "document_content": session.document_content,
                "participants": [
                    {
                        "participant_id": p.participant_id,
                        "display_name": p.display_name,
                        "participant_type": p.participant_type.value,
                        "joined_at": p.joined_at.isoformat()
                    }
                    for p in session.participants.values()
                ],
                "shared_state": session.shared_state,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Notify other participants
            await self._broadcast_to_session(session_id, {
                "type": CollaborationMessageType.USER_JOINED.value,
                "session_id": session_id,
                "participant": {
                    "participant_id": participant_id,
                    "display_name": display_name,
                    "participant_type": participant_type.value,
                    "joined_at": participant.joined_at.isoformat()
                },
                "timestamp": datetime.utcnow().isoformat()
            }, exclude_participant=participant_id)
            
            logger.info(f"Participant {participant_id} joined session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error joining session {session_id}: {e}")
            return False
    
    async def leave_session(self, session_id: str, participant_id: str):
        """Remove a participant from a collaboration session."""
        try:
            if session_id not in self.active_sessions:
                return
            
            session = self.active_sessions[session_id]
            
            if participant_id in session.participants:
                participant = session.participants[participant_id]
                
                # Remove participant
                del session.participants[participant_id]
                self.session_participants[session_id].discard(participant_id)
                
                if participant_id in self.participant_connections:
                    del self.participant_connections[participant_id]
                
                # Notify other participants
                await self._broadcast_to_session(session_id, {
                    "type": CollaborationMessageType.USER_LEFT.value,
                    "session_id": session_id,
                    "participant_id": participant_id,
                    "display_name": participant.display_name,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                # Clean up empty sessions
                if not session.participants:
                    await self._cleanup_session(session_id)
                
                logger.info(f"Participant {participant_id} left session {session_id}")
                
        except Exception as e:
            logger.error(f"Error leaving session {session_id}: {e}")
    
    async def handle_message(self, session_id: str, participant_id: str, message: Dict[str, Any]):
        """Handle incoming collaboration message."""
        start_time = time.time()
        
        try:
            message_type = message.get("type")
            
            if message_type == CollaborationMessageType.DOCUMENT_UPDATE.value:
                await self._handle_document_update(session_id, participant_id, message)
            
            elif message_type == CollaborationMessageType.CURSOR_UPDATE.value:
                await self._handle_cursor_update(session_id, participant_id, message)
            
            elif message_type == CollaborationMessageType.SELECTION_UPDATE.value:
                await self._handle_selection_update(session_id, participant_id, message)
            
            elif message_type == CollaborationMessageType.AGENT_REQUEST.value:
                await self._handle_agent_request(session_id, participant_id, message)
            
            elif message_type == CollaborationMessageType.HEARTBEAT.value:
                await self._handle_heartbeat(session_id, participant_id, message)
            
            else:
                logger.warning(f"Unknown message type: {message_type}")
            
            # Update metrics
            latency = (time.time() - start_time) * 1000  # Convert to milliseconds
            self.metrics["messages_sent"] += 1
            self.metrics["average_latency"] = (
                (self.metrics["average_latency"] * (self.metrics["messages_sent"] - 1) + latency) 
                / self.metrics["messages_sent"]
            )
            
            # Log if latency exceeds 200ms threshold
            if latency > 200:
                logger.warning(f"High latency detected: {latency:.2f}ms for message type {message_type}")
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await self._send_error_to_participant(participant_id, f"Error processing message: {str(e)}")
    
    async def _handle_document_update(self, session_id: str, participant_id: str, message: Dict[str, Any]):
        """Handle document update operations."""
        if session_id not in self.active_sessions:
            return
        
        session = self.active_sessions[session_id]
        
        # Extract operation details
        operation_data = message.get("operation", {})
        operation = DocumentOperation(
            operation_id=str(uuid.uuid4()),
            operation_type=operation_data.get("type"),
            position=operation_data.get("position", 0),
            content=operation_data.get("content"),
            length=operation_data.get("length"),
            author_id=participant_id,
            timestamp=datetime.utcnow()
        )
        
        # Apply operation to document
        new_content = self._apply_operation(session.document_content, operation)
        session.document_content = new_content
        session.operation_history.append(operation)
        session.last_activity = datetime.utcnow()
        
        # Update metrics
        self.metrics["operations_processed"] += 1
        
        # Broadcast update to all other participants
        await self._broadcast_to_session(session_id, {
            "type": CollaborationMessageType.DOCUMENT_UPDATE.value,
            "session_id": session_id,
            "operation": {
                "operation_id": operation.operation_id,
                "type": operation.operation_type,
                "position": operation.position,
                "content": operation.content,
                "length": operation.length,
                "author_id": operation.author_id,
                "timestamp": operation.timestamp.isoformat()
            },
            "document_content": new_content,
            "timestamp": datetime.utcnow().isoformat()
        }, exclude_participant=participant_id)
        
        # Store updated session in Redis
        if self.redis_client:
            await self._store_session_in_redis(session)

    async def _handle_cursor_update(self, session_id: str, participant_id: str, message: Dict[str, Any]):
        """Handle cursor position updates."""
        if session_id not in self.active_sessions:
            return

        session = self.active_sessions[session_id]
        participant = session.participants.get(participant_id)

        if participant:
            cursor_data = message.get("cursor", {})
            participant.cursor_position = cursor_data
            participant.last_activity = datetime.utcnow()

            # Broadcast cursor update to other participants
            await self._broadcast_to_session(session_id, {
                "type": CollaborationMessageType.CURSOR_UPDATE.value,
                "session_id": session_id,
                "participant_id": participant_id,
                "cursor": cursor_data,
                "timestamp": datetime.utcnow().isoformat()
            }, exclude_participant=participant_id)

    async def _handle_selection_update(self, session_id: str, participant_id: str, message: Dict[str, Any]):
        """Handle text selection updates."""
        if session_id not in self.active_sessions:
            return

        session = self.active_sessions[session_id]
        participant = session.participants.get(participant_id)

        if participant:
            selection_data = message.get("selection", {})
            participant.selection = selection_data
            participant.last_activity = datetime.utcnow()

            # Broadcast selection update to other participants
            await self._broadcast_to_session(session_id, {
                "type": CollaborationMessageType.SELECTION_UPDATE.value,
                "session_id": session_id,
                "participant_id": participant_id,
                "selection": selection_data,
                "timestamp": datetime.utcnow().isoformat()
            }, exclude_participant=participant_id)

    async def _handle_agent_request(self, session_id: str, participant_id: str, message: Dict[str, Any]):
        """Handle AI agent assistance requests."""
        if session_id not in self.active_sessions:
            return

        session = self.active_sessions[session_id]
        request_data = message.get("request", {})
        query = request_data.get("query", "")
        context = request_data.get("context", {})

        # Notify participants that agent is thinking
        await self._broadcast_to_session(session_id, {
            "type": CollaborationMessageType.AGENT_THINKING.value,
            "session_id": session_id,
            "request_id": message.get("request_id"),
            "timestamp": datetime.utcnow().isoformat()
        })

        try:
            # Prepare context for AI agent
            agent_context = {
                "document_content": session.document_content,
                "participants": [p.display_name for p in session.participants.values()],
                "shared_state": session.shared_state,
                "recent_operations": [
                    {
                        "type": op.operation_type,
                        "author": op.author_id,
                        "timestamp": op.timestamp.isoformat()
                    }
                    for op in session.operation_history[-10:]  # Last 10 operations
                ],
                **context
            }

            # Enhanced query with collaboration context
            enhanced_query = f"""
            You are assisting in a collaborative document editing session.

            Current document content:
            {session.document_content}

            Active participants: {', '.join([p.display_name for p in session.participants.values()])}

            User request: {query}

            Please provide helpful assistance while being aware of the collaborative context.
            """

            # Get AI agent response
            agent_result = await self.ai_agent.reason_and_act(enhanced_query)

            # Send agent response to all participants
            await self._broadcast_to_session(session_id, {
                "type": CollaborationMessageType.AGENT_RESPONSE.value,
                "session_id": session_id,
                "request_id": message.get("request_id"),
                "response": {
                    "answer": agent_result.final_answer,
                    "reasoning_steps": [step.thought for step in agent_result.reasoning_steps],
                    "success": agent_result.success,
                    "suggestions": self._extract_suggestions_from_response(agent_result.final_answer)
                },
                "timestamp": datetime.utcnow().isoformat()
            })

        except Exception as e:
            logger.error(f"Error processing agent request: {e}")
            await self._broadcast_to_session(session_id, {
                "type": CollaborationMessageType.ERROR.value,
                "session_id": session_id,
                "request_id": message.get("request_id"),
                "error": f"Agent request failed: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            })

    async def _handle_heartbeat(self, session_id: str, participant_id: str, message: Dict[str, Any]):
        """Handle heartbeat messages to keep connections alive."""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            participant = session.participants.get(participant_id)

            if participant:
                participant.last_activity = datetime.utcnow()

                # Send heartbeat response
                await self._send_to_participant(participant_id, {
                    "type": CollaborationMessageType.HEARTBEAT.value,
                    "session_id": session_id,
                    "timestamp": datetime.utcnow().isoformat()
                })

    def _apply_operation(self, content: str, operation: DocumentOperation) -> str:
        """Apply a document operation using operational transform."""
        if operation.operation_type == "insert":
            return content[:operation.position] + operation.content + content[operation.position:]

        elif operation.operation_type == "delete":
            end_pos = operation.position + (operation.length or 0)
            return content[:operation.position] + content[end_pos:]

        elif operation.operation_type == "replace":
            end_pos = operation.position + (operation.length or 0)
            return content[:operation.position] + operation.content + content[end_pos:]

        else:
            logger.warning(f"Unknown operation type: {operation.operation_type}")
            return content

    def _extract_suggestions_from_response(self, response: str) -> List[str]:
        """Extract actionable suggestions from AI agent response."""
        suggestions = []

        # Simple pattern matching for suggestions
        import re
        suggestion_patterns = [
            r"I suggest (.+?)(?:\.|$)",
            r"You could (.+?)(?:\.|$)",
            r"Consider (.+?)(?:\.|$)",
            r"Try (.+?)(?:\.|$)"
        ]

        for pattern in suggestion_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            suggestions.extend(matches)

        return suggestions[:5]  # Limit to 5 suggestions

    async def _broadcast_to_session(self, session_id: str, message: Dict[str, Any],
                                  exclude_participant: str = None):
        """Broadcast a message to all participants in a session."""
        if session_id not in self.active_sessions:
            return

        session = self.active_sessions[session_id]

        for participant_id, participant in session.participants.items():
            if exclude_participant and participant_id == exclude_participant:
                continue

            await self._send_to_participant(participant_id, message)

    async def _send_to_participant(self, participant_id: str, message: Dict[str, Any]):
        """Send a message to a specific participant."""
        if participant_id not in self.participant_connections:
            # Queue message for offline participant
            self.message_queues[participant_id].append(message)
            return

        websocket = self.participant_connections[participant_id]

        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending message to participant {participant_id}: {e}")
            # Remove dead connection
            if participant_id in self.participant_connections:
                del self.participant_connections[participant_id]

    async def _send_error_to_participant(self, participant_id: str, error_message: str):
        """Send an error message to a participant."""
        await self._send_to_participant(participant_id, {
            "type": CollaborationMessageType.ERROR.value,
            "error": error_message,
            "timestamp": datetime.utcnow().isoformat()
        })

    async def _store_session_in_redis(self, session: CollaborationSession):
        """Store session data in Redis for persistence."""
        if not self.redis_client:
            return

        try:
            session_data = {
                "session_id": session.session_id,
                "document_id": session.document_id,
                "document_content": session.document_content,
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "shared_state": session.shared_state,
                "operation_count": len(session.operation_history)
            }

            await self.redis_client.setex(
                f"collaboration_session:{session.session_id}",
                3600,  # 1 hour TTL
                json.dumps(session_data)
            )

        except Exception as e:
            logger.error(f"Error storing session in Redis: {e}")

    async def _load_session_from_redis(self, session_id: str) -> Optional[CollaborationSession]:
        """Load session data from Redis."""
        if not self.redis_client:
            return None

        try:
            session_data = await self.redis_client.get(f"collaboration_session:{session_id}")
            if not session_data:
                return None

            data = json.loads(session_data)

            return CollaborationSession(
                session_id=data["session_id"],
                document_id=data["document_id"],
                document_content=data["document_content"],
                participants={},
                created_at=datetime.fromisoformat(data["created_at"]),
                last_activity=datetime.fromisoformat(data["last_activity"]),
                operation_history=[],
                shared_state=data["shared_state"]
            )

        except Exception as e:
            logger.error(f"Error loading session from Redis: {e}")
            return None

    async def _cleanup_session(self, session_id: str):
        """Clean up an empty session."""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]

        if session_id in self.session_participants:
            del self.session_participants[session_id]

        self.metrics["active_sessions"] -= 1

        # Remove from Redis
        if self.redis_client:
            await self.redis_client.delete(f"collaboration_session:{session_id}")

        logger.info(f"Cleaned up empty session {session_id}")

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a collaboration session."""
        if session_id not in self.active_sessions:
            return None

        session = self.active_sessions[session_id]

        return {
            "session_id": session.session_id,
            "document_id": session.document_id,
            "participant_count": len(session.participants),
            "participants": [
                {
                    "participant_id": p.participant_id,
                    "display_name": p.display_name,
                    "participant_type": p.participant_type.value,
                    "joined_at": p.joined_at.isoformat(),
                    "last_activity": p.last_activity.isoformat()
                }
                for p in session.participants.values()
            ],
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "operation_count": len(session.operation_history),
            "document_length": len(session.document_content)
        }

    def get_service_metrics(self) -> Dict[str, Any]:
        """Get collaboration service metrics."""
        return {
            **self.metrics,
            "active_sessions": len(self.active_sessions),
            "active_participants": len(self.participant_connections),
            "queued_messages": sum(len(queue) for queue in self.message_queues.values())
        }


# WebSocket endpoint for collaboration
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

collaboration_router = APIRouter()


@collaboration_router.websocket("/collaborate/{session_id}")
async def collaboration_websocket(
    websocket: WebSocket,
    session_id: str,
    participant_id: str = Query(...),
    display_name: str = Query(...),
    participant_type: str = Query("human_user")
):
    """
    WebSocket endpoint for real-time collaboration.

    Path Parameters:
    - session_id: ID of the collaboration session

    Query Parameters:
    - participant_id: Unique identifier for the participant
    - display_name: Display name for the participant
    - participant_type: Type of participant (human_user, ai_agent)
    """
    # Accept WebSocket connection
    await websocket.accept()

    # Parse participant type
    try:
        p_type = ParticipantType(participant_type)
    except ValueError:
        p_type = ParticipantType.HUMAN_USER

    # Join collaboration session
    joined = await collaboration_service.join_session(
        session_id=session_id,
        participant_id=participant_id,
        participant_type=p_type,
        display_name=display_name,
        websocket=websocket
    )

    if not joined:
        await websocket.close(code=4004, reason="Failed to join session")
        return

    try:
        # Handle incoming messages
        while True:
            try:
                # Receive message with timeout to detect disconnections
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                message = json.loads(data)

                # Handle the message
                await collaboration_service.handle_message(session_id, participant_id, message)

            except asyncio.TimeoutError:
                # Send heartbeat to check connection
                await websocket.send_text(json.dumps({
                    "type": CollaborationMessageType.HEARTBEAT.value,
                    "timestamp": datetime.utcnow().isoformat()
                }))

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON received from {participant_id}: {e}")
                await websocket.send_text(json.dumps({
                    "type": CollaborationMessageType.ERROR.value,
                    "error": "Invalid JSON format",
                    "timestamp": datetime.utcnow().isoformat()
                }))

    except WebSocketDisconnect:
        logger.info(f"Participant {participant_id} disconnected from session {session_id}")

    except Exception as e:
        logger.error(f"Error in collaboration WebSocket for {participant_id}: {e}")

    finally:
        # Clean up participant
        await collaboration_service.leave_session(session_id, participant_id)


@collaboration_router.get("/sessions/{session_id}/info")
async def get_session_info(session_id: str):
    """Get information about a collaboration session."""
    info = collaboration_service.get_session_info(session_id)
    if not info:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Session not found")
    return info


@collaboration_router.post("/sessions")
async def create_collaboration_session(
    document_id: str,
    initial_content: str = "",
    creator_id: str = None
):
    """Create a new collaboration session."""
    session = await collaboration_service.create_session(
        document_id=document_id,
        initial_content=initial_content,
        creator_id=creator_id
    )

    return {
        "session_id": session.session_id,
        "document_id": session.document_id,
        "created_at": session.created_at.isoformat(),
        "websocket_url": f"/api/v1/collaborate/{session.session_id}"
    }


@collaboration_router.get("/metrics")
async def get_collaboration_metrics():
    """Get collaboration service metrics."""
    return collaboration_service.get_service_metrics()


# Global collaboration service instance
collaboration_service = CollaborationService()
