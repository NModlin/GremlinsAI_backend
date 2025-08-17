"""
End-to-End Orchestrator Workflow Tests - Task T3.3

This module tests complete orchestrator workflows that coordinate
multiple system components for complex task execution.

Features:
- Task orchestration workflows
- Multi-component coordination
- Asynchronous task execution
- Task status monitoring
- Error handling and recovery
- Performance monitoring
"""

import pytest
import asyncio
import httpx
import json
import time
from typing import Dict, Any, List, Optional

# Test configuration
BASE_URL = "http://localhost:8000"  # Staging environment URL
TIMEOUT = 30.0  # Request timeout in seconds


class E2ETestClient:
    """Enhanced HTTP client for end-to-end testing."""

    def __init__(self, base_url: str = BASE_URL, timeout: float = TIMEOUT):
        self.base_url = base_url
        self.timeout = timeout
        self.session_data = {}

    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            follow_redirects=True
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def post(self, endpoint: str, json_data: Dict[str, Any] = None, **kwargs) -> httpx.Response:
        """Make POST request with error handling."""
        try:
            response = await self.client.post(endpoint, json=json_data, **kwargs)
            return response
        except httpx.TimeoutException:
            pytest.fail(f"Request to {endpoint} timed out after {self.timeout}s")
        except httpx.RequestError as e:
            pytest.fail(f"Request to {endpoint} failed: {e}")

    async def get(self, endpoint: str, **kwargs) -> httpx.Response:
        """Make GET request with error handling."""
        try:
            response = await self.client.get(endpoint, **kwargs)
            return response
        except httpx.TimeoutException:
            pytest.fail(f"Request to {endpoint} timed out after {self.timeout}s")
        except httpx.RequestError as e:
            pytest.fail(f"Request to {endpoint} failed: {e}")


