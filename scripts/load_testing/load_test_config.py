"""
Load Testing Configuration for GremlinsAI Backend - Task T3.5

This module provides configuration settings and test scenarios for
comprehensive load testing validation.

Features:
- Environment-specific configurations
- Test scenario definitions
- Performance target specifications
- User behavior patterns
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from enum import Enum


class TestEnvironment(Enum):
    """Test environment types."""
    LOCAL = "local"
    STAGING = "staging"
    PRODUCTION = "production"


class TestScenario(Enum):
    """Load test scenario types."""
    SMOKE = "smoke"           # Quick validation (100 users, 2 minutes)
    LOAD = "load"             # Standard load test (1000 users, 5 minutes)
    STRESS = "stress"         # Stress test (2000 users, 10 minutes)
    SPIKE = "spike"           # Spike test (rapid ramp-up)
    ENDURANCE = "endurance"   # Long-duration test (1000 users, 30 minutes)


@dataclass
class LoadTestConfig:
    """Load test configuration settings."""
    
    # Test parameters
    max_users: int
    spawn_rate: int
    test_duration: int
    
    # Performance targets
    max_response_time: float
    max_error_rate: float
    min_throughput: float
    
    # Environment settings
    host: str
    environment: TestEnvironment
    
    # Test behavior
    ramp_up_duration: Optional[int] = None
    cool_down_duration: int = 30
    
    def __post_init__(self):
        """Calculate derived values."""
        if self.ramp_up_duration is None:
            self.ramp_up_duration = self.max_users // self.spawn_rate


# Environment-specific configurations
ENVIRONMENT_CONFIGS = {
    TestEnvironment.LOCAL: {
        "host": "http://localhost:8000",
        "max_response_time": 3.0,  # More lenient for local testing
        "max_error_rate": 0.10,    # 10% error rate acceptable locally
        "min_throughput": 50.0     # Lower throughput expectation
    },
    TestEnvironment.STAGING: {
        "host": "https://staging.gremlinsai.com",
        "max_response_time": 2.5,  # Staging should be close to production
        "max_error_rate": 0.05,    # 5% error rate
        "min_throughput": 100.0    # Production-like throughput
    },
    TestEnvironment.PRODUCTION: {
        "host": "https://api.gremlinsai.com",
        "max_response_time": 2.0,  # Strict production requirements
        "max_error_rate": 0.02,    # 2% error rate
        "min_throughput": 200.0    # High throughput requirement
    }
}


# Test scenario configurations
TEST_SCENARIOS = {
    TestScenario.SMOKE: {
        "max_users": 100,
        "spawn_rate": 10,
        "test_duration": 120,  # 2 minutes
        "description": "Quick smoke test to validate basic functionality"
    },
    TestScenario.LOAD: {
        "max_users": 1000,
        "spawn_rate": 10,
        "test_duration": 300,  # 5 minutes
        "description": "Standard load test for 1000+ concurrent users"
    },
    TestScenario.STRESS: {
        "max_users": 2000,
        "spawn_rate": 20,
        "test_duration": 600,  # 10 minutes
        "description": "Stress test to find system breaking point"
    },
    TestScenario.SPIKE: {
        "max_users": 1500,
        "spawn_rate": 50,      # Rapid ramp-up
        "test_duration": 180,  # 3 minutes
        "description": "Spike test with rapid user ramp-up"
    },
    TestScenario.ENDURANCE: {
        "max_users": 1000,
        "spawn_rate": 5,       # Slow ramp-up
        "test_duration": 1800, # 30 minutes
        "description": "Endurance test for sustained load"
    }
}


# User behavior patterns
USER_BEHAVIOR_PATTERNS = {
    "conversation_heavy": {
        "start_conversation": 50,      # 50% of requests
        "continue_conversation": 35,   # 35% of requests
        "multi_agent_query": 10,       # 10% of requests
        "check_system_health": 3,      # 3% of requests
        "document_operations": 1,      # 1% of requests
        "check_conversation_history": 1 # 1% of requests
    },
    "api_heavy": {
        "start_conversation": 30,
        "continue_conversation": 20,
        "multi_agent_query": 20,
        "check_system_health": 15,
        "document_operations": 10,
        "check_conversation_history": 5
    },
    "research_heavy": {
        "start_conversation": 25,
        "continue_conversation": 25,
        "multi_agent_query": 30,       # Heavy multi-agent usage
        "check_system_health": 5,
        "document_operations": 10,     # More document operations
        "check_conversation_history": 5
    },
    "balanced": {
        "start_conversation": 40,
        "continue_conversation": 25,
        "multi_agent_query": 15,
        "check_system_health": 10,
        "document_operations": 5,
        "check_conversation_history": 5
    }
}


def create_load_test_config(
    scenario: TestScenario,
    environment: TestEnvironment,
    custom_overrides: Optional[Dict[str, Any]] = None
) -> LoadTestConfig:
    """
    Create a load test configuration for the specified scenario and environment.
    
    Args:
        scenario: Test scenario type
        environment: Target environment
        custom_overrides: Optional custom configuration overrides
        
    Returns:
        LoadTestConfig: Complete configuration for the load test
    """
    # Get base scenario configuration
    scenario_config = TEST_SCENARIOS[scenario].copy()
    
    # Get environment-specific settings
    env_config = ENVIRONMENT_CONFIGS[environment].copy()
    
    # Apply custom overrides if provided
    if custom_overrides:
        scenario_config.update(custom_overrides)
        env_config.update(custom_overrides)
    
    # Create configuration
    config = LoadTestConfig(
        max_users=scenario_config["max_users"],
        spawn_rate=scenario_config["spawn_rate"],
        test_duration=scenario_config["test_duration"],
        max_response_time=env_config["max_response_time"],
        max_error_rate=env_config["max_error_rate"],
        min_throughput=env_config["min_throughput"],
        host=env_config["host"],
        environment=environment
    )
    
    return config


def get_user_behavior_weights(pattern: str = "balanced") -> Dict[str, int]:
    """
    Get user behavior task weights for the specified pattern.
    
    Args:
        pattern: Behavior pattern name
        
    Returns:
        Dict mapping task names to weights
    """
    return USER_BEHAVIOR_PATTERNS.get(pattern, USER_BEHAVIOR_PATTERNS["balanced"])


# Performance thresholds for different metrics
PERFORMANCE_THRESHOLDS = {
    "response_time": {
        "excellent": 0.5,    # <500ms
        "good": 1.0,         # <1s
        "acceptable": 2.0,   # <2s
        "poor": 5.0          # <5s
    },
    "error_rate": {
        "excellent": 0.001,  # <0.1%
        "good": 0.01,        # <1%
        "acceptable": 0.05,  # <5%
        "poor": 0.10         # <10%
    },
    "throughput": {
        "excellent": 500,    # >500 RPS
        "good": 200,         # >200 RPS
        "acceptable": 100,   # >100 RPS
        "poor": 50           # >50 RPS
    }
}


def evaluate_performance(metrics: Dict[str, float]) -> Dict[str, str]:
    """
    Evaluate performance metrics against thresholds.
    
    Args:
        metrics: Dictionary of performance metrics
        
    Returns:
        Dictionary of performance ratings
    """
    ratings = {}
    
    # Evaluate response time (95th percentile)
    response_time = metrics.get("p95_response_time", float('inf'))
    if response_time <= PERFORMANCE_THRESHOLDS["response_time"]["excellent"]:
        ratings["response_time"] = "excellent"
    elif response_time <= PERFORMANCE_THRESHOLDS["response_time"]["good"]:
        ratings["response_time"] = "good"
    elif response_time <= PERFORMANCE_THRESHOLDS["response_time"]["acceptable"]:
        ratings["response_time"] = "acceptable"
    else:
        ratings["response_time"] = "poor"
    
    # Evaluate error rate
    error_rate = metrics.get("error_rate", 1.0)
    if error_rate <= PERFORMANCE_THRESHOLDS["error_rate"]["excellent"]:
        ratings["error_rate"] = "excellent"
    elif error_rate <= PERFORMANCE_THRESHOLDS["error_rate"]["good"]:
        ratings["error_rate"] = "good"
    elif error_rate <= PERFORMANCE_THRESHOLDS["error_rate"]["acceptable"]:
        ratings["error_rate"] = "acceptable"
    else:
        ratings["error_rate"] = "poor"
    
    # Evaluate throughput
    throughput = metrics.get("requests_per_second", 0)
    if throughput >= PERFORMANCE_THRESHOLDS["throughput"]["excellent"]:
        ratings["throughput"] = "excellent"
    elif throughput >= PERFORMANCE_THRESHOLDS["throughput"]["good"]:
        ratings["throughput"] = "good"
    elif throughput >= PERFORMANCE_THRESHOLDS["throughput"]["acceptable"]:
        ratings["throughput"] = "acceptable"
    else:
        ratings["throughput"] = "poor"
    
    return ratings


# Test data for realistic queries
CONVERSATION_STARTERS = [
    "What are the benefits of renewable energy?",
    "Explain machine learning in simple terms",
    "How does climate change affect coastal cities?",
    "What are the latest developments in AI technology?",
    "Can you help me understand blockchain technology?",
    "What are the best practices for sustainable development?",
    "How do neural networks work?",
    "What is the impact of automation on jobs?",
    "Explain quantum computing concepts",
    "What are the challenges in space exploration?",
    "How can we address global food security?",
    "What are the implications of genetic engineering?",
    "Describe the future of transportation",
    "How does cybersecurity affect businesses?",
    "What are the benefits of remote work?",
    "Explain the concept of circular economy",
    "How do we tackle plastic pollution?",
    "What is the role of AI in healthcare?",
    "Describe sustainable urban planning",
    "How can we improve education systems?"
]

FOLLOWUP_QUERIES = [
    "Can you provide more details about that?",
    "What are the practical applications?",
    "How does this compare to alternatives?",
    "What are the potential risks or challenges?",
    "Can you give me some specific examples?",
    "How might this evolve in the future?",
    "What should I consider when implementing this?",
    "Are there any recent developments in this area?",
    "How does this impact different industries?",
    "What are the cost implications?",
    "Who are the key players in this field?",
    "What regulatory considerations exist?",
    "How can individuals contribute?",
    "What are the environmental impacts?",
    "How does this affect developing countries?"
]

COMPLEX_QUERIES = [
    "Analyze the economic and environmental impacts of electric vehicles",
    "Compare different approaches to sustainable urban planning",
    "Evaluate the pros and cons of remote work policies",
    "Assess the potential of renewable energy technologies",
    "Examine the ethical implications of AI in healthcare",
    "Investigate the relationship between technology and privacy",
    "Study the effects of globalization on local economies",
    "Research the impact of social media on mental health",
    "Analyze the challenges of aging populations",
    "Explore the future of work in the digital age"
]

RAG_QUERIES = [
    "What are the key findings about climate change?",
    "Summarize the latest research on AI ethics",
    "Find information about sustainable energy solutions",
    "Search for best practices in software development",
    "Look up recent developments in biotechnology",
    "Research trends in digital transformation",
    "Find studies on workplace productivity",
    "Search for information on data privacy laws",
    "Look up research on renewable energy adoption",
    "Find reports on cybersecurity threats"
]
