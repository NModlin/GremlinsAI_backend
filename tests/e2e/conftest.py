"""
End-to-End Test Configuration - Task T3.3

This module provides configuration and fixtures for end-to-end tests
that simulate complete user workflows against live staging environments.

Features:
- Staging environment configuration
- Real HTTP client setup
- Test data management
- Performance monitoring
- Error handling and recovery
- Cross-workflow test utilities
"""

import pytest
import asyncio
import os
import time
import httpx
from typing import Dict, Any, List, Optional
from pathlib import Path


# E2E Test Configuration
E2E_CONFIG = {
    "base_url": os.getenv("E2E_BASE_URL", "http://localhost:8000"),
    "timeout": float(os.getenv("E2E_TIMEOUT", "30.0")),
    "max_retries": int(os.getenv("E2E_MAX_RETRIES", "3")),
    "retry_delay": float(os.getenv("E2E_RETRY_DELAY", "1.0")),
    "staging_health_check": os.getenv("E2E_HEALTH_CHECK", "true").lower() == "true",
    "performance_monitoring": os.getenv("E2E_PERFORMANCE", "true").lower() == "true",
    "verbose_logging": os.getenv("E2E_VERBOSE", "false").lower() == "true"
}


class E2ETestClient:
    """Enhanced HTTP client for end-to-end testing with retry logic and monitoring."""
    
    def __init__(self, base_url: str = None, timeout: float = None):
        self.base_url = base_url or E2E_CONFIG["base_url"]
        self.timeout = timeout or E2E_CONFIG["timeout"]
        self.max_retries = E2E_CONFIG["max_retries"]
        self.retry_delay = E2E_CONFIG["retry_delay"]
        self.session_data = {}
        self.performance_metrics = []
        
    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "GremlinsAI-E2E-Tests/1.0",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def _make_request_with_retry(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        """Make HTTP request with retry logic and performance monitoring."""
        start_time = time.time()
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                if E2E_CONFIG["verbose_logging"]:
                    print(f"🔍 {method} {endpoint} (attempt {attempt + 1})")
                
                response = await getattr(self.client, method.lower())(endpoint, **kwargs)
                
                # Record performance metrics
                end_time = time.time()
                self.performance_metrics.append({
                    "method": method,
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "response_time": end_time - start_time,
                    "attempt": attempt + 1,
                    "timestamp": start_time
                })
                
                return response
                
            except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError) as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    if E2E_CONFIG["verbose_logging"]:
                        print(f"⚠️  Request failed (attempt {attempt + 1}): {e}")
                        print(f"   Retrying in {self.retry_delay}s...")
                    
                    await asyncio.sleep(self.retry_delay)
                    continue
                else:
                    # Record failed request
                    end_time = time.time()
                    self.performance_metrics.append({
                        "method": method,
                        "endpoint": endpoint,
                        "status_code": None,
                        "response_time": end_time - start_time,
                        "attempt": attempt + 1,
                        "error": str(e),
                        "timestamp": start_time
                    })
                    
                    raise last_exception
        
        raise last_exception
    
    async def post(self, endpoint: str, json_data: Dict[str, Any] = None, **kwargs) -> httpx.Response:
        """Make POST request with retry logic."""
        return await self._make_request_with_retry("POST", endpoint, json=json_data, **kwargs)
    
    async def get(self, endpoint: str, **kwargs) -> httpx.Response:
        """Make GET request with retry logic."""
        return await self._make_request_with_retry("GET", endpoint, **kwargs)
    
    async def put(self, endpoint: str, json_data: Dict[str, Any] = None, **kwargs) -> httpx.Response:
        """Make PUT request with retry logic."""
        return await self._make_request_with_retry("PUT", endpoint, json=json_data, **kwargs)
    
    async def delete(self, endpoint: str, **kwargs) -> httpx.Response:
        """Make DELETE request with retry logic."""
        return await self._make_request_with_retry("DELETE", endpoint, **kwargs)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance metrics summary."""
        if not self.performance_metrics:
            return {}
        
        response_times = [m["response_time"] for m in self.performance_metrics if "error" not in m]
        successful_requests = len([m for m in self.performance_metrics if "error" not in m])
        failed_requests = len([m for m in self.performance_metrics if "error" in m])
        
        return {
            "total_requests": len(self.performance_metrics),
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": successful_requests / len(self.performance_metrics) if self.performance_metrics else 0,
            "avg_response_time": sum(response_times) / len(response_times) if response_times else 0,
            "min_response_time": min(response_times) if response_times else 0,
            "max_response_time": max(response_times) if response_times else 0,
            "total_test_time": max([m["timestamp"] + m["response_time"] for m in self.performance_metrics]) - min([m["timestamp"] for m in self.performance_metrics]) if self.performance_metrics else 0
        }


class StagingEnvironmentValidator:
    """Validator for staging environment health and readiness."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.health_status = {}
    
    async def validate_environment(self) -> bool:
        """Validate that staging environment is ready for E2E tests."""
        if not E2E_CONFIG["staging_health_check"]:
            return True
        
        try:
            async with E2ETestClient(self.base_url) as client:
                # Check root endpoint
                root_response = await client.get("/")
                
                if root_response.status_code != 200:
                    print(f"❌ Staging root endpoint failed: {root_response.status_code}")
                    return False
                
                root_data = root_response.json()
                self.health_status["root"] = {
                    "status": "healthy",
                    "version": root_data.get("version", "unknown"),
                    "features": len(root_data.get("features", []))
                }
                
                # Check health endpoint
                try:
                    health_response = await client.get("/api/v1/health/health")
                    
                    if health_response.status_code == 200:
                        health_data = health_response.json()
                        self.health_status["health"] = {
                            "status": health_data.get("status", "unknown"),
                            "accessible": True
                        }
                    else:
                        self.health_status["health"] = {
                            "status": "unhealthy",
                            "accessible": False,
                            "status_code": health_response.status_code
                        }
                
                except Exception as e:
                    self.health_status["health"] = {
                        "status": "error",
                        "accessible": False,
                        "error": str(e)
                    }
                
                # Check key API endpoints
                key_endpoints = [
                    "/api/v1/multi-agent/capabilities",
                    "/api/v1/realtime/info"
                ]
                
                endpoint_health = {}
                for endpoint in key_endpoints:
                    try:
                        response = await client.get(endpoint)
                        endpoint_health[endpoint] = {
                            "status_code": response.status_code,
                            "accessible": response.status_code == 200
                        }
                    except Exception as e:
                        endpoint_health[endpoint] = {
                            "accessible": False,
                            "error": str(e)
                        }
                
                self.health_status["endpoints"] = endpoint_health
                
                # Determine overall health
                root_healthy = self.health_status["root"]["status"] == "healthy"
                endpoints_healthy = all(ep.get("accessible", False) for ep in endpoint_health.values())
                
                overall_healthy = root_healthy and endpoints_healthy
                
                if overall_healthy:
                    print("✅ Staging environment validation passed")
                else:
                    print("⚠️  Staging environment has some issues but may still be usable")
                
                return overall_healthy
        
        except Exception as e:
            print(f"❌ Staging environment validation failed: {e}")
            return False