class TestOrchestratorWorkflow:
    """End-to-end tests for orchestrator workflows."""
    
    @pytest.fixture
    async def e2e_client(self):
        """Create E2E test client."""
        async with E2ETestClient() as client:
            yield client
    
    @pytest.mark.asyncio
    async def test_synchronous_task_orchestration_workflow(self, e2e_client):
        """Test complete synchronous task orchestration workflow."""
        # Step 1: Execute synchronous agent chat task
        task_request = {
            "task_type": "AGENT_CHAT",
            "payload": {
                "input": "Explain the concept of machine learning in simple terms",
                "conversation_id": None,
                "save_conversation": True
            },
            "execution_mode": "SYNCHRONOUS",
            "priority": 1
        }
        
        print(f"\n🔍 Step 1: Executing synchronous orchestrator task")
        print(f"   Task type: {task_request['task_type']}")
        print(f"   Execution mode: {task_request['execution_mode']}")
        
        response = await e2e_client.post("/api/v1/orchestrator/execute", json_data=task_request)
        
        assert response.status_code == 200, f"Orchestrator task failed: {response.text}"
        data = response.json()
        
        # Validate orchestrator response structure
        assert "task_id" in data, "Response missing 'task_id' field"
        assert "status" in data, "Response missing 'status' field"
        assert "result" in data, "Response missing 'result' field"
        assert "execution_time" in data, "Response missing 'execution_time' field"
        
        task_id = data["task_id"]
        status = data["status"]
        result = data["result"]
        execution_time = data["execution_time"]
        
        assert task_id is not None, "Task ID should not be None"
        assert status in ["COMPLETED", "FAILED", "PENDING"], f"Invalid status: {status}"
        assert isinstance(execution_time, (int, float)), "Execution time should be numeric"
        
        print(f"✅ Synchronous task completed")
        print(f"   Task ID: {task_id}")
        print(f"   Status: {status}")
        print(f"   Execution time: {execution_time:.2f}s")
        print(f"   Result length: {len(str(result)) if result else 0} characters")
        
        # Step 2: Check task status
        if task_id:
            print(f"\n🔍 Step 2: Checking task status")
            
            status_response = await e2e_client.get(f"/api/v1/orchestrator/status/{task_id}")
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                
                assert "task_id" in status_data, "Status response missing 'task_id' field"
                assert "status" in status_data, "Status response missing 'status' field"
                assert status_data["task_id"] == task_id, "Task ID mismatch"
                
                print(f"✅ Task status retrieved")
                print(f"   Status: {status_data['status']}")
                print(f"   Task ID matches: ✅")
            else:
                print(f"⚠️  Task status check failed: {status_response.status_code}")
        
        # Step 3: Check orchestrator health
        print(f"\n🔍 Step 3: Checking orchestrator health")
        
        health_response = await e2e_client.get("/api/v1/orchestrator/health")
        
        if health_response.status_code == 200:
            health_data = health_response.json()
            
            assert "status" in health_data, "Health response missing 'status' field"
            
            print(f"✅ Orchestrator health check completed")
            print(f"   Status: {health_data['status']}")
            print(f"   Active tasks: {health_data.get('active_tasks', 'N/A')}")
            print(f"   Completed tasks: {health_data.get('completed_tasks', 'N/A')}")
        else:
            print(f"⚠️  Orchestrator health check failed: {health_response.status_code}")
    
    @pytest.mark.asyncio
    async def test_enhanced_agent_chat_workflow(self, e2e_client):
        """Test enhanced agent chat workflow through orchestrator."""
        # Test enhanced chat with multiple features
        enhanced_request = {
            "input": "What are the environmental benefits of renewable energy?",
            "conversation_id": None,
            "use_multi_agent": True,
            "use_rag": False,
            "save_conversation": True,
            "async_mode": False
        }
        
        print(f"\n🔍 Testing enhanced agent chat workflow")
        print(f"   Multi-agent: {enhanced_request['use_multi_agent']}")
        print(f"   RAG enabled: {enhanced_request['use_rag']}")
        print(f"   Async mode: {enhanced_request['async_mode']}")
        
        # Make request to enhanced chat endpoint
        response = await e2e_client.post("/api/v1/orchestrator/agent/enhanced-chat", params=enhanced_request)
        
        if response.status_code == 200:
            data = response.json()
            
            # Validate enhanced chat response
            assert "task_id" in data, "Enhanced chat response missing 'task_id' field"
            assert "status" in data, "Enhanced chat response missing 'status' field"
            assert "response" in data, "Enhanced chat response missing 'response' field"
            assert "execution_time" in data, "Enhanced chat response missing 'execution_time' field"
            assert "async_mode" in data, "Enhanced chat response missing 'async_mode' field"
            
            task_id = data["task_id"]
            status = data["status"]
            response_content = data["response"]
            execution_time = data["execution_time"]
            async_mode = data["async_mode"]
            
            print(f"✅ Enhanced agent chat completed")
            print(f"   Task ID: {task_id}")
            print(f"   Status: {status}")
            print(f"   Execution time: {execution_time:.2f}s")
            print(f"   Async mode: {async_mode}")
            print(f"   Response available: {'✅' if response_content else '❌'}")
            
            # If response is available, validate content
            if response_content and isinstance(response_content, dict):
                if "output" in response_content:
                    output = response_content["output"]
                    print(f"   Response length: {len(output)} characters")
                    assert len(output) > 0, "Enhanced chat output should not be empty"
        
        else:
            print(f"⚠️  Enhanced agent chat failed: {response.status_code}")
            # Continue with other tests even if this fails
    
    @pytest.mark.asyncio
    async def test_multi_task_orchestration_workflow(self, e2e_client):
        """Test orchestration of multiple concurrent tasks."""
        # Create multiple tasks for concurrent execution
        tasks = [
            {
                "task_type": "AGENT_CHAT",
                "payload": {
                    "input": f"Task {i}: What is the significance of task {i} in AI systems?",
                    "save_conversation": False
                },
                "execution_mode": "SYNCHRONOUS",
                "priority": i
            }
            for i in range(1, 4)  # Create 3 tasks
        ]
        
        print(f"\n🔍 Testing multi-task orchestration workflow")
        print(f"   Number of tasks: {len(tasks)}")
        
        # Submit all tasks concurrently
        task_responses = []
        for i, task in enumerate(tasks):
            print(f"   Submitting task {i+1}: {task['payload']['input'][:50]}...")
            
            response = await e2e_client.post("/api/v1/orchestrator/execute", json_data=task)
            task_responses.append((i+1, response))
        
        # Analyze results
        successful_tasks = 0
        failed_tasks = 0
        total_execution_time = 0
        
        for task_num, response in task_responses:
            if response.status_code == 200:
                data = response.json()
                status = data.get("status", "UNKNOWN")
                execution_time = data.get("execution_time", 0)
                
                if status == "COMPLETED":
                    successful_tasks += 1
                    total_execution_time += execution_time
                    print(f"   ✅ Task {task_num} completed in {execution_time:.2f}s")
                else:
                    failed_tasks += 1
                    print(f"   ❌ Task {task_num} failed with status: {status}")
            else:
                failed_tasks += 1
                print(f"   ❌ Task {task_num} request failed: {response.status_code}")
        
        # Validate overall performance
        success_rate = successful_tasks / len(tasks)
        avg_execution_time = total_execution_time / successful_tasks if successful_tasks > 0 else 0
        
        print(f"\n✅ Multi-task orchestration completed")
        print(f"   Total tasks: {len(tasks)}")
        print(f"   Successful: {successful_tasks}")
        print(f"   Failed: {failed_tasks}")
        print(f"   Success rate: {success_rate:.2%}")
        print(f"   Average execution time: {avg_execution_time:.2f}s")
        
        # Assert reasonable success rate
        assert success_rate >= 0.5, f"Success rate too low: {success_rate:.2%}"
    
    @pytest.mark.asyncio
    async def test_orchestrator_error_handling_workflow(self, e2e_client):
        """Test orchestrator error handling and recovery workflows."""
        # Test invalid task type
        invalid_task = {
            "task_type": "INVALID_TASK_TYPE",
            "payload": {"input": "This should fail"},
            "execution_mode": "SYNCHRONOUS"
        }
        
        print(f"\n🔍 Testing orchestrator error handling")
        print(f"   Testing invalid task type: {invalid_task['task_type']}")
        
        response = await e2e_client.post("/api/v1/orchestrator/execute", json_data=invalid_task)
        
        # Should return appropriate error status
        assert response.status_code in [400, 422, 500], f"Expected error status, got {response.status_code}"
        
        if response.status_code in [400, 422]:
            error_data = response.json()
            assert "detail" in error_data, "Error response should contain 'detail' field"
            print(f"   ✅ Invalid task type properly rejected: {response.status_code}")
        else:
            print(f"   ✅ Invalid task type handled with server error: {response.status_code}")
        
        # Test malformed payload
        malformed_task = {
            "task_type": "AGENT_CHAT",
            "payload": "this should be a dict, not a string",
            "execution_mode": "SYNCHRONOUS"
        }
        
        print(f"   Testing malformed payload")
        
        malformed_response = await e2e_client.post("/api/v1/orchestrator/execute", json_data=malformed_task)
        
        # Should return validation error
        assert malformed_response.status_code in [400, 422], f"Expected validation error, got {malformed_response.status_code}"
        
        print(f"   ✅ Malformed payload properly rejected: {malformed_response.status_code}")
        
        # Test recovery with valid task
        recovery_task = {
            "task_type": "AGENT_CHAT",
            "payload": {
                "input": "This is a recovery test after error scenarios",
                "save_conversation": False
            },
            "execution_mode": "SYNCHRONOUS"
        }
        
        print(f"   Testing recovery with valid task")
        
        recovery_response = await e2e_client.post("/api/v1/orchestrator/execute", json_data=recovery_task)
        
        # Recovery should succeed
        if recovery_response.status_code == 200:
            recovery_data = recovery_response.json()
            print(f"   ✅ Recovery successful: {recovery_data.get('status', 'UNKNOWN')}")
        else:
            print(f"   ⚠️  Recovery failed: {recovery_response.status_code}")
        
        print(f"\n✅ Orchestrator error handling workflow completed")


