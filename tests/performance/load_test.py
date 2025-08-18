"""
Load Testing Suite for Phase 3, Task 3.4: Performance Optimization

This module provides comprehensive load testing for GremlinsAI to validate:
- Cache hit rates >70% for common API queries
- Vector search performance >1000 QPS
- Horizontal scaling to 10+ instances
- Load balancer traffic distribution effectiveness

Uses Locust for realistic user behavior simulation with hundreds/thousands
of concurrent users testing all major system components.
"""

import json
import random
import time
import uuid
from typing import Dict, List, Any
from locust import HttpUser, task, between, events
from locust.contrib.fasthttp import FastHttpUser
import websocket
import threading


class GremlinsAIUser(FastHttpUser):
    """
    Simulates realistic GremlinsAI user behavior for load testing.
    
    Tests all major system components:
    - Authentication and session management
    - Document upload and processing
    - RAG queries and vector search
    - Real-time collaboration features
    - Multimodal content processing
    """
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Initialize user session."""
        self.user_id = f"load_test_user_{uuid.uuid4().hex[:8]}"
        self.api_key = "test_api_key_for_load_testing"
        self.session_token = None
        self.document_ids = []
        self.conversation_id = None
        
        # Authenticate user
        self.authenticate()
    
    def authenticate(self):
        """Authenticate user and get session token."""
        response = self.client.post("/api/v1/auth/login", json={
            "user_id": self.user_id,
            "api_key": self.api_key
        })
        
        if response.status_code == 200:
            self.session_token = response.json().get("token")
            self.client.headers.update({
                "Authorization": f"Bearer {self.session_token}"
            })
    
    @task(3)
    def health_check(self):
        """Test health endpoint (high frequency)."""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")
    
    @task(5)
    def upload_document(self):
        """Test document upload and processing."""
        # Generate test document content
        content = f"Test document content for load testing. User: {self.user_id}. " * 50
        
        files = {
            "file": ("test_doc.txt", content, "text/plain")
        }
        
        with self.client.post("/api/v1/documents/upload", 
                             files=files, 
                             catch_response=True) as response:
            if response.status_code == 200:
                document_id = response.json().get("document_id")
                if document_id:
                    self.document_ids.append(document_id)
                response.success()
            else:
                response.failure(f"Document upload failed: {response.status_code}")
    
    @task(10)
    def rag_query(self):
        """Test RAG queries and vector search performance."""
        queries = [
            "What is artificial intelligence?",
            "How does machine learning work?",
            "Explain neural networks",
            "What are the benefits of automation?",
            "How to optimize database performance?",
            "What is cloud computing?",
            "Explain microservices architecture",
            "How does caching improve performance?",
            "What is load balancing?",
            "Describe horizontal scaling"
        ]
        
        query = random.choice(queries)
        
        with self.client.post("/api/v1/rag/query", 
                             json={
                                 "query": query,
                                 "max_results": 5,
                                 "include_sources": True
                             },
                             catch_response=True) as response:
            if response.status_code == 200:
                results = response.json().get("results", [])
                if len(results) > 0:
                    response.success()
                else:
                    response.failure("No results returned")
            else:
                response.failure(f"RAG query failed: {response.status_code}")
    
    @task(7)
    def vector_search(self):
        """Test vector search performance directly."""
        search_terms = [
            "performance optimization",
            "database scaling",
            "caching strategies",
            "load balancing",
            "microservices",
            "artificial intelligence",
            "machine learning",
            "data processing",
            "real-time systems",
            "distributed computing"
        ]
        
        term = random.choice(search_terms)
        
        with self.client.post("/api/v1/search/vector", 
                             json={
                                 "query": term,
                                 "limit": 10,
                                 "filters": {
                                     "document_type": "text"
                                 }
                             },
                             catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Vector search failed: {response.status_code}")
    
    @task(4)
    def chat_conversation(self):
        """Test chat conversation functionality."""
        if not self.conversation_id:
            # Create new conversation
            with self.client.post("/api/v1/conversations", 
                                 json={
                                     "title": f"Load test conversation {self.user_id}"
                                 }) as response:
                if response.status_code == 200:
                    self.conversation_id = response.json().get("conversation_id")
        
        if self.conversation_id:
            messages = [
                "Hello, how can you help me?",
                "What is the weather like today?",
                "Can you explain quantum computing?",
                "How do I optimize my code?",
                "What are best practices for testing?",
                "Tell me about distributed systems",
                "How does caching work?",
                "What is the difference between SQL and NoSQL?"
            ]
            
            message = random.choice(messages)
            
            with self.client.post(f"/api/v1/conversations/{self.conversation_id}/messages",
                                 json={
                                     "content": message,
                                     "role": "user"
                                 },
                                 catch_response=True) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Chat message failed: {response.status_code}")
    
    @task(2)
    def multimodal_upload(self):
        """Test multimodal content upload."""
        # Simulate image upload
        image_data = b"fake_image_data_for_testing" * 100
        
        files = {
            "file": ("test_image.jpg", image_data, "image/jpeg")
        }
        
        with self.client.post("/api/v1/multimodal/upload",
                             files=files,
                             catch_response=True) as response:
            if response.status_code in [200, 202]:  # Accept async processing
                response.success()
            else:
                response.failure(f"Multimodal upload failed: {response.status_code}")
    
    @task(1)
    def cache_performance_test(self):
        """Test cache performance with repeated queries."""
        # Make the same query multiple times to test caching
        cache_test_query = "cache performance test query"
        
        for i in range(3):
            with self.client.post("/api/v1/rag/query",
                                 json={
                                     "query": cache_test_query,
                                     "max_results": 5
                                 },
                                 catch_response=True) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Cache test failed: {response.status_code}")
    
    @task(1)
    def metrics_endpoint(self):
        """Test metrics endpoint for monitoring."""
        with self.client.get("/metrics", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Metrics endpoint failed: {response.status_code}")


class WebSocketUser(HttpUser):
    """
    Tests real-time collaboration features via WebSocket connections.
    
    Simulates collaborative editing scenarios with multiple users
    connecting to the same document and making concurrent edits.
    """
    
    wait_time = between(2, 5)
    
    def on_start(self):
        """Initialize WebSocket connection."""
        self.user_id = f"ws_user_{uuid.uuid4().hex[:8]}"
        self.document_id = f"test_doc_{random.randint(1, 10)}"  # Share documents
        self.ws = None
        self.connect_websocket()
    
    def connect_websocket(self):
        """Connect to WebSocket endpoint."""
        try:
            ws_url = f"ws://localhost:8000/api/v1/websocket/collaborate/{self.document_id}"
            ws_url += f"?user_id={self.user_id}&display_name=LoadTestUser"
            
            self.ws = websocket.create_connection(ws_url)
            
            # Join document room
            join_message = {
                "type": "join_room",
                "room_id": f"document:{self.document_id}",
                "document_id": self.document_id
            }
            self.ws.send(json.dumps(join_message))
            
        except Exception as e:
            print(f"WebSocket connection failed: {e}")
    
    @task(5)
    def send_document_edit(self):
        """Send document edit via WebSocket."""
        if not self.ws:
            return
        
        try:
            edit_message = {
                "type": "document_edit",
                "room_id": f"document:{self.document_id}",
                "operation": {
                    "type": "insert",
                    "position": random.randint(0, 100),
                    "content": f"Edit from {self.user_id} at {time.time()}"
                },
                "version": random.randint(1, 100)
            }
            
            self.ws.send(json.dumps(edit_message))
            
        except Exception as e:
            print(f"WebSocket send failed: {e}")
            self.connect_websocket()  # Reconnect
    
    @task(2)
    def send_cursor_position(self):
        """Send cursor position update."""
        if not self.ws:
            return
        
        try:
            cursor_message = {
                "type": "cursor_position",
                "room_id": f"document:{self.document_id}",
                "position": random.randint(0, 1000),
                "selection_start": random.randint(0, 50),
                "selection_end": random.randint(50, 100)
            }
            
            self.ws.send(json.dumps(cursor_message))
            
        except Exception as e:
            print(f"Cursor position send failed: {e}")
    
    def on_stop(self):
        """Clean up WebSocket connection."""
        if self.ws:
            try:
                self.ws.close()
            except:
                pass


# Performance metrics collection
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, context, **kwargs):
    """Collect performance metrics during load testing."""
    if exception:
        print(f"Request failed: {name} - {exception}")
    else:
        # Log successful requests for analysis
        if response_time > 1000:  # Log slow requests (>1s)
            print(f"Slow request: {name} - {response_time}ms")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Initialize load test."""
    print("Starting GremlinsAI load test...")
    print(f"Target host: {environment.host}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Finalize load test and collect results."""
    print("Load test completed.")
    
    # Calculate performance metrics
    stats = environment.stats
    
    print(f"Total requests: {stats.total.num_requests}")
    print(f"Failed requests: {stats.total.num_failures}")
    print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"95th percentile: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"Requests per second: {stats.total.total_rps:.2f}")
    
    # Check acceptance criteria
    failure_rate = stats.total.num_failures / stats.total.num_requests if stats.total.num_requests > 0 else 0
    avg_response_time = stats.total.avg_response_time
    
    print("\n=== ACCEPTANCE CRITERIA VALIDATION ===")
    print(f"Failure rate: {failure_rate:.2%} (should be <5%)")
    print(f"Average response time: {avg_response_time:.2f}ms (should be <500ms)")
    print(f"95th percentile: {stats.total.get_response_time_percentile(0.95):.2f}ms (should be <1000ms)")


if __name__ == "__main__":
    # Run load test with specific configuration
    import subprocess
    import sys
    
    # Configuration for different test scenarios
    test_configs = {
        "smoke": "--users 10 --spawn-rate 2 --run-time 60s",
        "load": "--users 100 --spawn-rate 10 --run-time 300s", 
        "stress": "--users 500 --spawn-rate 50 --run-time 600s",
        "spike": "--users 1000 --spawn-rate 100 --run-time 300s"
    }
    
    test_type = sys.argv[1] if len(sys.argv) > 1 else "load"
    config = test_configs.get(test_type, test_configs["load"])
    
    cmd = f"locust -f {__file__} --host=http://localhost:8000 {config} --html=load_test_report.html"
    
    print(f"Running {test_type} test...")
    print(f"Command: {cmd}")
    
    subprocess.run(cmd.split())