# Pytest fixtures
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def staging_validator():
    """Validate staging environment before running tests."""
    validator = StagingEnvironmentValidator(E2E_CONFIG["base_url"])
    
    is_healthy = await validator.validate_environment()
    
    if not is_healthy:
        pytest.skip("Staging environment is not healthy or accessible")
    
    yield validator


@pytest.fixture
async def e2e_client():
    """Create E2E test client with performance monitoring."""
    async with E2ETestClient() as client:
        yield client


@pytest.fixture
def sample_conversation_data():
    """Sample data for conversation testing."""
    return {
        "initial_query": "What were the key findings of the latest IPCC report?",
        "followup_query": "Based on that, what are the top three recommended actions for coastal cities?",
        "context_dependent_query": "How would these recommendations specifically apply to Miami?",
        "expected_context_keywords": ["IPCC", "climate", "coastal", "cities", "recommendations", "Miami"]
    }


@pytest.fixture
def sample_document_data():
    """Sample document data for testing."""
    return {
        "title": "E2E Test Document - Climate Change Report",
        "content": """
        Climate Change and Urban Planning Report
        
        Executive Summary:
        This report examines the impact of climate change on urban environments
        and provides recommendations for sustainable city planning.
        
        Key Findings:
        1. Urban heat islands are intensifying due to climate change
        2. Coastal cities face increased flooding risks from sea level rise
        3. Green infrastructure provides multiple climate benefits
        4. Community engagement is essential for adaptation success
        
        Recommendations:
        - Implement nature-based solutions for urban cooling
        - Develop climate-resilient infrastructure
        - Create community-centered adaptation plans
        - Invest in early warning systems
        """,
        "content_type": "text/plain",
        "tags": ["climate", "urban", "planning", "e2e-test"]
    }