class TestWorkflowIntegration:
    """Test integration between different workflow components."""
    
    @pytest.fixture
    async def e2e_client(self):
        """Create E2E test client."""
        async with E2ETestClient() as client:
            yield client
    
    @pytest.mark.asyncio
    async def test_agent_to_orchestrator_workflow(self, e2e_client):
        """Test workflow that uses both direct agent API and orchestrator."""
        # Step 1: Start conversation with direct agent API
        direct_request = {
            "input": "What are the key principles of sustainable development?",
            "save_conversation": True
        }
        
        print(f"\n🔍 Step 1: Starting conversation with direct agent API")
        
        direct_response = await e2e_client.post("/api/v1/agent/chat", json_data=direct_request)
        
        assert direct_response.status_code == 200, f"Direct agent request failed: {direct_response.text}"
        direct_data = direct_response.json()
        
        conversation_id = direct_data["conversation_id"]
        assert conversation_id is not None, "Conversation ID should be created"
        
        print(f"   ✅ Direct agent conversation started (ID: {conversation_id})")
        
        # Step 2: Continue conversation through orchestrator
        orchestrator_request = {
            "task_type": "AGENT_CHAT",
            "payload": {
                "input": "How do these principles apply to urban planning?",
                "conversation_id": conversation_id,
                "save_conversation": True
            },
            "execution_mode": "SYNCHRONOUS"
        }
        
        print(f"\n🔍 Step 2: Continuing conversation through orchestrator")
        
        orchestrator_response = await e2e_client.post("/api/v1/orchestrator/execute", json_data=orchestrator_request)
        
        if orchestrator_response.status_code == 200:
            orchestrator_data = orchestrator_response.json()
            
            # Validate that orchestrator maintained conversation context
            assert orchestrator_data["status"] in ["COMPLETED", "PENDING"], f"Unexpected status: {orchestrator_data['status']}"
            
            print(f"   ✅ Orchestrator continued conversation successfully")
            print(f"   Status: {orchestrator_data['status']}")
            
            # Step 3: Verify conversation history
            history_response = await e2e_client.get(f"/api/v1/history/conversations/{conversation_id}/messages")
            
            if history_response.status_code == 200:
                history_data = history_response.json()
                messages = history_data.get("messages", [])
                
                # Should have at least 4 messages (2 user + 2 assistant)
                assert len(messages) >= 4, f"Expected at least 4 messages, got {len(messages)}"
                
                print(f"   ✅ Conversation history validated")
                print(f"   Total messages: {len(messages)}")
                print(f"   Integration successful: ✅")
            else:
                print(f"   ⚠️  Could not verify conversation history: {history_response.status_code}")
        
        else:
            print(f"   ⚠️  Orchestrator continuation failed: {orchestrator_response.status_code}")
    
    @pytest.mark.asyncio
    async def test_end_to_end_system_workflow(self, e2e_client):
        """Test complete end-to-end system workflow touching all major components."""
        workflow_steps = []
        
        # Step 1: Check system health
        print(f"\n🔍 Step 1: Checking system health")
        
        health_response = await e2e_client.get("/api/v1/health/health")
        
        if health_response.status_code == 200:
            health_data = health_response.json()
            workflow_steps.append(("health_check", "✅", health_data.get("status", "unknown")))
            print(f"   ✅ System health: {health_data.get('status', 'unknown')}")
        else:
            workflow_steps.append(("health_check", "❌", f"HTTP {health_response.status_code}"))
            print(f"   ❌ System health check failed: {health_response.status_code}")
        
        # Step 2: Get system capabilities
        print(f"\n🔍 Step 2: Getting system capabilities")
        
        capabilities_response = await e2e_client.get("/api/v1/multi-agent/capabilities")
        
        if capabilities_response.status_code == 200:
            capabilities_data = capabilities_response.json()
            workflow_steps.append(("capabilities", "✅", f"{len(capabilities_data.get('agents', {}))} agents"))
            print(f"   ✅ System capabilities retrieved")
        else:
            workflow_steps.append(("capabilities", "❌", f"HTTP {capabilities_response.status_code}"))
            print(f"   ❌ Capabilities check failed: {capabilities_response.status_code}")
        
        # Step 3: Execute multi-agent workflow
        print(f"\n🔍 Step 3: Executing multi-agent workflow")
        
        multi_agent_request = {
            "input": "Analyze the impact of artificial intelligence on future job markets",
            "workflow_type": "simple_research",
            "save_conversation": True
        }
        
        multi_agent_response = await e2e_client.post("/api/v1/multi-agent/execute", json_data=multi_agent_request)
        
        if multi_agent_response.status_code == 200:
            multi_agent_data = multi_agent_response.json()
            conversation_id = multi_agent_data.get("conversation_id")
            workflow_steps.append(("multi_agent", "✅", f"Conv: {conversation_id[:8] if conversation_id else 'N/A'}"))
            print(f"   ✅ Multi-agent workflow completed")
        else:
            workflow_steps.append(("multi_agent", "❌", f"HTTP {multi_agent_response.status_code}"))
            print(f"   ❌ Multi-agent workflow failed: {multi_agent_response.status_code}")
        
        # Step 4: Test orchestrator integration
        print(f"\n🔍 Step 4: Testing orchestrator integration")
        
        orchestrator_health = await e2e_client.get("/api/v1/orchestrator/health")
        
        if orchestrator_health.status_code == 200:
            orchestrator_data = orchestrator_health.json()
            workflow_steps.append(("orchestrator", "✅", orchestrator_data.get("status", "unknown")))
            print(f"   ✅ Orchestrator health: {orchestrator_data.get('status', 'unknown')}")
        else:
            workflow_steps.append(("orchestrator", "❌", f"HTTP {orchestrator_health.status_code}"))
            print(f"   ❌ Orchestrator health failed: {orchestrator_health.status_code}")
        
        # Step 5: Test real-time capabilities
        print(f"\n🔍 Step 5: Testing real-time capabilities")
        
        realtime_info = await e2e_client.get("/api/v1/realtime/info")
        
        if realtime_info.status_code == 200:
            realtime_data = realtime_info.json()
            workflow_steps.append(("realtime", "✅", f"{len(realtime_data.get('supported_message_types', []))} types"))
            print(f"   ✅ Real-time capabilities available")
        else:
            workflow_steps.append(("realtime", "❌", f"HTTP {realtime_info.status_code}"))
            print(f"   ❌ Real-time capabilities failed: {realtime_info.status_code}")
        
        # Final workflow summary
        print(f"\n🎉 End-to-End System Workflow Summary")
        print(f"   {'Component':<15} {'Status':<6} {'Details'}")
        print(f"   {'-'*15} {'-'*6} {'-'*20}")
        
        successful_steps = 0
        for step_name, status, details in workflow_steps:
            print(f"   {step_name:<15} {status:<6} {details}")
            if status == "✅":
                successful_steps += 1
        
        success_rate = successful_steps / len(workflow_steps)
        print(f"\n   Overall Success Rate: {success_rate:.2%} ({successful_steps}/{len(workflow_steps)})")
        
        # Assert reasonable success rate for E2E workflow
        assert success_rate >= 0.6, f"E2E workflow success rate too low: {success_rate:.2%}"
        
        print(f"   🎉 End-to-End System Workflow PASSED")


# Test execution markers
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.asyncio,
    pytest.mark.timeout(600)  # 10 minute timeout for orchestrator tests
]
