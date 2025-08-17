# tests/integration/test_collaboration_service.py
"""
Integration tests for real-time collaboration service.

These tests verify that the CollaborationService can:
- Manage real-time WebSocket connections
- Handle concurrent document editing
- Broadcast messages with <200ms latency
- Maintain shared state consistency
- Integrate AI agents for collaborative assistance
"""

import pytest
import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any, List

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket
from fastapi import FastAPI

from app.services.collaboration_service import (
    CollaborationService, CollaborationMessageType, ParticipantType,
    CollaborationParticipant, DocumentOperation, CollaborationSession,
    collaboration_router
)
from app.core.agent import AgentResult, ReasoningStep


class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.messages_sent = []
        self.messages_received = []
        self.is_connected = True
    
    async def accept(self):
        """Mock accept method."""
        pass
    
    async def send_text(self, data: str):
        """Mock send_text method."""
        if self.is_connected:
            self.messages_sent.append(json.loads(data))
        else:
            raise Exception("WebSocket disconnected")
    
    async def receive_text(self):
        """Mock receive_text method."""
        if self.messages_received:
            return json.dumps(self.messages_received.pop(0))
        else:
            # Simulate waiting for message
            await asyncio.sleep(0.1)
            return json.dumps({"type": "heartbeat"})
    
    def add_received_message(self, message: Dict[str, Any]):
        """Add a message to the received queue."""
        self.messages_received.append(message)
    
    def disconnect(self):
        """Simulate disconnection."""
        self.is_connected = False


