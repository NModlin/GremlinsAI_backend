# tests/integration/test_api_endpoints.py
"""
Integration tests for GremlinsAI API endpoints.

These tests run against real services (Weaviate, database) to ensure
end-to-end functionality works correctly. Following prometheus.md specifications
for comprehensive testing framework.
"""

import pytest
import asyncio
import json
import time
from typing import Dict, Any
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.database.database import get_db
from app.api.v1.schemas.documents import DocumentCreate, RAGRequest
from app.api.v1.schemas.chat_history import AgentConversationRequest


class TestAPIEndpoints:
    """Integration tests for core API endpoints."""

    @pytest.fixture(autouse=True)
    async def setup_test_app(self, test_db_session: AsyncSession):
        """Set up test application with real database."""
        async def override_get_db():
            yield test_db_session
        
        app.dependency_overrides[get_db] = override_get_db
        yield
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_health_endpoint(self, test_client: TestClient):
        """Test health check endpoint."""
        response = test_client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_document_upload_and_retrieval(self, test_client: TestClient, sample_document_content: str):
        """Test document upload and retrieval workflow."""
        # Test document creation
        document_data = {
            "title": "Test Document",
            "content": sample_document_content,
            "content_type": "text/markdown",
            "tags": ["test", "documentation"]
        }
        
        response = test_client.post("/api/v1/documents/", json=document_data)
        assert response.status_code == 200
        
        created_doc = response.json()
        assert "id" in created_doc
        assert created_doc["title"] == "Test Document"
        assert created_doc["content_type"] == "text/markdown"
        document_id = created_doc["id"]
        
        # Test document retrieval
        response = test_client.get(f"/api/v1/documents/{document_id}")
        assert response.status_code == 200
        
        retrieved_doc = response.json()
        assert retrieved_doc["id"] == document_id
        assert retrieved_doc["title"] == "Test Document"
        
        # Test document listing
        response = test_client.get("/api/v1/documents/")
        assert response.status_code == 200
        
        docs_list = response.json()
        assert "documents" in docs_list
        assert len(docs_list["documents"]) >= 1
        
        return document_id

    @pytest.mark.asyncio
    async def test_semantic_search(self, test_client: TestClient, sample_document_content: str):
        """Test semantic search functionality."""
        # First create a document
        document_data = {
            "title": "Search Test Document",
            "content": sample_document_content,
            "content_type": "text/markdown",
            "tags": ["search", "test"]
        }
        
        response = test_client.post("/api/v1/documents/", json=document_data)
        assert response.status_code == 200
        
        # Wait a moment for indexing
        time.sleep(1)
        
        # Test semantic search
        search_data = {
            "query": "What is GremlinsAI?",
            "limit": 5,
            "similarity_threshold": 0.7
        }
        
        response = test_client.post("/api/v1/documents/search", json=search_data)
        assert response.status_code == 200
        
        search_results = response.json()
        assert "results" in search_results
        assert isinstance(search_results["results"], list)

    @pytest.mark.asyncio
    async def test_agent_rag_query(self, test_client: TestClient, test_weaviate_container, sample_document_content: str):
        """
        Test full RAG pipeline with real Weaviate instance.
        This is the core integration test following prometheus.md template.
        """
        # Step 1: Upload test document
        document_data = {
            "title": "RAG Test Document",
            "content": sample_document_content,
            "content_type": "text/markdown",
            "tags": ["rag", "test", "integration"]
        }
        
        response = test_client.post("/api/v1/documents/", json=document_data)
        assert response.status_code == 200
        document_id = response.json()["id"]
        
        # Wait for document processing and indexing
        time.sleep(2)
        
        # Step 2: Perform RAG query
        rag_data = {
            "query": "What are the main features of GremlinsAI?",
            "max_results": 3,
            "similarity_threshold": 0.7,
            "include_sources": True
        }
        
        with patch('app.core.production_llm_manager.ChatOllama') as mock_ollama:
            # Mock LLM response for consistent testing
            mock_response = type('MockResponse', (), {})()
            mock_response.content = "Based on the provided context, GremlinsAI is a production-ready AI agent system with the following main features: intelligent document processing, multi-modal content understanding, real-time collaboration, and advanced RAG capabilities."
            
            mock_llm = mock_ollama.return_value
            mock_llm.ainvoke.return_value = mock_response
            
            response = test_client.post("/api/v1/documents/rag", json=rag_data)
        
        # Step 3: Validate response
        assert response.status_code == 200
        
        rag_result = response.json()
        assert "answer" in rag_result
        assert "sources" in rag_result
        assert "query" in rag_result
        
        # Validate answer quality
        answer = rag_result["answer"]
        assert len(answer) > 50  # Substantial response
        assert "GremlinsAI" in answer
        assert any(feature in answer.lower() for feature in ["document", "processing", "features"])
        
        # Validate sources
        sources = rag_result["sources"]
        assert isinstance(sources, list)
        assert len(sources) > 0
        
        # Validate source structure
        for source in sources:
            assert "content" in source
            assert "similarity_score" in source
            assert source["similarity_score"] >= 0.7  # Above threshold

    @pytest.mark.asyncio
    async def test_agent_conversation(self, test_client: TestClient, mock_ollama_service):
        """Test agent conversation endpoint."""
        conversation_data = {
            "message": "Hello, can you help me understand what GremlinsAI does?",
            "conversation_id": "test-conversation-001",
            "user_id": "test-user",
            "context": {
                "session_id": "test-session",
                "user_preferences": {"response_style": "detailed"}
            }
        }
        
        response = test_client.post("/api/v1/agent/chat", json=conversation_data)
        assert response.status_code == 200
        
        chat_result = response.json()
        assert "response" in chat_result
        assert "conversation_id" in chat_result
        assert "timestamp" in chat_result
        
        # Validate response structure
        agent_response = chat_result["response"]
        assert len(agent_response) > 10  # Non-empty response
        assert chat_result["conversation_id"] == "test-conversation-001"

    @pytest.mark.asyncio
    async def test_system_status(self, test_client: TestClient):
        """Test system status endpoint."""
        response = test_client.get("/api/v1/documents/system/status")
        assert response.status_code == 200
        
        status = response.json()
        assert "database_status" in status
        assert "vector_store_status" in status
        assert "llm_status" in status
        
        # Validate status structure
        assert isinstance(status["database_status"], str)
        assert isinstance(status["vector_store_status"], str)
        assert isinstance(status["llm_status"], str)

    @pytest.mark.asyncio
    async def test_query_suggestions(self, test_client: TestClient, sample_document_content: str):
        """Test query suggestions functionality."""
        # First create a document
        document_data = {
            "title": "Suggestions Test Document",
            "content": sample_document_content,
            "content_type": "text/markdown"
        }
        
        response = test_client.post("/api/v1/documents/", json=document_data)
        assert response.status_code == 200
        
        # Test query suggestions
        suggestions_data = {
            "partial_query": "What is",
            "limit": 5
        }
        
        response = test_client.post("/api/v1/documents/suggestions", json=suggestions_data)
        assert response.status_code == 200
        
        suggestions = response.json()
        assert "suggestions" in suggestions
        assert isinstance(suggestions["suggestions"], list)

    @pytest.mark.asyncio
    async def test_error_handling(self, test_client: TestClient):
        """Test API error handling."""
        # Test invalid document ID
        response = test_client.get("/api/v1/documents/invalid-id")
        assert response.status_code == 404
        
        # Test invalid JSON in request
        response = test_client.post(
            "/api/v1/documents/",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, test_client: TestClient, sample_document_content: str):
        """Test handling of concurrent requests."""
        # Create multiple documents concurrently
        async def create_document(index: int):
            document_data = {
                "title": f"Concurrent Test Document {index}",
                "content": f"{sample_document_content}\n\nDocument ID: {index}",
                "content_type": "text/markdown",
                "tags": [f"concurrent-{index}", "test"]
            }
            
            response = test_client.post("/api/v1/documents/", json=document_data)
            return response.status_code == 200, response.json()
        
        # Run 10 concurrent document creations
        tasks = [create_document(i) for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Validate all requests succeeded
        successful_requests = sum(1 for success, _ in results if success)
        assert successful_requests >= 8  # Allow for some potential failures in test environment

    @pytest.mark.asyncio
    async def test_response_times(self, test_client: TestClient):
        """Test API response times meet performance requirements."""
        endpoints_to_test = [
            ("/api/v1/health", "GET"),
            ("/api/v1/documents/", "GET"),
            ("/api/v1/documents/system/status", "GET")
        ]
        
        for endpoint, method in endpoints_to_test:
            start_time = time.time()
            
            if method == "GET":
                response = test_client.get(endpoint)
            else:
                response = test_client.post(endpoint, json={})
            
            response_time = time.time() - start_time
            
            # API responses should be under 2 seconds
            assert response_time < 2.0, f"{endpoint} took {response_time:.2f}s"
            assert response.status_code in [200, 422]  # 422 for invalid POST data is acceptable

    @pytest.mark.asyncio
    async def test_rag_query_endpoint(self, test_client: TestClient):
        """
        Test RAG query endpoint following the established integration testing pattern.

        This test:
        1. Starts a test Weaviate container (handled by test fixtures)
        2. Uploads a known document through the API
        3. Sends a query to the new /rag-query endpoint that can only be answered using the document
        4. Asserts that the response is successful, answer is correct, and sources cite the document
        """
        # Step 1: Upload a test document with specific content
        test_content = """
        The GremlinsAI system is a production-ready artificial intelligence platform
        that specializes in retrieval-augmented generation (RAG). It uses Weaviate
        as its vector database to store and retrieve document embeddings. The system
        can process natural language queries and provide accurate, context-aware responses
        by combining semantic search with large language model generation.

        Key features include:
        - Semantic search with >0.8 similarity scores
        - Sub-2-second query response times
        - Proper citation of source documents
        - Confidence scoring for answer quality
        """

        upload_response = test_client.post(
            "/api/v1/documents/",
            json={
                "title": "GremlinsAI System Documentation",
                "content": test_content,
                "content_type": "text/plain",
                "metadata": {"category": "documentation", "system": "gremlinsai"}
            }
        )

        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        assert "id" in upload_data
        document_id = upload_data["id"]

        # Step 2: Wait for document indexing in Weaviate
        await asyncio.sleep(3)  # Allow time for embedding generation and indexing

        # Step 3: Send a query that can only be answered using the uploaded document
        rag_query = "What vector database does GremlinsAI use and what are its key features?"

        rag_response = test_client.post(
            "/api/v1/documents/rag-query",
            json={
                "query": rag_query,
                "search_limit": 5,
                "score_threshold": 0.7,
                "use_multi_agent": False,
                "save_conversation": False
            }
        )

        # Step 4: Assert successful response
        assert rag_response.status_code == 200
        rag_data = rag_response.json()

        # Verify response structure
        assert "query" in rag_data
        assert "answer" in rag_data
        assert "sources" in rag_data
        assert "context_used" in rag_data
        assert "confidence" in rag_data
        assert "query_time" in rag_data

        # Verify query matches
        assert rag_data["query"] == rag_query

        # Verify answer correctness - should mention Weaviate
        answer = rag_data["answer"].lower()
        assert "weaviate" in answer, f"Answer should mention Weaviate: {rag_data['answer']}"

        # Verify context was used
        assert rag_data["context_used"] is True, "RAG should use retrieved context"

        # Verify sources cite the uploaded document
        sources = rag_data["sources"]
        assert len(sources) > 0, "RAG response should include source citations"

        # Check that at least one source is our uploaded document
        found_source_document = False
        for source in sources:
            if source["document_id"] == document_id:
                found_source_document = True
                assert source["score"] > 0.7, f"Source similarity score should be >0.7: {source['score']}"
                break

        assert found_source_document, "RAG sources should include the uploaded document"

        # Verify confidence score meets requirements
        confidence = rag_data["confidence"]
        assert confidence > 0.8, f"Confidence score should be >0.8: {confidence}"

        # Verify query response time meets requirements (<2 seconds)
        query_time_ms = rag_data["query_time"]
        assert query_time_ms < 2000, f"Query time should be <2000ms: {query_time_ms}ms"

        # Verify search metadata
        search_metadata = rag_data.get("search_metadata", {})
        assert "total_chunks" in search_metadata
        assert search_metadata["total_chunks"] > 0


if __name__ == "__main__":
    pytest.main([__file__])
