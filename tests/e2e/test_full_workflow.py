# tests/e2e/test_full_workflow.py
"""
End-to-end tests for GremlinsAI full user workflows.

These tests simulate complete user journeys from start to finish,
testing the entire application stack including API, database, and services.
"""

import pytest
import asyncio
import time
import json
from typing import Dict, List, Any
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.database.database import get_db


class TestFullWorkflow:
    """End-to-end workflow tests."""

    @pytest.fixture(autouse=True)
    async def setup_test_app(self, test_db_session: AsyncSession):
        """Set up test application with real database."""
        async def override_get_db():
            yield test_db_session
        
        app.dependency_overrides[get_db] = override_get_db
        yield
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_complete_document_workflow(self, test_client: TestClient, sample_document_content: str, sample_test_queries: List[str]):
        """
        Test complete document workflow:
        1. Upload document
        2. Verify document processing
        3. Perform semantic search
        4. Execute RAG queries
        5. Get analytics
        """
        workflow_results = {}
        
        # Step 1: Upload document
        document_data = {
            "title": "E2E Test Document - Complete Workflow",
            "content": sample_document_content,
            "content_type": "text/markdown",
            "tags": ["e2e", "workflow", "test", "complete"]
        }
        
        response = test_client.post("/api/v1/documents/", json=document_data)
        assert response.status_code == 200
        
        document = response.json()
        document_id = document["id"]
        workflow_results["document_created"] = True
        workflow_results["document_id"] = document_id
        
        # Step 2: Verify document processing (wait for indexing)
        time.sleep(2)
        
        response = test_client.get(f"/api/v1/documents/{document_id}")
        assert response.status_code == 200
        
        retrieved_doc = response.json()
        assert retrieved_doc["title"] == document_data["title"]
        workflow_results["document_retrieved"] = True
        
        # Step 3: Perform semantic search
        search_results = []
        for query in sample_test_queries[:3]:  # Test first 3 queries
            search_data = {
                "query": query,
                "limit": 5,
                "similarity_threshold": 0.6
            }
            
            response = test_client.post("/api/v1/documents/search", json=search_data)
            assert response.status_code == 200
            
            search_result = response.json()
            search_results.append({
                "query": query,
                "results_count": len(search_result.get("results", [])),
                "success": True
            })
        
        workflow_results["semantic_searches"] = search_results
        workflow_results["search_success_rate"] = sum(1 for r in search_results if r["success"]) / len(search_results)
        
        # Step 4: Execute RAG queries
        rag_results = []
        
        with patch('app.core.production_llm_manager.ChatOllama') as mock_ollama:
            # Mock LLM responses for consistent testing
            mock_responses = [
                "GremlinsAI is a production-ready AI agent system designed for intelligent document processing and multi-modal content understanding.",
                "The architecture uses a microservices approach with FastAPI backend, Weaviate vector database, Redis caching, and Ollama for local LLM inference.",
                "The main features include intelligent document processing, multi-modal content understanding, real-time collaboration, and advanced RAG capabilities.",
                "To get started: 1) Install dependencies, 2) Configure environment variables, 3) Start the services, 4) Upload your first document.",
                "The system uses Weaviate as the vector database and Redis as the caching layer for optimal performance."
            ]
            
            mock_response_iter = iter(mock_responses)
            
            def mock_ainvoke(*args, **kwargs):
                response = type('MockResponse', (), {})()
                response.content = next(mock_response_iter, mock_responses[0])
                return response
            
            mock_llm = mock_ollama.return_value
            mock_llm.ainvoke.side_effect = mock_ainvoke
            
            for query in sample_test_queries:
                rag_data = {
                    "query": query,
                    "max_results": 3,
                    "similarity_threshold": 0.6,
                    "include_sources": True
                }
                
                start_time = time.time()
                response = test_client.post("/api/v1/documents/rag", json=rag_data)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    rag_result = response.json()
                    rag_results.append({
                        "query": query,
                        "answer_length": len(rag_result.get("answer", "")),
                        "sources_count": len(rag_result.get("sources", [])),
                        "response_time": response_time,
                        "success": True
                    })
                else:
                    rag_results.append({
                        "query": query,
                        "success": False,
                        "error": response.text
                    })
        
        workflow_results["rag_queries"] = rag_results
        workflow_results["rag_success_rate"] = sum(1 for r in rag_results if r.get("success", False)) / len(rag_results)
        workflow_results["avg_rag_response_time"] = sum(r.get("response_time", 0) for r in rag_results if r.get("success", False)) / max(1, sum(1 for r in rag_results if r.get("success", False)))
        
        # Step 5: Get system analytics
        response = test_client.get("/api/v1/documents/analytics/search?days_back=1")
        if response.status_code == 200:
            analytics = response.json()
            workflow_results["analytics_retrieved"] = True
            workflow_results["analytics_data"] = analytics
        else:
            workflow_results["analytics_retrieved"] = False
        
        # Validate overall workflow success
        assert workflow_results["document_created"]
        assert workflow_results["document_retrieved"]
        assert workflow_results["search_success_rate"] >= 0.8  # 80% success rate
        assert workflow_results["rag_success_rate"] >= 0.8  # 80% success rate
        assert workflow_results["avg_rag_response_time"] < 3.0  # Under 3 seconds
        
        return workflow_results

    @pytest.mark.asyncio
    async def test_multi_user_collaboration_workflow(self, test_client: TestClient, sample_document_content: str):
        """
        Test multi-user collaboration workflow:
        1. User A uploads document
        2. User B searches and queries
        3. User A and B have conversations
        4. Verify shared access and history
        """
        # User A uploads document
        user_a_doc = {
            "title": "Collaboration Test Document",
            "content": sample_document_content,
            "content_type": "text/markdown",
            "tags": ["collaboration", "multi-user", "test"]
        }
        
        response = test_client.post("/api/v1/documents/", json=user_a_doc)
        assert response.status_code == 200
        document_id = response.json()["id"]
        
        time.sleep(1)  # Wait for processing
        
        # User B searches the document
        search_data = {
            "query": "What is GremlinsAI?",
            "limit": 3
        }
        
        response = test_client.post("/api/v1/documents/search", json=search_data)
        assert response.status_code == 200
        search_results = response.json()
        assert len(search_results.get("results", [])) > 0
        
        # User A starts conversation
        with patch('app.core.production_llm_manager.ChatOllama') as mock_ollama:
            mock_response = type('MockResponse', (), {})()
            mock_response.content = "Hello! I'm here to help you with GremlinsAI. What would you like to know?"
            
            mock_llm = mock_ollama.return_value
            mock_llm.ainvoke.return_value = mock_response
            
            user_a_conversation = {
                "message": "Hello, I just uploaded a document about GremlinsAI",
                "conversation_id": "collab-user-a-001",
                "user_id": "user-a",
                "context": {"session_id": "session-a"}
            }
            
            response = test_client.post("/api/v1/agent/chat", json=user_a_conversation)
            assert response.status_code == 200
            
            # User B starts separate conversation
            user_b_conversation = {
                "message": "I found a document about GremlinsAI, can you tell me more?",
                "conversation_id": "collab-user-b-001",
                "user_id": "user-b",
                "context": {"session_id": "session-b"}
            }
            
            response = test_client.post("/api/v1/agent/chat", json=user_b_conversation)
            assert response.status_code == 200
        
        # Verify both users can access the document
        response = test_client.get(f"/api/v1/documents/{document_id}")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, test_client: TestClient):
        """
        Test error recovery and resilience:
        1. Attempt invalid operations
        2. Verify graceful error handling
        3. Verify system remains functional
        """
        # Test invalid document upload
        invalid_doc = {
            "title": "",  # Invalid: empty title
            "content": "",  # Invalid: empty content
            "content_type": "invalid/type"  # Invalid content type
        }
        
        response = test_client.post("/api/v1/documents/", json=invalid_doc)
        assert response.status_code == 422  # Validation error
        
        # Test invalid document ID access
        response = test_client.get("/api/v1/documents/nonexistent-id")
        assert response.status_code == 404
        
        # Test invalid search query
        invalid_search = {
            "query": "",  # Empty query
            "limit": -1,  # Invalid limit
            "similarity_threshold": 2.0  # Invalid threshold (>1.0)
        }
        
        response = test_client.post("/api/v1/documents/search", json=invalid_search)
        assert response.status_code == 422
        
        # Verify system is still functional after errors
        response = test_client.get("/api/v1/health")
        assert response.status_code == 200
        
        # Verify valid operations still work
        valid_doc = {
            "title": "Recovery Test Document",
            "content": "This document tests system recovery after errors.",
            "content_type": "text/plain",
            "tags": ["recovery", "test"]
        }
        
        response = test_client.post("/api/v1/documents/", json=valid_doc)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_performance_under_load(self, test_client: TestClient, sample_document_content: str):
        """
        Test system performance under load:
        1. Create multiple documents
        2. Perform concurrent searches
        3. Execute concurrent RAG queries
        4. Verify performance metrics
        """
        # Create multiple documents
        document_ids = []
        for i in range(5):
            doc_data = {
                "title": f"Load Test Document {i}",
                "content": f"{sample_document_content}\n\nDocument number: {i}",
                "content_type": "text/markdown",
                "tags": [f"load-test-{i}", "performance"]
            }
            
            response = test_client.post("/api/v1/documents/", json=doc_data)
            assert response.status_code == 200
            document_ids.append(response.json()["id"])
        
        time.sleep(2)  # Wait for indexing
        
        # Perform concurrent searches
        async def perform_search(query_index: int):
            search_data = {
                "query": f"What is document {query_index}?",
                "limit": 3
            }
            
            start_time = time.time()
            response = test_client.post("/api/v1/documents/search", json=search_data)
            response_time = time.time() - start_time
            
            return {
                "success": response.status_code == 200,
                "response_time": response_time,
                "query_index": query_index
            }
        
        # Run 10 concurrent searches
        search_tasks = [perform_search(i) for i in range(10)]
        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # Validate performance
        successful_searches = [r for r in search_results if isinstance(r, dict) and r.get("success")]
        success_rate = len(successful_searches) / len(search_results)
        avg_response_time = sum(r["response_time"] for r in successful_searches) / len(successful_searches)
        
        assert success_rate >= 0.9  # 90% success rate
        assert avg_response_time < 2.0  # Under 2 seconds average
        
        # Test concurrent RAG queries
        with patch('app.core.production_llm_manager.ChatOllama') as mock_ollama:
            mock_response = type('MockResponse', (), {})()
            mock_response.content = "This is a test response for load testing."
            
            mock_llm = mock_ollama.return_value
            mock_llm.ainvoke.return_value = mock_response
            
            async def perform_rag_query(query_index: int):
                rag_data = {
                    "query": f"Tell me about document {query_index}",
                    "max_results": 2,
                    "include_sources": True
                }
                
                start_time = time.time()
                response = test_client.post("/api/v1/documents/rag", json=rag_data)
                response_time = time.time() - start_time
                
                return {
                    "success": response.status_code == 200,
                    "response_time": response_time,
                    "query_index": query_index
                }
            
            # Run 5 concurrent RAG queries
            rag_tasks = [perform_rag_query(i) for i in range(5)]
            rag_results = await asyncio.gather(*rag_tasks, return_exceptions=True)
            
            # Validate RAG performance
            successful_rag = [r for r in rag_results if isinstance(r, dict) and r.get("success")]
            rag_success_rate = len(successful_rag) / len(rag_results)
            avg_rag_time = sum(r["response_time"] for r in successful_rag) / len(successful_rag)
            
            assert rag_success_rate >= 0.8  # 80% success rate for RAG
            assert avg_rag_time < 5.0  # Under 5 seconds for RAG queries


if __name__ == "__main__":
    pytest.main([__file__])