@pytest.fixture
def sample_orchestrator_tasks():
    """Sample orchestrator task data for testing."""
    return [
        {
            "task_type": "AGENT_CHAT",
            "payload": {
                "input": "Explain the benefits of renewable energy",
                "save_conversation": False
            },
            "execution_mode": "SYNCHRONOUS",
            "priority": 1
        },
        {
            "task_type": "AGENT_CHAT",
            "payload": {
                "input": "What are the challenges in renewable energy adoption?",
                "save_conversation": False
            },
            "execution_mode": "SYNCHRONOUS",
            "priority": 2
        }
    ]


@pytest.fixture
def performance_monitor():
    """Performance monitoring fixture."""
    metrics = {
        "start_time": time.time(),
        "requests": [],
        "errors": [],
        "response_times": []
    }
    
    yield metrics
    
    # Calculate final metrics
    end_time = time.time()
    metrics["end_time"] = end_time
    metrics["total_duration"] = end_time - metrics["start_time"]
    
    if metrics["response_times"]:
        metrics["avg_response_time"] = sum(metrics["response_times"]) / len(metrics["response_times"])
        metrics["max_response_time"] = max(metrics["response_times"])
        metrics["min_response_time"] = min(metrics["response_times"])
    
    if E2E_CONFIG["performance_monitoring"] and E2E_CONFIG["verbose_logging"]:
        print(f"\n📊 Performance Summary:")
        print(f"   Total duration: {metrics['total_duration']:.2f}s")
        print(f"   Total requests: {len(metrics['requests'])}")
        print(f"   Errors: {len(metrics['errors'])}")
        if metrics.get("avg_response_time"):
            print(f"   Avg response time: {metrics['avg_response_time']:.3f}s")


@pytest.fixture(autouse=True)
async def test_isolation():
    """Ensure test isolation and cleanup."""
    # Pre-test setup
    test_start_time = time.time()
    
    yield
    
    # Post-test cleanup
    test_end_time = time.time()
    test_duration = test_end_time - test_start_time
    
    if E2E_CONFIG["verbose_logging"]:
        print(f"   Test duration: {test_duration:.2f}s")
    
    # Add small delay between tests to avoid overwhelming the staging environment
    if test_duration < 1.0:
        await asyncio.sleep(0.5)


# Test markers and configuration
def pytest_configure(config):
    """Configure pytest with E2E-specific markers."""
    config.addinivalue_line(
        "markers", "e2e: mark test as an end-to-end test"
    )
    config.addinivalue_line(
        "markers", "conversation: mark test as conversation workflow test"
    )
    config.addinivalue_line(
        "markers", "orchestrator: mark test as orchestrator workflow test"
    )
    config.addinivalue_line(
        "markers", "document: mark test as document workflow test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance workflow test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running E2E test"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection for E2E tests."""
    # Add e2e marker to all tests in e2e directory
    for item in items:
        if "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
    
    # Set default timeout for E2E tests
    for item in items:
        if item.get_closest_marker("e2e"):
            if not item.get_closest_marker("timeout"):
                item.add_marker(pytest.mark.timeout(E2E_CONFIG["timeout"]))


# Async test configuration
@pytest.fixture(scope="session")
def asyncio_mode():
    """Configure asyncio mode for pytest-asyncio."""
    return "auto"
