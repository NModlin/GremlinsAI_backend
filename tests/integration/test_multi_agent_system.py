"""
Integration tests for the Multi-Agent Coordination System
Phase 3, Task 3.1: Multi-Agent Coordination System

Tests the complete multi-agent workflow including:
- Multiple specialized agents coordination
- Inter-agent communication and context preservation
- Workflow execution engine with error handling
- Performance monitoring and metrics tracking
- Complex task completion that single agents cannot handle
"""

import pytest
import asyncio
import time
import json
from typing import Dict, Any
from fastapi.testclient import TestClient
from testcontainers.compose import DockerCompose

from app.main import app
from app.core.config import get_settings


class TestMultiAgentCoordinationSystem:
    """Integration tests for the complete multi-agent coordination system."""
    
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
    
    @pytest.mark.asyncio
    async def test_multi_agent_coordination_workflow(self, test_client: TestClient):
        """
        Test the complete multi-agent coordination system following acceptance criteria.
        
        This test validates:
        1. Multiple agents can coordinate to complete complex tasks
        2. Context and information are preserved between agents
        3. Workflow execution handles failures gracefully
        4. Performance metrics are logged and tracked
        5. Complex tasks that single agents cannot handle are completed
        """
        # Step 1: Upload multiple documents with different types of information
        documents = [
            {
                "title": "GremlinsAI Technical Architecture",
                "content": """
                GremlinsAI Technical Architecture Overview
                
                System Components:
                - Multi-Agent Coordination System using CrewAI framework
                - RAG (Retrieval-Augmented Generation) system with Weaviate
                - Document processing pipeline with intelligent chunking
                - Real-time collaboration features with WebSocket support
                
                Key Technologies:
                - Vector Database: Weaviate for semantic search
                - LLM Integration: ProductionLLMManager with local and cloud providers
                - Background Processing: Celery with Redis for async tasks
                - API Framework: FastAPI with comprehensive endpoint coverage
                
                Performance Requirements:
                - Sub-2-second RAG response times
                - 30-second document processing pipeline
                - >90% test coverage with integration testing
                - Real-time collaboration with <200ms latency
                """,
                "content_type": "text/markdown"
            },
            {
                "title": "GremlinsAI Business Requirements",
                "content": """
                GremlinsAI Business Requirements and Objectives
                
                Primary Goals:
                - Provide intelligent document processing and retrieval
                - Enable collaborative AI-powered workflows
                - Support enterprise-scale deployment and scaling
                - Maintain high security and data privacy standards
                
                Target Markets:
                - Enterprise knowledge management
                - Research and development teams
                - Educational institutions
                - Content creation and analysis
                
                Success Metrics:
                - User engagement and retention rates
                - Query accuracy and relevance scores
                - System performance and reliability
                - Customer satisfaction and feedback
                
                Competitive Advantages:
                - Advanced multi-agent coordination capabilities
                - Semantic search with high accuracy
                - Real-time collaborative features
                - Comprehensive API ecosystem
                """,
                "content_type": "text/markdown"
            },
            {
                "title": "GremlinsAI Risk Assessment",
                "content": """
                GremlinsAI Risk Assessment and Mitigation Strategies
                
                Technical Risks:
                - LLM provider availability and rate limiting
                - Vector database performance under high load
                - Multi-agent coordination complexity and failure modes
                - Data consistency during migration processes
                
                Business Risks:
                - Market competition from established players
                - Regulatory changes affecting AI systems
                - Data privacy and security compliance requirements
                - Scaling costs and infrastructure management
                
                Mitigation Strategies:
                - Implement fallback mechanisms for all critical components
                - Comprehensive monitoring and alerting systems
                - Regular security audits and compliance reviews
                - Diversified technology stack with vendor independence
                
                Opportunities:
                - Growing demand for AI-powered knowledge management
                - Potential for industry partnerships and integrations
                - Expansion into specialized vertical markets
                - Development of proprietary AI models and algorithms
                """,
                "content_type": "text/markdown"
            }
        ]
        
        # Upload all documents and wait for processing
        document_ids = []
        for doc in documents:
            upload_response = test_client.post("/api/v1/documents/", json=doc)
            assert upload_response.status_code == 200
            
            upload_data = upload_response.json()
            job_id = upload_data["job_id"]
            
            # Wait for processing completion
            max_wait = 35
            start_time = time.time()
            while time.time() - start_time < max_wait:
                status_response = test_client.get(f"/api/v1/documents/status/{job_id}")
                status_data = status_response.json()
                
                if status_data["status"] == "completed":
                    document_ids.append(status_data["result"]["document_id"])
                    break
                elif status_data["status"] == "failed":
                    pytest.fail(f"Document processing failed: {status_data.get('error')}")
                
                await asyncio.sleep(2)
            else:
                pytest.fail("Document processing timeout")
        
        assert len(document_ids) == 3, "All documents should be processed successfully"
        
        # Step 2: Execute complex multi-agent task that requires information from all documents
        complex_task = """
        Analyze the GremlinsAI system comprehensively by examining its technical architecture, 
        business requirements, and risk assessment. Provide a detailed strategic analysis that includes:
        
        1. Technical strengths and potential weaknesses
        2. Market positioning and competitive advantages
        3. Key risks and recommended mitigation strategies
        4. Strategic recommendations for future development
        5. Implementation priorities and timeline suggestions
        
        This analysis should synthesize information from multiple sources and provide insights 
        that go beyond what any single document contains.
        """
        
        # Execute the multi-agent task
        start_time = time.time()
        
        multi_agent_response = test_client.post(
            "/api/v1/multi-agent/execute-task",
            json={
                "task_description": complex_task,
                "workflow_type": "research_analyze_write",
                "context": {
                    "document_ids": document_ids,
                    "analysis_depth": "comprehensive"
                },
                "timeout": 300,
                "save_conversation": False
            }
        )
        
        execution_time = time.time() - start_time
        
        # Step 3: Validate successful multi-agent coordination
        assert multi_agent_response.status_code == 200
        response_data = multi_agent_response.json()
        
        # Validate response structure
        assert "success" in response_data
        assert "result" in response_data
        assert "agents_involved" in response_data
        assert "execution_time" in response_data
        assert "performance_metrics" in response_data
        
        # Validate successful execution
        assert response_data["success"] is True, f"Multi-agent task should succeed: {response_data.get('error_message')}"
        
        # Validate multiple agents were involved
        agents_involved = response_data["agents_involved"]
        assert len(agents_involved) >= 2, f"Multiple agents should be involved: {agents_involved}"
        
        # Expected agents for research_analyze_write workflow
        expected_agents = ["researcher", "analyst", "writer"]
        for expected_agent in expected_agents:
            assert any(expected_agent in agent for agent in agents_involved), f"Expected agent {expected_agent} should be involved"
        
        # Validate context preservation
        assert response_data["context_preserved"] is True, "Context should be preserved between agents"
        
        # Validate performance metrics
        performance_metrics = response_data["performance_metrics"]
        assert "execution_time" in performance_metrics
        assert "agents_involved" in performance_metrics
        assert "inter_agent_communications" in performance_metrics
        assert performance_metrics["success"] is True
        
        # Step 4: Validate result quality and complexity
        result = response_data["result"]
        assert len(result) > 500, "Result should be comprehensive and detailed"
        
        # Check that the result synthesizes information from multiple sources
        technical_keywords = ["architecture", "weaviate", "crewai", "fastapi"]
        business_keywords = ["enterprise", "market", "competitive", "objectives"]
        risk_keywords = ["risk", "mitigation", "security", "compliance"]
        
        result_lower = result.lower()
        
        # Validate technical analysis
        technical_mentions = sum(1 for keyword in technical_keywords if keyword in result_lower)
        assert technical_mentions >= 2, "Result should mention technical aspects"
        
        # Validate business analysis
        business_mentions = sum(1 for keyword in business_keywords if keyword in result_lower)
        assert business_mentions >= 2, "Result should mention business aspects"
        
        # Validate risk analysis
        risk_mentions = sum(1 for keyword in risk_keywords if keyword in result_lower)
        assert risk_mentions >= 2, "Result should mention risk aspects"
        
        # Step 5: Validate performance requirements
        assert execution_time < 300, f"Execution should complete within timeout: {execution_time}s"
        assert response_data["execution_time"] > 0, "Execution time should be recorded"
        
        # Step 6: Test performance monitoring
        performance_response = test_client.get("/api/v1/multi-agent/performance")
        assert performance_response.status_code == 200
        
        performance_data = performance_response.json()
        assert "performance_summary" in performance_data
        assert "active_workflows" in performance_data
        
        performance_summary = performance_data["performance_summary"]
        assert performance_summary["total_tasks"] >= 1
        assert performance_summary["success_rate"] > 0
        
        # Step 7: Test workflow information endpoint
        workflows_response = test_client.get("/api/v1/multi-agent/workflows")
        assert workflows_response.status_code == 200
        
        workflows_data = workflows_response.json()
        assert "available_workflows" in workflows_data
        assert "research_analyze_write" in workflows_data["available_workflows"]
        
        workflow_info = workflows_data["available_workflows"]["research_analyze_write"]
        assert "agents" in workflow_info
        assert "researcher" in workflow_info["agents"]
        assert "analyst" in workflow_info["agents"]
        assert "writer" in workflow_info["agents"]
    
    @pytest.mark.asyncio
    async def test_multi_agent_error_handling(self, test_client: TestClient):
        """Test graceful error handling in multi-agent workflows."""
        # Test with invalid workflow type
        error_response = test_client.post(
            "/api/v1/multi-agent/execute-task",
            json={
                "task_description": "Test task",
                "workflow_type": "invalid_workflow",
                "timeout": 30
            }
        )
        
        assert error_response.status_code == 422
        assert "Invalid workflow_type" in error_response.json()["detail"]
        
        # Test with missing task description
        missing_task_response = test_client.post(
            "/api/v1/multi-agent/execute-task",
            json={
                "workflow_type": "research_analyze_write"
            }
        )
        
        assert missing_task_response.status_code == 422
        assert "task_description is required" in missing_task_response.json()["detail"]
        
        # Test with very short timeout (should trigger timeout handling)
        timeout_response = test_client.post(
            "/api/v1/multi-agent/execute-task",
            json={
                "task_description": "Complex analysis that takes time",
                "workflow_type": "complex_analysis",
                "timeout": 1  # Very short timeout
            }
        )
        
        # Should either complete quickly or handle timeout gracefully
        assert timeout_response.status_code == 200
        timeout_data = timeout_response.json()
        
        if not timeout_data["success"]:
            # If it failed due to timeout, should have appropriate error handling
            assert "timeout" in timeout_data.get("error_message", "").lower() or "fallback" in timeout_data["result"].lower()
    
    @pytest.mark.asyncio
    async def test_multi_agent_workflow_types(self, test_client: TestClient):
        """Test different multi-agent workflow types."""
        test_task = "Analyze the benefits of AI-powered document processing systems."
        
        workflow_types = ["research_analyze_write", "complex_analysis", "collaborative_query"]
        
        for workflow_type in workflow_types:
            response = test_client.post(
                "/api/v1/multi-agent/execute-task",
                json={
                    "task_description": test_task,
                    "workflow_type": workflow_type,
                    "timeout": 120
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Each workflow should complete successfully or provide meaningful fallback
            assert "result" in data
            assert len(data["result"]) > 0
            assert data["workflow_type"] == workflow_type
            
            # Should have performance metrics
            assert "performance_metrics" in data
            assert "execution_time" in data["performance_metrics"]
    
    @pytest.mark.asyncio
    async def test_legacy_endpoint_compatibility(self, test_client: TestClient):
        """Test backward compatibility with legacy multi-agent endpoint."""
        legacy_response = test_client.post(
            "/api/v1/multi-agent/execute",
            json={
                "input": "What are the key features of GremlinsAI?",
                "workflow_type": "research_analyze_write",
                "context": "Technical documentation analysis",
                "save_conversation": False
            }
        )
        
        assert legacy_response.status_code == 200
        legacy_data = legacy_response.json()
        
        # Should have the same structure as new endpoint
        assert "success" in legacy_data
        assert "result" in legacy_data
        assert "agents_involved" in legacy_data


if __name__ == "__main__":
    pytest.main([__file__])
