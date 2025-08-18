# tests/performance/test_load_performance.py
"""
Performance and load tests for GremlinsAI.

These tests verify that the system meets performance requirements
under various load conditions and stress scenarios.
"""

import pytest
import asyncio
import time
import statistics
import psutil
import threading
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.database.database import get_db


class TestLoadPerformance:
    """Performance and load testing suite."""

    @pytest.fixture(autouse=True)
    async def setup_test_app(self, test_db_session: AsyncSession):
        """Set up test application with real database."""
        async def override_get_db():
            yield test_db_session
        
        app.dependency_overrides[get_db] = override_get_db
        yield
        app.dependency_overrides.clear()

    def measure_system_resources(self) -> Dict[str, float]:
        """Measure current system resource usage."""
        process = psutil.Process()
        return {
            "cpu_percent": process.cpu_percent(),
            "memory_mb": process.memory_info().rss / 1024 / 1024,
            "memory_percent": process.memory_percent(),
            "threads": process.num_threads()
        }

    @pytest.mark.asyncio
    async def test_concurrent_document_creation(self, test_client: TestClient, performance_test_config: Dict[str, Any]):
        """Test concurrent document creation performance."""
        concurrent_users = performance_test_config["concurrent_users"]
        requests_per_user = performance_test_config["requests_per_user"]
        max_response_time = performance_test_config["max_response_time"]
        
        def create_document(user_id: int, doc_id: int) -> Dict[str, Any]:
            """Create a single document and measure performance."""
            start_time = time.time()
            start_resources = self.measure_system_resources()
            
            document_data = {
                "title": f"Performance Test Doc {user_id}-{doc_id}",
                "content": f"This is a performance test document created by user {user_id}, document {doc_id}. " * 50,
                "content_type": "text/plain",
                "tags": [f"perf-test-{user_id}", f"doc-{doc_id}", "performance"]
            }
            
            try:
                response = test_client.post("/api/v1/documents/", json=document_data)
                response_time = time.time() - start_time
                end_resources = self.measure_system_resources()
                
                return {
                    "success": response.status_code == 200,
                    "response_time": response_time,
                    "status_code": response.status_code,
                    "user_id": user_id,
                    "doc_id": doc_id,
                    "cpu_delta": end_resources["cpu_percent"] - start_resources["cpu_percent"],
                    "memory_delta": end_resources["memory_mb"] - start_resources["memory_mb"]
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "response_time": time.time() - start_time,
                    "user_id": user_id,
                    "doc_id": doc_id
                }
        
        # Execute concurrent document creation
        results = []
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = []
            
            for user_id in range(concurrent_users):
                for doc_id in range(requests_per_user):
                    future = executor.submit(create_document, user_id, doc_id)
                    futures.append(future)
            
            for future in as_completed(futures):
                results.append(future.result())
        
        # Analyze results
        successful_requests = [r for r in results if r["success"]]
        failed_requests = [r for r in results if not r["success"]]
        
        success_rate = len(successful_requests) / len(results)
        response_times = [r["response_time"] for r in successful_requests]
        
        # Performance assertions
        assert success_rate >= performance_test_config["success_rate_threshold"]
        assert statistics.mean(response_times) <= max_response_time
        assert statistics.median(response_times) <= max_response_time * 0.8
        assert max(response_times) <= max_response_time * 2  # 95th percentile allowance
        
        # Resource usage assertions
        avg_memory_delta = statistics.mean([r.get("memory_delta", 0) for r in successful_requests])
        assert avg_memory_delta <= performance_test_config["memory_limit_mb"]
        
        return {
            "total_requests": len(results),
            "successful_requests": len(successful_requests),
            "failed_requests": len(failed_requests),
            "success_rate": success_rate,
            "avg_response_time": statistics.mean(response_times),
            "median_response_time": statistics.median(response_times),
            "max_response_time": max(response_times),
            "min_response_time": min(response_times),
            "avg_memory_delta": avg_memory_delta
        }

    @pytest.mark.asyncio
    async def test_concurrent_search_performance(self, test_client: TestClient, sample_document_content: str, performance_test_config: Dict[str, Any]):
        """Test concurrent search performance."""
        # First, create test documents
        document_ids = []
        for i in range(5):
            doc_data = {
                "title": f"Search Performance Test Doc {i}",
                "content": f"{sample_document_content}\n\nDocument ID: {i}",
                "content_type": "text/markdown",
                "tags": [f"search-perf-{i}", "performance"]
            }
            
            response = test_client.post("/api/v1/documents/", json=doc_data)
            assert response.status_code == 200
            document_ids.append(response.json()["id"])
        
        time.sleep(2)  # Wait for indexing
        
        def perform_search(search_id: int) -> Dict[str, Any]:
            """Perform a single search and measure performance."""
            queries = [
                "What is GremlinsAI?",
                "How does the architecture work?",
                "What are the main features?",
                "How to get started?",
                "What databases are used?"
            ]
            
            query = queries[search_id % len(queries)]
            start_time = time.time()
            
            search_data = {
                "query": query,
                "limit": 5,
                "similarity_threshold": 0.6
            }
            
            try:
                response = test_client.post("/api/v1/documents/search", json=search_data)
                response_time = time.time() - start_time
                
                return {
                    "success": response.status_code == 200,
                    "response_time": response_time,
                    "results_count": len(response.json().get("results", [])) if response.status_code == 200 else 0,
                    "search_id": search_id,
                    "query": query
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "response_time": time.time() - start_time,
                    "search_id": search_id
                }
        
        # Execute concurrent searches
        concurrent_searches = 20
        results = []
        
        with ThreadPoolExecutor(max_workers=concurrent_searches) as executor:
            futures = [executor.submit(perform_search, i) for i in range(concurrent_searches)]
            
            for future in as_completed(futures):
                results.append(future.result())
        
        # Analyze search performance
        successful_searches = [r for r in results if r["success"]]
        success_rate = len(successful_searches) / len(results)
        response_times = [r["response_time"] for r in successful_searches]
        
        assert success_rate >= 0.95  # 95% success rate for searches
        assert statistics.mean(response_times) <= 1.5  # Average under 1.5 seconds
        assert max(response_times) <= 3.0  # Max under 3 seconds
        
        return {
            "concurrent_searches": concurrent_searches,
            "success_rate": success_rate,
            "avg_response_time": statistics.mean(response_times),
            "max_response_time": max(response_times),
            "avg_results_count": statistics.mean([r.get("results_count", 0) for r in successful_searches])
        }

    @pytest.mark.asyncio
    async def test_rag_query_performance(self, test_client: TestClient, sample_document_content: str):
        """Test RAG query performance under load."""
        # Create test document
        doc_data = {
            "title": "RAG Performance Test Document",
            "content": sample_document_content,
            "content_type": "text/markdown",
            "tags": ["rag-performance", "test"]
        }
        
        response = test_client.post("/api/v1/documents/", json=doc_data)
        assert response.status_code == 200
        
        time.sleep(2)  # Wait for indexing
        
        def perform_rag_query(query_id: int) -> Dict[str, Any]:
            """Perform a single RAG query and measure performance."""
            queries = [
                "What is GremlinsAI and what does it do?",
                "Explain the architecture of GremlinsAI",
                "What are the key features and capabilities?",
                "How do I get started with GremlinsAI?",
                "What technologies does GremlinsAI use?"
            ]
            
            query = queries[query_id % len(queries)]
            start_time = time.time()
            
            with patch('app.core.production_llm_manager.ChatOllama') as mock_ollama:
                # Mock LLM response for consistent testing
                mock_response = type('MockResponse', (), {})()
                mock_response.content = f"Based on the provided context, here's what I can tell you about {query}: GremlinsAI is a comprehensive AI system designed for document processing and intelligent query answering."
                
                mock_llm = mock_ollama.return_value
                mock_llm.ainvoke.return_value = mock_response
                
                rag_data = {
                    "query": query,
                    "max_results": 3,
                    "similarity_threshold": 0.6,
                    "include_sources": True
                }
                
                try:
                    response = test_client.post("/api/v1/documents/rag", json=rag_data)
                    response_time = time.time() - start_time
                    
                    result_data = response.json() if response.status_code == 200 else {}
                    
                    return {
                        "success": response.status_code == 200,
                        "response_time": response_time,
                        "answer_length": len(result_data.get("answer", "")),
                        "sources_count": len(result_data.get("sources", [])),
                        "query_id": query_id,
                        "query": query
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "error": str(e),
                        "response_time": time.time() - start_time,
                        "query_id": query_id
                    }
        
        # Execute concurrent RAG queries
        concurrent_queries = 10
        results = []
        
        with ThreadPoolExecutor(max_workers=concurrent_queries) as executor:
            futures = [executor.submit(perform_rag_query, i) for i in range(concurrent_queries)]
            
            for future in as_completed(futures):
                results.append(future.result())
        
        # Analyze RAG performance
        successful_queries = [r for r in results if r["success"]]
        success_rate = len(successful_queries) / len(results)
        response_times = [r["response_time"] for r in successful_queries]
        
        assert success_rate >= 0.9  # 90% success rate for RAG
        assert statistics.mean(response_times) <= 3.0  # Average under 3 seconds
        assert max(response_times) <= 5.0  # Max under 5 seconds
        
        return {
            "concurrent_rag_queries": concurrent_queries,
            "success_rate": success_rate,
            "avg_response_time": statistics.mean(response_times),
            "max_response_time": max(response_times),
            "avg_answer_length": statistics.mean([r.get("answer_length", 0) for r in successful_queries]),
            "avg_sources_count": statistics.mean([r.get("sources_count", 0) for r in successful_queries])
        }

    @pytest.mark.asyncio
    async def test_memory_usage_stability(self, test_client: TestClient):
        """Test memory usage stability over time."""
        initial_memory = self.measure_system_resources()["memory_mb"]
        memory_measurements = [initial_memory]
        
        # Perform various operations and monitor memory
        for i in range(20):
            # Create document
            doc_data = {
                "title": f"Memory Test Doc {i}",
                "content": f"Memory stability test document {i}. " * 100,
                "content_type": "text/plain"
            }
            
            response = test_client.post("/api/v1/documents/", json=doc_data)
            assert response.status_code == 200
            
            # Perform search
            search_data = {
                "query": f"memory test {i}",
                "limit": 3
            }
            
            test_client.post("/api/v1/documents/search", json=search_data)
            
            # Measure memory
            current_memory = self.measure_system_resources()["memory_mb"]
            memory_measurements.append(current_memory)
            
            time.sleep(0.1)  # Small delay
        
        # Analyze memory stability
        memory_growth = memory_measurements[-1] - memory_measurements[0]
        max_memory = max(memory_measurements)
        
        # Memory should not grow excessively (allow 100MB growth)
        assert memory_growth <= 100, f"Memory grew by {memory_growth:.2f}MB"
        assert max_memory <= initial_memory + 150, f"Peak memory usage too high: {max_memory:.2f}MB"
        
        return {
            "initial_memory_mb": initial_memory,
            "final_memory_mb": memory_measurements[-1],
            "memory_growth_mb": memory_growth,
            "max_memory_mb": max_memory,
            "measurements": memory_measurements
        }


if __name__ == "__main__":
    pytest.main([__file__])
