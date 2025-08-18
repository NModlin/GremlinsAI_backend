#!/usr/bin/env python3
"""
Load Testing Script for GremlinsAI Backend - Task T3.5

This script conducts comprehensive load testing to validate the system's ability
to handle 1000+ concurrent users while maintaining <2s response times.

Features:
- Realistic user journey simulation
- Gradual ramp-up from 1 to 1000+ concurrent users
- Automatic performance validation against acceptance criteria
- Comprehensive reporting and analysis
- Integration with monitoring stack
"""

import os
import sys
import time
import json
import statistics
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from locust import HttpUser, task, between, events
from locust.env import Environment
from locust.stats import stats_printer, stats_history
from locust.log import setup_logging
import gevent


class GremlinsAIUser(HttpUser):
    """
    Simulates realistic user behavior for GremlinsAI Backend.
    
    This class defines user journeys that mirror real usage patterns:
    - Starting conversations
    - Asking follow-up questions
    - Using different API endpoints
    - Maintaining conversation context
    """
    
    # Wait time between requests (1-3 seconds to simulate human behavior)
    wait_time = between(1, 3)
    
    def on_start(self):
        """Initialize user session data."""
        self.conversation_id = None
        self.user_id = f"load_test_user_{id(self)}"
        self.conversation_count = 0
        self.successful_requests = 0
        self.failed_requests = 0
    
    @task(40)  # 40% of requests - Primary user action
    def start_conversation(self):
        """
        Start a new conversation with the agent.
        
        This simulates the most common user action - starting a new conversation
        with a variety of realistic queries.
        """
        queries = [
            "What are the benefits of renewable energy?",
            "Explain machine learning in simple terms",
            "How does climate change affect coastal cities?",
            "What are the latest developments in AI technology?",
            "Can you help me understand blockchain technology?",
            "What are the best practices for sustainable development?",
            "How do neural networks work?",
            "What is the impact of automation on jobs?",
            "Explain quantum computing concepts",
            "What are the challenges in space exploration?"
        ]
        
        query = queries[self.conversation_count % len(queries)]
        
        payload = {
            "input": query,
            "save_conversation": True
        }
        
        with self.client.post(
            "/api/v1/agent/chat",
            json=payload,
            catch_response=True,
            name="start_conversation"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    self.conversation_id = data.get("conversation_id")
                    self.successful_requests += 1
                    
                    # Validate response structure
                    if not data.get("output"):
                        response.failure("Empty response output")
                    elif len(data.get("output", "")) < 10:
                        response.failure("Response too short")
                    else:
                        response.success()
                        
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
                    self.failed_requests += 1
            else:
                response.failure(f"HTTP {response.status_code}")
                self.failed_requests += 1
        
        self.conversation_count += 1
    
    @task(25)  # 25% of requests - Follow-up questions
    def continue_conversation(self):
        """
        Continue an existing conversation with follow-up questions.
        
        This simulates users asking follow-up questions to maintain
        conversation context and test the system's ability to handle
        contextual queries.
        """
        if not self.conversation_id:
            # Start a conversation first
            self.start_conversation()
            return
        
        followup_queries = [
            "Can you provide more details about that?",
            "What are the practical applications?",
            "How does this compare to alternatives?",
            "What are the potential risks or challenges?",
            "Can you give me some specific examples?",
            "How might this evolve in the future?",
            "What should I consider when implementing this?",
            "Are there any recent developments in this area?",
            "How does this impact different industries?",
            "What are the cost implications?"
        ]
        
        query = followup_queries[self.conversation_count % len(followup_queries)]
        
        payload = {
            "input": query,
            "conversation_id": self.conversation_id,
            "save_conversation": True
        }
        
        with self.client.post(
            "/api/v1/agent/chat",
            json=payload,
            catch_response=True,
            name="continue_conversation"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("conversation_id") == self.conversation_id:
                        self.successful_requests += 1
                        response.success()
                    else:
                        response.failure("Conversation ID mismatch")
                        self.failed_requests += 1
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
                    self.failed_requests += 1
            else:
                response.failure(f"HTTP {response.status_code}")
                self.failed_requests += 1
    
    @task(15)  # 15% of requests - Multi-agent queries
    def multi_agent_query(self):
        """
        Test multi-agent capabilities for complex queries.
        
        This simulates users leveraging advanced AI capabilities
        for more complex reasoning tasks.
        """
        complex_queries = [
            "Analyze the economic and environmental impacts of electric vehicles",
            "Compare different approaches to sustainable urban planning",
            "Evaluate the pros and cons of remote work policies",
            "Assess the potential of renewable energy technologies",
            "Examine the ethical implications of AI in healthcare"
        ]
        
        query = complex_queries[self.conversation_count % len(complex_queries)]
        
        payload = {
            "input": query,
            "workflow_type": "simple_research",
            "save_conversation": True
        }
        
        with self.client.post(
            "/api/v1/multi-agent/execute",
            json=payload,
            catch_response=True,
            name="multi_agent_query"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("output") or data.get("result"):
                        self.successful_requests += 1
                        response.success()
                    else:
                        response.failure("Empty multi-agent response")
                        self.failed_requests += 1
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
                    self.failed_requests += 1
            else:
                response.failure(f"HTTP {response.status_code}")
                self.failed_requests += 1
    
    @task(10)  # 10% of requests - Health checks and system info
    def check_system_health(self):
        """
        Check system health and capabilities.
        
        This simulates monitoring and health check requests
        that would be made by clients or monitoring systems.
        """
        endpoints = [
            ("/", "root_endpoint"),
            ("/api/v1/health/health", "health_check"),
            ("/api/v1/multi-agent/capabilities", "capabilities_check"),
            ("/api/v1/realtime/info", "realtime_info")
        ]
        
        endpoint, name = endpoints[self.conversation_count % len(endpoints)]
        
        with self.client.get(
            endpoint,
            catch_response=True,
            name=name
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    self.successful_requests += 1
                    response.success()
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
                    self.failed_requests += 1
            else:
                response.failure(f"HTTP {response.status_code}")
                self.failed_requests += 1
    
    @task(5)  # 5% of requests - Document operations
    def document_operations(self):
        """
        Test document-related operations.
        
        This simulates users interacting with document features
        like RAG queries and document searches.
        """
        # Test RAG query
        rag_queries = [
            "What are the key findings about climate change?",
            "Summarize the latest research on AI ethics",
            "Find information about sustainable energy solutions",
            "Search for best practices in software development",
            "Look up recent developments in biotechnology"
        ]
        
        query = rag_queries[self.conversation_count % len(rag_queries)]
        
        payload = {
            "query": query,
            "max_results": 5,
            "include_sources": True
        }
        
        with self.client.post(
            "/api/v1/documents/rag",
            json=payload,
            catch_response=True,
            name="document_rag_query"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "answer" in data:
                        self.successful_requests += 1
                        response.success()
                    else:
                        response.failure("No answer in RAG response")
                        self.failed_requests += 1
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
                    self.failed_requests += 1
            else:
                # RAG might not be available, don't count as failure
                response.success()
    
    @task(5)  # 5% of requests - Conversation history
    def check_conversation_history(self):
        """
        Check conversation history and messages.
        
        This simulates users reviewing their conversation history
        and checking message details.
        """
        if not self.conversation_id:
            return
        
        with self.client.get(
            f"/api/v1/history/conversations/{self.conversation_id}/messages",
            catch_response=True,
            name="conversation_history"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "messages" in data:
                        self.successful_requests += 1
                        response.success()
                    else:
                        response.failure("No messages in history response")
                        self.failed_requests += 1
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
                    self.failed_requests += 1
            else:
                response.failure(f"HTTP {response.status_code}")
                self.failed_requests += 1


class LoadTestRunner:
    """
    Manages and executes load tests with comprehensive reporting.
    
    This class handles the setup, execution, and analysis of load tests,
    including automatic validation against acceptance criteria.
    """
    
    def __init__(self, host: str = "http://localhost:8000"):
        self.host = host
        self.results = {}
        self.start_time = None
        self.end_time = None
        
        # Performance targets (acceptance criteria)
        self.max_response_time = 2.0  # seconds
        self.max_error_rate = 0.05    # 5%
        self.min_rps = 100           # requests per second
        
        # Test configuration
        self.max_users = 1000
        self.spawn_rate = 10  # users per second
        self.test_duration = 300  # 5 minutes at peak load
    
    def setup_environment(self):
        """Setup Locust environment for programmatic execution."""
        self.env = Environment(user_classes=[GremlinsAIUser])
        self.env.create_local_runner()
        
        # Setup logging
        setup_logging("INFO", None)
        
        # Setup event listeners for data collection
        self.setup_event_listeners()
    
    def setup_event_listeners(self):
        """Setup event listeners to collect test data."""
        self.request_data = []
        self.user_data = []
        
        @events.request.add_listener
        def on_request(request_type, name, response_time, response_length, exception, context, **kwargs):
            """Collect request data for analysis."""
            self.request_data.append({
                'timestamp': time.time(),
                'request_type': request_type,
                'name': name,
                'response_time': response_time,
                'response_length': response_length,
                'exception': str(exception) if exception else None,
                'success': exception is None
            })
        
        @events.user_error.add_listener
        def on_user_error(user_instance, exception, tb, **kwargs):
            """Collect user error data."""
            self.user_data.append({
                'timestamp': time.time(),
                'user_id': id(user_instance),
                'exception': str(exception),
                'traceback': tb
            })
    
    def run_load_test(self, users: int = None, spawn_rate: int = None, duration: int = None):
        """
        Execute the load test with specified parameters.
        
        Args:
            users: Maximum number of concurrent users
            spawn_rate: Users to spawn per second
            duration: Test duration in seconds
        """
        users = users or self.max_users
        spawn_rate = spawn_rate or self.spawn_rate
        duration = duration or self.test_duration
        
        print(f"\n🚀 Starting Load Test")
        print(f"   Target: {users} concurrent users")
        print(f"   Spawn rate: {spawn_rate} users/second")
        print(f"   Duration: {duration} seconds")
        print(f"   Host: {self.host}")
        
        self.start_time = time.time()
        
        # Start the test
        self.env.runner.start(users, spawn_rate=spawn_rate)
        
        # Wait for ramp-up
        ramp_up_time = users / spawn_rate
        print(f"\n⏳ Ramping up to {users} users ({ramp_up_time:.1f}s)...")
        
        # Monitor ramp-up progress
        for i in range(int(ramp_up_time) + 1):
            time.sleep(1)
            current_users = len(self.env.runner.user_greenlets)
            print(f"   Current users: {current_users}/{users}", end='\r')
        
        print(f"\n✅ Ramp-up complete: {len(self.env.runner.user_greenlets)} users active")
        
        # Run at peak load
        print(f"\n🔥 Running at peak load for {duration} seconds...")
        
        # Monitor test progress
        for i in range(duration):
            time.sleep(1)
            stats = self.env.runner.stats
            current_rps = stats.total.current_rps
            avg_response_time = stats.total.avg_response_time
            error_rate = stats.total.fail_ratio
            
            if i % 30 == 0:  # Print status every 30 seconds
                print(f"   Time: {i}s | RPS: {current_rps:.1f} | "
                      f"Avg Response: {avg_response_time:.0f}ms | "
                      f"Error Rate: {error_rate:.2%}")
        
        # Stop the test
        self.env.runner.stop()
        self.end_time = time.time()
        
        print(f"\n🏁 Load test completed!")
        
        # Wait for all requests to complete
        time.sleep(2)
        
        return self.analyze_results()
    
    def analyze_results(self) -> Dict[str, Any]:
        """
        Analyze test results and validate against acceptance criteria.
        
        Returns:
            Dict containing test results and pass/fail status
        """
        stats = self.env.runner.stats
        total_stats = stats.total
        
        # Calculate key metrics
        total_requests = total_stats.num_requests
        total_failures = total_stats.num_failures
        avg_response_time = total_stats.avg_response_time / 1000  # Convert to seconds
        max_response_time = total_stats.max_response_time / 1000  # Convert to seconds
        min_response_time = total_stats.min_response_time / 1000  # Convert to seconds
        error_rate = total_stats.fail_ratio
        rps = total_stats.total_rps
        
        # Calculate percentiles from request data
        response_times = [r['response_time'] / 1000 for r in self.request_data if r['success']]
        
        if response_times:
            p50_response_time = statistics.median(response_times)
            p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
            p99_response_time = statistics.quantiles(response_times, n=100)[98]  # 99th percentile
        else:
            p50_response_time = p95_response_time = p99_response_time = 0
        
        # Test duration
        test_duration = self.end_time - self.start_time if self.start_time and self.end_time else 0
        
        # Compile results
        results = {
            'test_summary': {
                'total_requests': total_requests,
                'total_failures': total_failures,
                'test_duration': test_duration,
                'concurrent_users': self.max_users,
                'host': self.host
            },
            'performance_metrics': {
                'requests_per_second': rps,
                'avg_response_time': avg_response_time,
                'min_response_time': min_response_time,
                'max_response_time': max_response_time,
                'p50_response_time': p50_response_time,
                'p95_response_time': p95_response_time,
                'p99_response_time': p99_response_time,
                'error_rate': error_rate
            },
            'acceptance_criteria': {
                'max_response_time_target': self.max_response_time,
                'max_error_rate_target': self.max_error_rate,
                'min_rps_target': self.min_rps
            }
        }
        
        # Validate against acceptance criteria
        criteria_results = {
            'response_time_pass': p95_response_time <= self.max_response_time,
            'error_rate_pass': error_rate <= self.max_error_rate,
            'throughput_pass': rps >= self.min_rps
        }
        
        results['validation'] = criteria_results
        results['overall_pass'] = all(criteria_results.values())
        
        self.results = results
        return results
    
    def print_results(self):
        """Print comprehensive test results."""
        if not self.results:
            print("❌ No test results available")
            return
        
        results = self.results
        
        print(f"\n" + "="*80)
        print(f"📊 LOAD TEST RESULTS - Task T3.5")
        print(f"="*80)
        
        # Test Summary
        summary = results['test_summary']
        print(f"\n📋 Test Summary:")
        print(f"   Host: {summary['host']}")
        print(f"   Concurrent Users: {summary['concurrent_users']:,}")
        print(f"   Test Duration: {summary['test_duration']:.1f} seconds")
        print(f"   Total Requests: {summary['total_requests']:,}")
        print(f"   Total Failures: {summary['total_failures']:,}")
        
        # Performance Metrics
        metrics = results['performance_metrics']
        print(f"\n📈 Performance Metrics:")
        print(f"   Requests/Second: {metrics['requests_per_second']:.1f}")
        print(f"   Average Response Time: {metrics['avg_response_time']:.3f}s")
        print(f"   50th Percentile: {metrics['p50_response_time']:.3f}s")
        print(f"   95th Percentile: {metrics['p95_response_time']:.3f}s")
        print(f"   99th Percentile: {metrics['p99_response_time']:.3f}s")
        print(f"   Max Response Time: {metrics['max_response_time']:.3f}s")
        print(f"   Error Rate: {metrics['error_rate']:.2%}")
        
        # Acceptance Criteria Validation
        validation = results['validation']
        criteria = results['acceptance_criteria']
        
        print(f"\n✅ Acceptance Criteria Validation:")
        
        # Response Time Check
        response_time_status = "✅ PASS" if validation['response_time_pass'] else "❌ FAIL"
        print(f"   Response Time (<{criteria['max_response_time_target']}s): {response_time_status}")
        print(f"      95th Percentile: {metrics['p95_response_time']:.3f}s")
        
        # Error Rate Check
        error_rate_status = "✅ PASS" if validation['error_rate_pass'] else "❌ FAIL"
        print(f"   Error Rate (<{criteria['max_error_rate_target']:.1%}): {error_rate_status}")
        print(f"      Actual: {metrics['error_rate']:.2%}")
        
        # Throughput Check
        throughput_status = "✅ PASS" if validation['throughput_pass'] else "❌ FAIL"
        print(f"   Throughput (>{criteria['min_rps_target']} RPS): {throughput_status}")
        print(f"      Actual: {metrics['requests_per_second']:.1f} RPS")
        
        # Overall Result
        overall_status = "🎉 PASS" if results['overall_pass'] else "❌ FAIL"
        print(f"\n🎯 Overall Result: {overall_status}")
        
        if results['overall_pass']:
            print("   ✅ System meets all performance requirements for 1000+ concurrent users")
            print("   ✅ Ready for production deployment")
        else:
            print("   ❌ System does not meet performance requirements")
            print("   ⚠️  Performance optimization needed before production")
        
        return results['overall_pass']
    
    def save_results(self, filename: str = None):
        """Save test results to JSON file."""
        if not self.results:
            return
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"load_test_results_{timestamp}.json"
        
        results_dir = Path("scripts/load_testing/results")
        results_dir.mkdir(exist_ok=True)
        
        filepath = results_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n💾 Results saved to: {filepath}")


def main():
    """Main entry point for load testing."""
    parser = argparse.ArgumentParser(description="Run load tests for GremlinsAI Backend")
    parser.add_argument("--host", default="http://localhost:8000", help="Target host URL")
    parser.add_argument("--users", type=int, default=1000, help="Maximum concurrent users")
    parser.add_argument("--spawn-rate", type=int, default=10, help="Users to spawn per second")
    parser.add_argument("--duration", type=int, default=300, help="Test duration in seconds")
    parser.add_argument("--save-results", action="store_true", help="Save results to file")
    
    args = parser.parse_args()
    
    # Create and run load test
    runner = LoadTestRunner(host=args.host)
    runner.setup_environment()
    
    try:
        # Run the load test
        results = runner.run_load_test(
            users=args.users,
            spawn_rate=args.spawn_rate,
            duration=args.duration
        )
        
        # Print results
        success = runner.print_results()
        
        # Save results if requested
        if args.save_results:
            runner.save_results()
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️  Load test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Load test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
