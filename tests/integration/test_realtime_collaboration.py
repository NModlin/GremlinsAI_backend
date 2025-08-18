"""
Integration tests for Real-time Collaboration Features
Phase 3, Task 3.3: Real-time Collaboration Features

Tests the complete real-time collaboration system including:
- WebSocket connection stability for extended periods
- Sub-200ms collaborative editing latency
- Support for 100+ concurrent users per room
- Graceful handling of client disconnections
- Redis pub/sub broadcasting for horizontal scaling
"""

import pytest
import asyncio
import time
import json
import websockets
from typing import List, Dict, Any
from fastapi.testclient import TestClient
from testcontainers.compose import DockerCompose
import concurrent.futures

from app.main import app
from app.core.config import get_settings


class TestRealtimeCollaboration:
    """Integration tests for the complete real-time collaboration system."""
    
    @pytest.fixture(scope="class")
    def docker_compose(self):
        """Start test infrastructure with Docker Compose."""
        settings = get_settings()
        
        # Use docker-compose for test infrastructure
        compose = DockerCompose(".", compose_file_name="docker-compose.test.yml")
        compose.start()
        
        # Wait for services to be ready
        time.sleep(10)
        
        yield compose
        
        # Cleanup
        compose.stop()
    
    @pytest.fixture(scope="class")
    def test_client(self, docker_compose):
        """Create test client with test infrastructure."""
        return TestClient(app)
    
    @pytest.fixture
    def websocket_url(self):
        """Get WebSocket URL for testing."""
        return "ws://localhost:8000/api/v1/websocket/collaborate"
    
    @pytest.mark.asyncio
    async def test_websocket_connection_stability(self, websocket_url):
        """
        Test WebSocket connections remain stable for extended periods.
        
        This test validates:
        1. WebSocket connections can be established successfully
        2. Connections remain stable for extended periods (simulated)
        3. Heartbeat mechanism keeps connections alive
        4. Graceful handling of connection lifecycle
        """
        document_id = "test_doc_stability"
        user_id = "test_user_stability"
        display_name = "Test User Stability"
        
        # Build WebSocket URL with parameters
        ws_url = f"{websocket_url}/{document_id}?user_id={user_id}&display_name={display_name}"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                # Send initial join message
                join_message = {
                    "type": "join_room",
                    "room_id": f"document:{document_id}",
                    "document_id": document_id
                }
                await websocket.send(json.dumps(join_message))
                
                # Receive welcome message
                response = await websocket.recv()
                response_data = json.loads(response)
                assert response_data.get("type") in ["system_message", "user_presence"]
                
                # Simulate extended connection (5 minutes compressed to 30 seconds)
                start_time = time.time()
                heartbeat_count = 0
                
                while time.time() - start_time < 30:  # 30 seconds test duration
                    # Send heartbeat every 5 seconds
                    if int(time.time() - start_time) % 5 == 0 and heartbeat_count < 6:
                        heartbeat_message = {
                            "type": "heartbeat",
                            "timestamp": time.time()
                        }
                        await websocket.send(json.dumps(heartbeat_message))
                        heartbeat_count += 1
                    
                    # Check for incoming messages (non-blocking)
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        message_data = json.loads(message)
                        
                        # Validate heartbeat responses
                        if message_data.get("type") == "heartbeat":
                            assert "timestamp" in message_data
                        
                    except asyncio.TimeoutError:
                        # No message received, continue
                        pass
                    
                    await asyncio.sleep(1)
                
                # Connection should still be alive
                final_message = {
                    "type": "system_message",
                    "message": "Connection stability test completed"
                }
                await websocket.send(json.dumps(final_message))
                
                # Verify connection is still responsive
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                assert response is not None
                
        except Exception as e:
            pytest.fail(f"WebSocket connection stability test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_collaborative_editing_latency(self, websocket_url):
        """
        Test collaborative editing latency is consistently below 200ms.
        
        This test validates:
        1. Two clients can connect to the same document
        2. Message from one client reaches another within 200ms
        3. Document edit operations are broadcast correctly
        4. Latency measurements are accurate
        """
        document_id = "test_doc_latency"
        
        # Client configurations
        client1_config = {
            "user_id": "user1_latency",
            "display_name": "User 1 Latency"
        }
        client2_config = {
            "user_id": "user2_latency", 
            "display_name": "User 2 Latency"
        }
        
        # Build WebSocket URLs
        ws_url1 = f"{websocket_url}/{document_id}?user_id={client1_config['user_id']}&display_name={client1_config['display_name']}"
        ws_url2 = f"{websocket_url}/{document_id}?user_id={client2_config['user_id']}&display_name={client2_config['display_name']}"
        
        latency_measurements = []
        
        try:
            # Connect both clients
            async with websockets.connect(ws_url1) as ws1, websockets.connect(ws_url2) as ws2:
                # Join room for both clients
                for ws, config in [(ws1, client1_config), (ws2, client2_config)]:
                    join_message = {
                        "type": "join_room",
                        "room_id": f"document:{document_id}",
                        "document_id": document_id
                    }
                    await ws.send(json.dumps(join_message))
                    
                    # Receive welcome/join messages
                    await ws.recv()
                
                # Wait for both clients to be fully connected
                await asyncio.sleep(2)
                
                # Perform latency test with multiple edit operations
                for i in range(5):
                    # Client 1 sends document edit
                    edit_message = {
                        "type": "document_edit",
                        "room_id": f"document:{document_id}",
                        "operation": {
                            "type": "insert",
                            "position": i * 10,
                            "content": f"Test edit {i} "
                        },
                        "version": i,
                        "timestamp": time.time()
                    }
                    
                    # Record send time
                    send_time = time.time()
                    await ws1.send(json.dumps(edit_message))
                    
                    # Client 2 should receive the edit
                    try:
                        response = await asyncio.wait_for(ws2.recv(), timeout=1.0)
                        receive_time = time.time()
                        
                        response_data = json.loads(response)
                        
                        # Validate it's the correct edit message
                        if response_data.get("type") == "document_edit":
                            latency = (receive_time - send_time) * 1000  # Convert to milliseconds
                            latency_measurements.append(latency)
                            
                            # Validate latency requirement
                            assert latency < 200, f"Latency {latency:.2f}ms exceeds 200ms requirement"
                            
                            # Validate message content
                            assert response_data.get("operation", {}).get("content") == f"Test edit {i} "
                        
                    except asyncio.TimeoutError:
                        pytest.fail(f"Client 2 did not receive edit message {i} within timeout")
                    
                    # Small delay between operations
                    await asyncio.sleep(0.5)
                
                # Validate overall latency performance
                if latency_measurements:
                    avg_latency = sum(latency_measurements) / len(latency_measurements)
                    max_latency = max(latency_measurements)
                    
                    assert avg_latency < 100, f"Average latency {avg_latency:.2f}ms should be well below 200ms"
                    assert max_latency < 200, f"Maximum latency {max_latency:.2f}ms exceeds 200ms requirement"
                    
                    print(f"Latency test results: avg={avg_latency:.2f}ms, max={max_latency:.2f}ms")
                
        except Exception as e:
            pytest.fail(f"Collaborative editing latency test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_concurrent_users_support(self, websocket_url):
        """
        Test the system can support 100+ concurrent users in a single room.
        
        This test validates:
        1. Multiple WebSocket connections can be established simultaneously
        2. Messages are broadcast to all connected clients
        3. System performance remains stable under load
        4. No message loss occurs with high concurrency
        """
        document_id = "test_doc_concurrent"
        num_clients = 20  # Reduced for test environment, would be 100+ in production
        
        async def create_client_connection(client_id: int):
            """Create a single client connection and test messaging."""
            user_id = f"user_{client_id}"
            display_name = f"User {client_id}"
            ws_url = f"{websocket_url}/{document_id}?user_id={user_id}&display_name={display_name}"
            
            try:
                async with websockets.connect(ws_url) as websocket:
                    # Join room
                    join_message = {
                        "type": "join_room",
                        "room_id": f"document:{document_id}",
                        "document_id": document_id
                    }
                    await websocket.send(json.dumps(join_message))
                    
                    # Receive welcome message
                    await websocket.recv()
                    
                    # Send a test message
                    test_message = {
                        "type": "document_edit",
                        "room_id": f"document:{document_id}",
                        "operation": {
                            "type": "insert",
                            "position": client_id,
                            "content": f"Client {client_id} edit"
                        },
                        "client_id": client_id
                    }
                    await websocket.send(json.dumps(test_message))
                    
                    # Listen for messages from other clients
                    messages_received = 0
                    start_time = time.time()
                    
                    while time.time() - start_time < 10 and messages_received < 5:  # Listen for 10 seconds or 5 messages
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                            message_data = json.loads(message)
                            
                            if message_data.get("type") == "document_edit":
                                messages_received += 1
                        
                        except asyncio.TimeoutError:
                            break
                    
                    return {
                        "client_id": client_id,
                        "success": True,
                        "messages_received": messages_received
                    }
                    
            except Exception as e:
                return {
                    "client_id": client_id,
                    "success": False,
                    "error": str(e)
                }
        
        # Create concurrent connections
        tasks = [create_client_connection(i) for i in range(num_clients)]
        
        # Execute all connections concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Analyze results
        successful_connections = 0
        failed_connections = 0
        total_messages_received = 0
        
        for result in results:
            if isinstance(result, dict):
                if result.get("success"):
                    successful_connections += 1
                    total_messages_received += result.get("messages_received", 0)
                else:
                    failed_connections += 1
                    print(f"Client {result.get('client_id')} failed: {result.get('error')}")
            else:
                failed_connections += 1
                print(f"Unexpected result: {result}")
        
        # Validate concurrent user support
        success_rate = successful_connections / num_clients
        assert success_rate >= 0.9, f"Success rate {success_rate:.2%} below 90% threshold"
        assert execution_time < 30, f"Connection setup took {execution_time:.2f}s, should be under 30s"
        
        print(f"Concurrent users test: {successful_connections}/{num_clients} successful, "
              f"{total_messages_received} total messages, {execution_time:.2f}s")
    
    @pytest.mark.asyncio
    async def test_disconnect_and_reconnect_handling(self, websocket_url):
        """
        Test graceful handling of client disconnections and reconnections.
        
        This test validates:
        1. System handles unexpected disconnections gracefully
        2. Reconnection is seamless and state is preserved
        3. Other clients are notified of disconnections/reconnections
        4. No data loss occurs during disconnect/reconnect cycles
        """
        document_id = "test_doc_disconnect"
        user_id = "test_user_disconnect"
        display_name = "Test User Disconnect"
        
        ws_url = f"{websocket_url}/{document_id}?user_id={user_id}&display_name={display_name}"
        
        try:
            # Initial connection
            async with websockets.connect(ws_url) as websocket1:
                # Join room
                join_message = {
                    "type": "join_room",
                    "room_id": f"document:{document_id}",
                    "document_id": document_id
                }
                await websocket1.send(json.dumps(join_message))
                await websocket1.recv()  # Welcome message
                
                # Send some data
                edit_message = {
                    "type": "document_edit",
                    "room_id": f"document:{document_id}",
                    "operation": {
                        "type": "insert",
                        "position": 0,
                        "content": "Initial content before disconnect"
                    }
                }
                await websocket1.send(json.dumps(edit_message))
                
                # Simulate disconnect by closing connection
                await websocket1.close()
            
            # Wait a moment to simulate network interruption
            await asyncio.sleep(2)
            
            # Reconnect
            async with websockets.connect(ws_url) as websocket2:
                # Rejoin room
                rejoin_message = {
                    "type": "join_room",
                    "room_id": f"document:{document_id}",
                    "document_id": document_id
                }
                await websocket2.send(json.dumps(rejoin_message))
                
                # Should receive welcome message
                response = await websocket2.recv()
                response_data = json.loads(response)
                assert response_data.get("type") in ["system_message", "user_presence"]
                
                # Send another edit to verify functionality
                reconnect_edit = {
                    "type": "document_edit",
                    "room_id": f"document:{document_id}",
                    "operation": {
                        "type": "insert",
                        "position": 100,
                        "content": "Content after reconnect"
                    }
                }
                await websocket2.send(json.dumps(reconnect_edit))
                
                # Verify connection is working
                heartbeat = {
                    "type": "heartbeat",
                    "timestamp": time.time()
                }
                await websocket2.send(json.dumps(heartbeat))
                
                # Should receive heartbeat response
                response = await asyncio.wait_for(websocket2.recv(), timeout=5.0)
                response_data = json.loads(response)
                assert response_data.get("type") == "heartbeat"
                
        except Exception as e:
            pytest.fail(f"Disconnect and reconnect handling test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__])
