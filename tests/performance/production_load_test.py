#!/usr/bin/env python3
"""
Production Load Testing Suite for GremlinsAI
Phase 4, Task 4.4: Load Testing & Optimization

This comprehensive Locust-based load testing suite simulates realistic user journeys
at scale to validate the system's ability to handle 1000+ concurrent users while
maintaining strict performance targets.

Features:
- Realistic user behavior simulation
- JWT authentication flow
- Document upload and processing
- Complex RAG queries
- Multi-agent task execution
- Real-time collaboration via WebSocket
- Comprehensive metrics collection
- Performance monitoring integration

Usage:
    locust -f production_load_test.py --host=http://localhost:8000
"""

import json
import random
import time
import uuid
import io
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from locust import HttpUser, task, between, events
from locust.exception import StopUser
import websocket
import threading
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
TEST_CONFIG = {
    "api_base": "/api/v1",
    "auth_endpoint": "/auth/login",
    "documents_endpoint": "/documents",
    "rag_endpoint": "/documents/rag",
    "multi_agent_endpoint": "/multi-agent/execute-task",
    "websocket_endpoint": "/ws/collaboration",
    "health_endpoint": "/health",
    
    # Test data configuration
    "test_users": [
        {"username": f"loadtest_user_{i}", "password": "LoadTest123!"}
        for i in range(1, 101)  # 100 test users
    ],
    
    # Document test data
    "test_documents": [
        {"name": "small_doc.txt", "size": 1024, "content_type": "text/plain"},
        {"name": "medium_doc.pdf", "size": 50 * 1024, "content_type": "application/pdf"},
        {"name": "large_doc.docx", "size": 500 * 1024, "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ],
    
    # RAG query templates
    "rag_queries": [
        "What are the main topics discussed in the document?",
        "Can you summarize the key findings?",
        "What recommendations are provided?",
        "How does this relate to current industry trends?",
        "What are the potential risks mentioned?",
        "What solutions are proposed for the identified problems?",
        "Can you extract the most important statistics?",
        "What are the next steps outlined in the document?",
    ],
    
    # Multi-agent task templates
    "multi_agent_tasks": [
        {
            "task_description": "Research and analyze market trends in renewable energy",
            "workflow_type": "research_analyze_write",
            "context": {"domain": "renewable_energy", "timeframe": "2024"}
        },
        {
            "task_description": "Analyze competitive landscape for AI startups",
            "workflow_type": "complex_analysis",
            "context": {"industry": "artificial_intelligence", "focus": "startups"}
        },
        {
            "task_description": "Create comprehensive report on cybersecurity best practices",
            "workflow_type": "collaborative_writing",
            "context": {"topic": "cybersecurity", "audience": "enterprise"}
        },
    ],
    
    # Performance thresholds
    "performance_thresholds": {
        "auth_response_time": 1.0,  # seconds
        "document_upload_time": 5.0,  # seconds
        "rag_query_time": 2.0,  # seconds
        "multi_agent_task_time": 30.0,  # seconds
        "websocket_connection_time": 2.0,  # seconds
    }
}

# Global metrics collection
METRICS = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "auth_failures": 0,
    "upload_failures": 0,
    "rag_failures": 0,
    "multi_agent_failures": 0,
    "websocket_failures": 0,
    "response_times": [],
    "error_details": []
}


class GremlinsAIUser(HttpUser):
    """
    Simulates a realistic GremlinsAI user performing various operations.
    
    This user class implements a comprehensive user journey that includes:
    1. Authentication and token management
    2. Document upload and processing
    3. RAG queries with various complexity levels
    4. Multi-agent task execution
    5. Real-time collaboration via WebSocket
    """
    
    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auth_token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.uploaded_documents: List[Dict[str, Any]] = []
        self.websocket_connection: Optional[websocket.WebSocket] = None
        self.session_id: str = str(uuid.uuid4())
        
        # Performance tracking
        self.request_start_time: Optional[float] = None
        self.user_metrics = {
            "requests_made": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "total_response_time": 0.0
        }
    
    def on_start(self):
        """Initialize user session with authentication."""
        logger.info(f"Starting user session: {self.session_id}")
        
        # Authenticate user
        if not self.authenticate():
            logger.error(f"Authentication failed for user {self.session_id}")
            raise StopUser("Authentication failed")
        
        logger.info(f"User {self.session_id} authenticated successfully")
    
    def on_stop(self):
        """Clean up user session."""
        logger.info(f"Stopping user session: {self.session_id}")
        
        # Close WebSocket connection if open
        if self.websocket_connection:
            try:
                self.websocket_connection.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket: {e}")
        
        # Log user metrics
        logger.info(f"User {self.session_id} metrics: {self.user_metrics}")
    
    def authenticate(self) -> bool:
        """Authenticate user and obtain JWT token."""
        start_time = time.time()
        
        # Select random test user
        user_data = random.choice(TEST_CONFIG["test_users"])
        
        try:
            response = self.client.post(
                f"{TEST_CONFIG['api_base']}{TEST_CONFIG['auth_endpoint']}",
                json={
                    "username": user_data["username"],
                    "password": user_data["password"]
                },
                headers={"Content-Type": "application/json"},
                name="auth_login"
            )
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                auth_data = response.json()
                self.auth_token = auth_data.get("access_token")
                self.user_id = user_data["username"]
                
                # Update metrics
                METRICS["successful_requests"] += 1
                METRICS["response_times"].append(response_time)
                self.user_metrics["successful_operations"] += 1
                
                # Check performance threshold
                if response_time > TEST_CONFIG["performance_thresholds"]["auth_response_time"]:
                    logger.warning(f"Auth response time exceeded threshold: {response_time:.2f}s")
                
                return True
            else:
                METRICS["failed_requests"] += 1
                METRICS["auth_failures"] += 1
                METRICS["error_details"].append({
                    "operation": "authentication",
                    "status_code": response.status_code,
                    "error": response.text,
                    "timestamp": datetime.utcnow().isoformat()
                })
                self.user_metrics["failed_operations"] += 1
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            METRICS["failed_requests"] += 1
            METRICS["auth_failures"] += 1
            self.user_metrics["failed_operations"] += 1
            return False
        finally:
            METRICS["total_requests"] += 1
            self.user_metrics["requests_made"] += 1
            self.user_metrics["total_response_time"] += response_time
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests."""
        if not self.auth_token:
            raise Exception("No authentication token available")
        
        return {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
    
    @task(3)
    def upload_document(self):
        """Upload a document for processing."""
        if not self.auth_token:
            return
        
        start_time = time.time()
        
        # Select random document type
        doc_config = random.choice(TEST_CONFIG["test_documents"])
        
        # Generate test document content
        content = self.generate_test_document_content(doc_config["size"])
        
        try:
            # Prepare multipart form data
            files = {
                "file": (doc_config["name"], io.BytesIO(content), doc_config["content_type"])
            }
            
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            response = self.client.post(
                f"{TEST_CONFIG['api_base']}{TEST_CONFIG['documents_endpoint']}/upload",
                files=files,
                headers=headers,
                name="document_upload"
            )
            
            response_time = time.time() - start_time
            
            if response.status_code in [200, 202]:  # Accept both success and accepted
                upload_data = response.json()
                
                # Store document info for later use
                self.uploaded_documents.append({
                    "filename": doc_config["name"],
                    "job_id": upload_data.get("job_id"),
                    "upload_time": datetime.utcnow(),
                    "size": doc_config["size"]
                })
                
                # Update metrics
                METRICS["successful_requests"] += 1
                METRICS["response_times"].append(response_time)
                self.user_metrics["successful_operations"] += 1
                
                # Check performance threshold
                if response_time > TEST_CONFIG["performance_thresholds"]["document_upload_time"]:
                    logger.warning(f"Document upload time exceeded threshold: {response_time:.2f}s")
                
                logger.info(f"Document uploaded successfully: {doc_config['name']} ({doc_config['size']} bytes)")
                
            else:
                METRICS["failed_requests"] += 1
                METRICS["upload_failures"] += 1
                METRICS["error_details"].append({
                    "operation": "document_upload",
                    "status_code": response.status_code,
                    "error": response.text,
                    "document_size": doc_config["size"],
                    "timestamp": datetime.utcnow().isoformat()
                })
                self.user_metrics["failed_operations"] += 1
                
        except Exception as e:
            logger.error(f"Document upload error: {e}")
            METRICS["failed_requests"] += 1
            METRICS["upload_failures"] += 1
            self.user_metrics["failed_operations"] += 1
        finally:
            METRICS["total_requests"] += 1
            self.user_metrics["requests_made"] += 1
            self.user_metrics["total_response_time"] += response_time
    
    @task(5)
    def perform_rag_query(self):
        """Perform a RAG query against uploaded documents."""
        if not self.auth_token:
            return
        
        start_time = time.time()
        
        # Select random query
        query = random.choice(TEST_CONFIG["rag_queries"])
        
        try:
            response = self.client.post(
                f"{TEST_CONFIG['api_base']}{TEST_CONFIG['rag_endpoint']}",
                json={
                    "query": query,
                    "top_k": random.randint(3, 10),
                    "certainty_threshold": random.uniform(0.7, 0.9),
                    "context_limit": random.randint(3000, 8000)
                },
                headers=self.get_auth_headers(),
                name="rag_query"
            )
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                rag_data = response.json()
                
                # Update metrics
                METRICS["successful_requests"] += 1
                METRICS["response_times"].append(response_time)
                self.user_metrics["successful_operations"] += 1
                
                # Check performance threshold
                if response_time > TEST_CONFIG["performance_thresholds"]["rag_query_time"]:
                    logger.warning(f"RAG query time exceeded threshold: {response_time:.2f}s")
                
                # Log query performance
                confidence = rag_data.get("confidence", 0)
                sources_count = len(rag_data.get("sources", []))
                
                logger.info(f"RAG query completed: {response_time:.2f}s, confidence: {confidence:.2f}, sources: {sources_count}")
                
            else:
                METRICS["failed_requests"] += 1
                METRICS["rag_failures"] += 1
                METRICS["error_details"].append({
                    "operation": "rag_query",
                    "status_code": response.status_code,
                    "error": response.text,
                    "query": query[:100],
                    "timestamp": datetime.utcnow().isoformat()
                })
                self.user_metrics["failed_operations"] += 1
                
        except Exception as e:
            logger.error(f"RAG query error: {e}")
            METRICS["failed_requests"] += 1
            METRICS["rag_failures"] += 1
            self.user_metrics["failed_operations"] += 1
        finally:
            METRICS["total_requests"] += 1
            self.user_metrics["requests_made"] += 1
            self.user_metrics["total_response_time"] += response_time
    
    @task(2)
    def execute_multi_agent_task(self):
        """Execute a multi-agent workflow task."""
        if not self.auth_token:
            return
        
        start_time = time.time()
        
        # Select random multi-agent task
        task_config = random.choice(TEST_CONFIG["multi_agent_tasks"])
        
        try:
            response = self.client.post(
                f"{TEST_CONFIG['api_base']}{TEST_CONFIG['multi_agent_endpoint']}",
                json=task_config,
                headers=self.get_auth_headers(),
                name="multi_agent_task",
                timeout=60  # Longer timeout for multi-agent tasks
            )
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                task_data = response.json()
                
                # Update metrics
                METRICS["successful_requests"] += 1
                METRICS["response_times"].append(response_time)
                self.user_metrics["successful_operations"] += 1
                
                # Check performance threshold
                if response_time > TEST_CONFIG["performance_thresholds"]["multi_agent_task_time"]:
                    logger.warning(f"Multi-agent task time exceeded threshold: {response_time:.2f}s")
                
                # Log task performance
                result_length = len(task_data.get("result", ""))
                agents_used = len(task_data.get("agents_used", []))
                
                logger.info(f"Multi-agent task completed: {response_time:.2f}s, result length: {result_length}, agents: {agents_used}")
                
            else:
                METRICS["failed_requests"] += 1
                METRICS["multi_agent_failures"] += 1
                METRICS["error_details"].append({
                    "operation": "multi_agent_task",
                    "status_code": response.status_code,
                    "error": response.text,
                    "task_type": task_config["workflow_type"],
                    "timestamp": datetime.utcnow().isoformat()
                })
                self.user_metrics["failed_operations"] += 1
                
        except Exception as e:
            logger.error(f"Multi-agent task error: {e}")
            METRICS["failed_requests"] += 1
            METRICS["multi_agent_failures"] += 1
            self.user_metrics["failed_operations"] += 1
        finally:
            METRICS["total_requests"] += 1
            self.user_metrics["requests_made"] += 1
            self.user_metrics["total_response_time"] += response_time

    @task(1)
    def websocket_collaboration(self):
        """Test real-time collaboration via WebSocket."""
        if not self.auth_token:
            return

        start_time = time.time()

        try:
            # Create WebSocket connection
            ws_url = f"ws://{self.host.replace('http://', '')}{TEST_CONFIG['api_base']}{TEST_CONFIG['websocket_endpoint']}"

            # Add authentication to WebSocket URL
            ws_url += f"?token={self.auth_token}"

            ws = websocket.create_connection(ws_url, timeout=5)

            connection_time = time.time() - start_time

            # Send test messages
            test_messages = [
                {"type": "join_room", "room_id": f"test_room_{random.randint(1, 10)}"},
                {"type": "message", "content": f"Test message from {self.user_id}"},
                {"type": "typing", "status": "start"},
                {"type": "typing", "status": "stop"},
            ]

            for message in test_messages:
                ws.send(json.dumps(message))
                time.sleep(0.1)  # Small delay between messages

                # Try to receive response
                try:
                    response = ws.recv()
                    logger.debug(f"WebSocket response: {response}")
                except websocket.WebSocketTimeoutError:
                    pass  # Timeout is acceptable for some messages

            ws.close()

            total_time = time.time() - start_time

            # Update metrics
            METRICS["successful_requests"] += 1
            METRICS["response_times"].append(total_time)
            self.user_metrics["successful_operations"] += 1

            # Check performance threshold
            if connection_time > TEST_CONFIG["performance_thresholds"]["websocket_connection_time"]:
                logger.warning(f"WebSocket connection time exceeded threshold: {connection_time:.2f}s")

            logger.info(f"WebSocket collaboration completed: {total_time:.2f}s")

        except Exception as e:
            logger.error(f"WebSocket collaboration error: {e}")
            METRICS["failed_requests"] += 1
            METRICS["websocket_failures"] += 1
            METRICS["error_details"].append({
                "operation": "websocket_collaboration",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
            self.user_metrics["failed_operations"] += 1
        finally:
            METRICS["total_requests"] += 1
            self.user_metrics["requests_made"] += 1

    @task(1)
    def health_check(self):
        """Perform health check to monitor system status."""
        start_time = time.time()

        try:
            response = self.client.get(
                f"{TEST_CONFIG['api_base']}{TEST_CONFIG['health_endpoint']}",
                name="health_check"
            )

            response_time = time.time() - start_time

            if response.status_code == 200:
                health_data = response.json()

                # Update metrics
                METRICS["successful_requests"] += 1
                METRICS["response_times"].append(response_time)
                self.user_metrics["successful_operations"] += 1

                # Log system health
                status = health_data.get("status", "unknown")
                logger.debug(f"System health: {status}")

            else:
                METRICS["failed_requests"] += 1
                self.user_metrics["failed_operations"] += 1

        except Exception as e:
            logger.error(f"Health check error: {e}")
            METRICS["failed_requests"] += 1
            self.user_metrics["failed_operations"] += 1
        finally:
            METRICS["total_requests"] += 1
            self.user_metrics["requests_made"] += 1

    def generate_test_document_content(self, size: int) -> bytes:
        """Generate test document content of specified size."""
        # Generate realistic text content
        base_text = """
        This is a test document for load testing the GremlinsAI platform.
        It contains various types of content to simulate real-world documents.

        Key topics covered:
        - Artificial Intelligence and Machine Learning
        - Document Processing and Analysis
        - Vector Embeddings and Semantic Search
        - Multi-Agent Systems and Collaboration
        - Performance Optimization and Scalability

        The document includes technical details, business insights, and
        recommendations for implementation. This content is designed to
        test the RAG system's ability to extract meaningful information
        and provide accurate responses to user queries.
        """

        # Repeat content to reach desired size
        content = base_text
        while len(content.encode()) < size:
            content += base_text

        # Truncate to exact size
        return content.encode()[:size]


# Event handlers for metrics collection
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Initialize test metrics when test starts."""
    logger.info("Starting GremlinsAI production load test")
    logger.info(f"Target host: {environment.host}")
    logger.info(f"Expected users: {environment.runner.target_user_count}")

    # Reset metrics
    global METRICS
    METRICS = {
        "total_requests": 0,
        "successful_requests": 0,
        "failed_requests": 0,
        "auth_failures": 0,
        "upload_failures": 0,
        "rag_failures": 0,
        "multi_agent_failures": 0,
        "websocket_failures": 0,
        "response_times": [],
        "error_details": []
    }


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Generate final metrics report when test stops."""
    logger.info("GremlinsAI production load test completed")

    # Calculate final metrics
    total_requests = METRICS["total_requests"]
    success_rate = (METRICS["successful_requests"] / total_requests * 100) if total_requests > 0 else 0

    response_times = METRICS["response_times"]
    if response_times:
        avg_response_time = sum(response_times) / len(response_times)
        p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)]
        p99_response_time = sorted(response_times)[int(len(response_times) * 0.99)]
    else:
        avg_response_time = p95_response_time = p99_response_time = 0

    # Generate metrics report
    report = {
        "test_summary": {
            "total_requests": total_requests,
            "successful_requests": METRICS["successful_requests"],
            "failed_requests": METRICS["failed_requests"],
            "success_rate": f"{success_rate:.2f}%",
            "test_duration": environment.runner.stats.total.get_current_response_time_percentile(1.0)
        },
        "performance_metrics": {
            "average_response_time": f"{avg_response_time:.3f}s",
            "p95_response_time": f"{p95_response_time:.3f}s",
            "p99_response_time": f"{p99_response_time:.3f}s",
            "requests_per_second": environment.runner.stats.total.current_rps
        },
        "failure_breakdown": {
            "auth_failures": METRICS["auth_failures"],
            "upload_failures": METRICS["upload_failures"],
            "rag_failures": METRICS["rag_failures"],
            "multi_agent_failures": METRICS["multi_agent_failures"],
            "websocket_failures": METRICS["websocket_failures"]
        },
        "error_details": METRICS["error_details"][-10:]  # Last 10 errors
    }

    # Save metrics to file
    with open(f"load_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
        json.dump(report, f, indent=2)

    logger.info(f"Final metrics: {json.dumps(report, indent=2)}")


if __name__ == "__main__":
    # This allows running the test directly with python
    import subprocess
    import sys

    print("Starting GremlinsAI Production Load Test")
    print("Use: locust -f production_load_test.py --host=http://localhost:8000")

    # Optional: Auto-start locust if run directly
    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        subprocess.run([
            "locust",
            "-f", "production_load_test.py",
            "--host=http://localhost:8000",
            "--users=100",
            "--spawn-rate=10",
            "--run-time=30m",
            "--html=load_test_report.html"
        ])