class TestCollaborationService:
    """Test suite for real-time collaboration capabilities."""
    
    @pytest.fixture
    def collaboration_service(self):
        """Create a collaboration service for testing."""
        return CollaborationService()
    
    @pytest.fixture
    def mock_agent_result(self):
        """Create a mock agent result for testing."""
        reasoning_steps = [
            ReasoningStep(
                step_number=1,
                thought="I need to analyze the document content and provide helpful suggestions",
                action="analyze_document",
                action_input="Analyzing collaborative document",
                observation="The document appears to be a business proposal with several sections that could be improved"
            ),
            ReasoningStep(
                step_number=2,
                thought="I can provide specific suggestions for improvement",
                action="final_answer",
                action_input="Based on my analysis...",
                observation="Final suggestions provided"
            )
        ]
        
        return AgentResult(
            final_answer="Based on my analysis of the collaborative document, I suggest adding more specific metrics to the business proposal. Consider including projected ROI figures and timeline milestones. You could also strengthen the executive summary with key value propositions.",
            reasoning_steps=reasoning_steps,
            total_steps=2,
            success=True
        )
    
    @pytest.mark.asyncio
    async def test_create_collaboration_session(self, collaboration_service):
        """Test creating a new collaboration session."""
        
        # Create session
        session = await collaboration_service.create_session(
            document_id="test_doc_123",
            initial_content="# Test Document\n\nThis is a test document for collaboration.",
            creator_id="user_1"
        )
        
        # Verify session creation
        assert session is not None
        assert session.document_id == "test_doc_123"
        assert session.document_content == "# Test Document\n\nThis is a test document for collaboration."
        assert len(session.participants) == 0
        assert len(session.operation_history) == 0
        assert session.session_id in collaboration_service.active_sessions
        
        # Verify metrics
        metrics = collaboration_service.get_service_metrics()
        assert metrics["total_sessions"] >= 1
        assert metrics["active_sessions"] >= 1
    
    @pytest.mark.asyncio
    async def test_join_and_leave_session(self, collaboration_service):
        """Test participants joining and leaving sessions."""
        
        # Create session
        session = await collaboration_service.create_session(
            document_id="test_doc_456",
            initial_content="Collaborative document content"
        )
        
        # Create mock WebSockets
        websocket1 = MockWebSocket("user_1")
        websocket2 = MockWebSocket("user_2")
        
        # Join session with first participant
        joined1 = await collaboration_service.join_session(
            session_id=session.session_id,
            participant_id="user_1",
            participant_type=ParticipantType.HUMAN_USER,
            display_name="Alice",
            websocket=websocket1
        )
        
        assert joined1 == True
        assert len(session.participants) == 1
        assert "user_1" in session.participants
        assert session.participants["user_1"].display_name == "Alice"
        
        # Verify document state message was sent
        assert len(websocket1.messages_sent) >= 1
        state_message = websocket1.messages_sent[0]
        assert state_message["type"] == CollaborationMessageType.DOCUMENT_STATE.value
        assert state_message["document_content"] == "Collaborative document content"
        
        # Join session with second participant
        joined2 = await collaboration_service.join_session(
            session_id=session.session_id,
            participant_id="user_2",
            participant_type=ParticipantType.HUMAN_USER,
            display_name="Bob",
            websocket=websocket2
        )
        
        assert joined2 == True
        assert len(session.participants) == 2
        
        # Verify user joined notification was sent to first participant
        user_joined_messages = [msg for msg in websocket1.messages_sent 
                               if msg["type"] == CollaborationMessageType.USER_JOINED.value]
        assert len(user_joined_messages) >= 1
        assert user_joined_messages[0]["participant"]["participant_id"] == "user_2"
        
        # Leave session
        await collaboration_service.leave_session(session.session_id, "user_1")
        assert len(session.participants) == 1
        assert "user_1" not in session.participants
        
        # Verify user left notification was sent to remaining participant
        user_left_messages = [msg for msg in websocket2.messages_sent 
                             if msg["type"] == CollaborationMessageType.USER_LEFT.value]
        assert len(user_left_messages) >= 1
        assert user_left_messages[0]["participant_id"] == "user_1"
    
    @pytest.mark.asyncio
    async def test_document_update_operations(self, collaboration_service):
        """Test real-time document update operations."""
        
        # Create session and join participants
        session = await collaboration_service.create_session(
            document_id="test_doc_789",
            initial_content="Hello world"
        )
        
        websocket1 = MockWebSocket("user_1")
        websocket2 = MockWebSocket("user_2")
        
        await collaboration_service.join_session(
            session.session_id, "user_1", ParticipantType.HUMAN_USER, "Alice", websocket1
        )
        await collaboration_service.join_session(
            session.session_id, "user_2", ParticipantType.HUMAN_USER, "Bob", websocket2
        )
        
        # Clear initial messages
        websocket1.messages_sent.clear()
        websocket2.messages_sent.clear()
        
        # Test insert operation
        insert_message = {
            "type": CollaborationMessageType.DOCUMENT_UPDATE.value,
            "operation": {
                "type": "insert",
                "position": 5,
                "content": " beautiful"
            }
        }
        
        start_time = time.time()
        await collaboration_service.handle_message(session.session_id, "user_1", insert_message)
        latency = (time.time() - start_time) * 1000
        
        # Verify latency is under 200ms
        assert latency < 200, f"Latency {latency:.2f}ms exceeds 200ms threshold"
        
        # Verify document was updated
        assert session.document_content == "Hello beautiful world"
        assert len(session.operation_history) == 1
        
        # Verify update was broadcast to other participant
        update_messages = [msg for msg in websocket2.messages_sent 
                          if msg["type"] == CollaborationMessageType.DOCUMENT_UPDATE.value]
        assert len(update_messages) == 1
        assert update_messages[0]["document_content"] == "Hello beautiful world"
        assert update_messages[0]["operation"]["type"] == "insert"
        assert update_messages[0]["operation"]["author_id"] == "user_1"
        
        # Test delete operation
        delete_message = {
            "type": CollaborationMessageType.DOCUMENT_UPDATE.value,
            "operation": {
                "type": "delete",
                "position": 6,
                "length": 9  # "beautiful"
            }
        }
        
        await collaboration_service.handle_message(session.session_id, "user_2", delete_message)
        
        # Verify document was updated
        assert session.document_content == "Hello  world"
        assert len(session.operation_history) == 2
        
        # Verify update was broadcast to first participant
        websocket1_updates = [msg for msg in websocket1.messages_sent 
                             if msg["type"] == CollaborationMessageType.DOCUMENT_UPDATE.value]
        assert len(websocket1_updates) == 1
        assert websocket1_updates[0]["operation"]["type"] == "delete"
        assert websocket1_updates[0]["operation"]["author_id"] == "user_2"
    
    @pytest.mark.asyncio
    async def test_cursor_and_selection_updates(self, collaboration_service):
        """Test cursor position and selection updates."""
        
        # Create session and join participants
        session = await collaboration_service.create_session(
            document_id="test_doc_cursor",
            initial_content="Test document for cursor tracking"
        )
        
        websocket1 = MockWebSocket("user_1")
        websocket2 = MockWebSocket("user_2")
        
        await collaboration_service.join_session(
            session.session_id, "user_1", ParticipantType.HUMAN_USER, "Alice", websocket1
        )
        await collaboration_service.join_session(
            session.session_id, "user_2", ParticipantType.HUMAN_USER, "Bob", websocket2
        )
        
        # Clear initial messages
        websocket2.messages_sent.clear()
        
        # Test cursor update
        cursor_message = {
            "type": CollaborationMessageType.CURSOR_UPDATE.value,
            "cursor": {
                "line": 0,
                "column": 10,
                "position": 10
            }
        }
        
        await collaboration_service.handle_message(session.session_id, "user_1", cursor_message)
        
        # Verify cursor was updated
        participant = session.participants["user_1"]
        assert participant.cursor_position["line"] == 0
        assert participant.cursor_position["column"] == 10
        
        # Verify cursor update was broadcast
        cursor_updates = [msg for msg in websocket2.messages_sent 
                         if msg["type"] == CollaborationMessageType.CURSOR_UPDATE.value]
        assert len(cursor_updates) == 1
        assert cursor_updates[0]["participant_id"] == "user_1"
        assert cursor_updates[0]["cursor"]["position"] == 10
        
        # Test selection update
        selection_message = {
            "type": CollaborationMessageType.SELECTION_UPDATE.value,
            "selection": {
                "start": 5,
                "end": 13,
                "text": "document"
            }
        }
        
        await collaboration_service.handle_message(session.session_id, "user_1", selection_message)
        
        # Verify selection was updated
        assert participant.selection["start"] == 5
        assert participant.selection["end"] == 13
        
        # Verify selection update was broadcast
        selection_updates = [msg for msg in websocket2.messages_sent 
                           if msg["type"] == CollaborationMessageType.SELECTION_UPDATE.value]
        assert len(selection_updates) == 1
        assert selection_updates[0]["selection"]["text"] == "document"
    
    @pytest.mark.asyncio
    async def test_ai_agent_integration(self, collaboration_service, mock_agent_result):
        """Test AI agent integration for collaborative assistance."""
        
        with patch.object(collaboration_service.ai_agent, 'reason_and_act', return_value=mock_agent_result):
            # Create session and join participant
            session = await collaboration_service.create_session(
                document_id="test_doc_ai",
                initial_content="# Business Proposal\n\nWe need to improve this document."
            )
            
            websocket1 = MockWebSocket("user_1")
            await collaboration_service.join_session(
                session.session_id, "user_1", ParticipantType.HUMAN_USER, "Alice", websocket1
            )
            
            # Clear initial messages
            websocket1.messages_sent.clear()
            
            # Send agent request
            agent_request = {
                "type": CollaborationMessageType.AGENT_REQUEST.value,
                "request_id": "req_123",
                "request": {
                    "query": "How can we improve this business proposal?",
                    "context": {
                        "section": "executive_summary"
                    }
                }
            }
            
            await collaboration_service.handle_message(session.session_id, "user_1", agent_request)
            
            # Verify agent thinking notification was sent
            thinking_messages = [msg for msg in websocket1.messages_sent 
                               if msg["type"] == CollaborationMessageType.AGENT_THINKING.value]
            assert len(thinking_messages) == 1
            assert thinking_messages[0]["request_id"] == "req_123"
            
            # Verify agent response was sent
            response_messages = [msg for msg in websocket1.messages_sent 
                               if msg["type"] == CollaborationMessageType.AGENT_RESPONSE.value]
            assert len(response_messages) == 1
            
            response = response_messages[0]
            assert response["request_id"] == "req_123"
            assert "business proposal" in response["response"]["answer"]
            assert response["response"]["success"] == True
            assert len(response["response"]["suggestions"]) > 0
            
            # Verify agent was called with collaborative context
            collaboration_service.ai_agent.reason_and_act.assert_called_once()
            call_args = collaboration_service.ai_agent.reason_and_act.call_args[0][0]
            assert "collaborative document editing session" in call_args
            assert session.document_content in call_args
            assert "Alice" in call_args
    
    @pytest.mark.asyncio
    async def test_concurrent_operations_performance(self, collaboration_service):
        """Test performance with concurrent operations."""
        
        # Create session
        session = await collaboration_service.create_session(
            document_id="test_doc_perf",
            initial_content="Performance test document"
        )
        
        # Create multiple participants
        participants = []
        websockets = []
        
        for i in range(5):
            websocket = MockWebSocket(f"user_{i}")
            websockets.append(websocket)
            
            await collaboration_service.join_session(
                session.session_id, f"user_{i}", ParticipantType.HUMAN_USER, 
                f"User{i}", websocket
            )
            participants.append(f"user_{i}")
        
        # Clear initial messages
        for ws in websockets:
            ws.messages_sent.clear()
        
        # Send concurrent document updates
        tasks = []
        start_time = time.time()
        
        for i, participant_id in enumerate(participants):
            update_message = {
                "type": CollaborationMessageType.DOCUMENT_UPDATE.value,
                "operation": {
                    "type": "insert",
                    "position": len(session.document_content),
                    "content": f" Update{i}"
                }
            }
            
            task = collaboration_service.handle_message(session.session_id, participant_id, update_message)
            tasks.append(task)
        
        # Wait for all operations to complete
        await asyncio.gather(*tasks)
        total_time = (time.time() - start_time) * 1000
        
        # Verify all operations were processed
        assert len(session.operation_history) == 5
        
        # Verify performance (should handle 5 concurrent operations quickly)
        assert total_time < 1000, f"Concurrent operations took {total_time:.2f}ms, expected <1000ms"
        
        # Verify all participants received all updates
        for i, websocket in enumerate(websockets):
            update_messages = [msg for msg in websocket.messages_sent 
                             if msg["type"] == CollaborationMessageType.DOCUMENT_UPDATE.value]
            # Each participant should receive updates from the other 4 participants
            assert len(update_messages) == 4
    
    def test_session_info_and_metrics(self, collaboration_service):
        """Test session information and service metrics."""
        
        # Get initial metrics
        initial_metrics = collaboration_service.get_service_metrics()
        assert "total_sessions" in initial_metrics
        assert "active_sessions" in initial_metrics
        assert "average_latency" in initial_metrics
        
        # Test session info for non-existent session
        info = collaboration_service.get_session_info("non_existent_session")
        assert info is None


if __name__ == "__main__":
    pytest.main([__file__])
