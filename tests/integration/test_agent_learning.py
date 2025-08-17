# tests/integration/test_agent_learning.py
"""
Integration tests for agent learning and adaptation capabilities.

These tests verify that the ProductionAgent can:
- Perform self-reflection on completed tasks
- Extract learning insights from performance analysis
- Store learning data in Weaviate
- Apply learning context to improve future performance
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from app.core.agent import ProductionAgent, AgentResult, ReasoningStep
from app.core.agent_learning import (
    AgentLearningService, AgentLearning, LearningInsight, 
    PerformanceMetrics, PerformanceCategory, LearningType
)
from app.core.task_planner import ExecutionPlan, PlanStep, PlanStepType, PlanStepStatus


class TestAgentLearning:
    """Test suite for agent learning and adaptation capabilities."""
    
    @pytest.fixture
    def mock_weaviate_client(self):
        """Create a mock Weaviate client for testing."""
        mock_client = MagicMock()
        
        # Mock collections
        mock_collections = MagicMock()
        mock_client.collections = mock_collections
        
        # Mock collection operations
        mock_collection = MagicMock()
        mock_collections.get.return_value = mock_collection
        
        # Mock data insertion
        mock_collection.data.insert.return_value = "test_learning_id_123"
        
        # Mock query operations
        mock_query_response = MagicMock()
        mock_query_response.objects = []
        mock_collection.query.near_text.return_value = mock_query_response
        
        return mock_client
    
    @pytest.fixture
    def sample_agent_result(self):
        """Create a sample agent result for testing."""
        # Create sample reasoning steps
        reasoning_steps = [
            ReasoningStep(
                step_number=1,
                thought="I need to research the topic",
                action="web_search",
                action_input="AI productivity tools market research",
                observation="Found comprehensive market data showing strong growth in AI productivity sector"
            ),
            ReasoningStep(
                step_number=2,
                thought="Now I need to analyze the target audience",
                action="text_processor",
                action_input="Analyze remote worker demographics and pain points",
                observation="Identified key demographics: 25-45 professionals, main pain points: communication and task management"
            ),
            ReasoningStep(
                step_number=3,
                thought="I can now provide a comprehensive marketing strategy",
                action="final_answer",
                action_input="Based on my research, here's a comprehensive marketing strategy...",
                observation="Final answer provided"
            )
        ]
        
        # Create sample execution plan
        execution_plan = ExecutionPlan(
            plan_id="test_plan_123",
            goal="Create a marketing strategy for AI productivity app",
            goal_type="creation",
            complexity_score=0.8,
            total_steps=3,
            estimated_duration=180,
            steps=[
                PlanStep(
                    step_id="step_1",
                    step_number=1,
                    title="Market Research",
                    description="Research AI productivity tools market",
                    step_type=PlanStepType.RESEARCH,
                    required_tools=["web_search"],
                    expected_output="Market analysis data",
                    dependencies=[],
                    estimated_duration=60,
                    status=PlanStepStatus.COMPLETED,
                    actual_output="Comprehensive market data collected"
                ),
                PlanStep(
                    step_id="step_2",
                    step_number=2,
                    title="Audience Analysis",
                    description="Analyze target audience demographics",
                    step_type=PlanStepType.ANALYSIS,
                    required_tools=["text_processor"],
                    expected_output="Target audience profile",
                    dependencies=["step_1"],
                    estimated_duration=60,
                    status=PlanStepStatus.COMPLETED,
                    actual_output="Target demographics identified"
                ),
                PlanStep(
                    step_id="step_3",
                    step_number=3,
                    title="Strategy Development",
                    description="Develop comprehensive marketing strategy",
                    step_type=PlanStepType.CREATION,
                    required_tools=["text_processor"],
                    expected_output="Marketing strategy document",
                    dependencies=["step_1", "step_2"],
                    estimated_duration=60,
                    status=PlanStepStatus.COMPLETED,
                    actual_output="Complete marketing strategy created"
                )
            ],
            required_tools=["web_search", "text_processor"],
            success_criteria=["Market analysis complete", "Audience identified", "Strategy documented"],
            fallback_strategies=["Use template approach", "Focus on primary channels"]
        )
        
        return AgentResult(
            final_answer="I've created a comprehensive marketing strategy for your AI productivity app targeting remote workers. The strategy includes market positioning, target audience analysis, and multi-channel approach focusing on LinkedIn, content marketing, and webinars.",
            reasoning_steps=reasoning_steps,
            total_steps=3,
            success=True,
            execution_plan=execution_plan,
            plan_used=True
        )
    
    @pytest.mark.asyncio
    async def test_agent_self_reflection_and_learning_storage(self, mock_weaviate_client, sample_agent_result):
        """Test that agent performs self-reflection and stores learning insights."""
        
        # Mock LLM response for reflection
        mock_reflection_response = json.dumps({
            "performance_assessment": {
                "overall_rating": "good",
                "strengths": ["Systematic approach", "Comprehensive research", "Clear strategy"],
                "weaknesses": ["Could be more efficient", "Limited tool diversity"],
                "efficiency_score": 0.8,
                "tool_effectiveness": 0.7,
                "planning_quality": 0.9
            },
            "learning_insights": [
                {
                    "type": "strategy_improvement",
                    "title": "Enhance research efficiency",
                    "description": "The research phase took longer than necessary due to broad initial queries",
                    "improvement_suggestion": "Use more specific, targeted search queries to reduce research time",
                    "confidence": 0.8,
                    "applicable_scenarios": ["market research", "competitive analysis"],
                    "impact": "Could reduce research time by 25%"
                },
                {
                    "type": "tool_optimization",
                    "title": "Diversify tool usage",
                    "description": "Heavy reliance on web_search and text_processor, missing other available tools",
                    "improvement_suggestion": "Consider using calculator for market sizing and data analysis tools",
                    "confidence": 0.6,
                    "applicable_scenarios": ["data analysis", "market research"],
                    "impact": "More accurate analysis and insights"
                }
            ],
            "strategy_recommendations": [
                "Use more targeted search queries for efficiency",
                "Incorporate quantitative analysis tools when dealing with market data",
                "Consider parallel execution of independent research tasks"
            ],
            "reflection_summary": "Good performance with systematic approach, but efficiency can be improved through better tool selection and more targeted queries."
        })
        
        with patch('app.core.agent.ProductionLLMManager') as mock_llm_manager_class, \
             patch('app.core.agent.get_tool_registry') as mock_tool_registry, \
             patch('app.core.agent.get_task_planner') as mock_task_planner_func, \
             patch('app.core.agent.get_context_store') as mock_context_store, \
             patch('app.core.agent.MemoryManager') as mock_memory_manager, \
             patch('app.core.agent_learning.ProductionLLMManager') as mock_learning_llm_manager_class:
            
            # Setup agent mocks
            mock_llm_manager = AsyncMock()
            mock_llm_manager_class.return_value = mock_llm_manager
            
            # Setup learning service LLM mock
            mock_learning_llm_manager = AsyncMock()
            mock_learning_llm_manager_class.return_value = mock_learning_llm_manager
            mock_learning_llm_manager.generate_response.return_value = mock_reflection_response
            
            # Setup other mocks
            mock_registry = MagicMock()
            mock_registry.list_tools.return_value = ["web_search", "text_processor", "calculator"]
            mock_registry.get_tool.return_value = MagicMock(description="Mock tool")
            mock_tool_registry.return_value = mock_registry
            
            mock_task_planner = MagicMock()
            mock_task_planner_func.return_value = mock_task_planner
            
            mock_context_store.return_value = MagicMock()
            mock_memory_manager.return_value = MagicMock()
            
            # Create agent with mocked Weaviate client
            agent = ProductionAgent(
                max_iterations=5, 
                max_execution_time=300, 
                planning_threshold=0.3,
                weaviate_client=mock_weaviate_client
            )
            
            # Test data
            original_query = "Create a comprehensive marketing strategy for an AI productivity app targeting remote workers"
            execution_time = 145.5
            
            # Perform self-reflection
            learning = await agent.self_reflection(
                agent_result=sample_agent_result,
                original_query=original_query,
                execution_time=execution_time
            )
            
            # Verify learning object was created
            assert learning is not None
            assert isinstance(learning, AgentLearning)
            assert learning.original_query == original_query
            assert learning.agent_type == "production_agent"
            assert learning.performance_category == PerformanceCategory.GOOD
            
            # Verify performance metrics
            assert learning.performance_metrics.efficiency_score == 0.8
            assert learning.performance_metrics.tool_usage_effectiveness == 0.7
            assert learning.performance_metrics.planning_accuracy == 0.9
            
            # Verify learning insights
            assert len(learning.learning_insights) == 2
            
            insight1 = learning.learning_insights[0]
            assert insight1.learning_type == LearningType.STRATEGY_IMPROVEMENT
            assert insight1.title == "Enhance research efficiency"
            assert insight1.confidence_score == 0.8
            assert "specific, targeted search queries" in insight1.improvement_suggestion
            
            insight2 = learning.learning_insights[1]
            assert insight2.learning_type == LearningType.TOOL_OPTIMIZATION
            assert insight2.title == "Diversify tool usage"
            assert insight2.confidence_score == 0.6
            
            # Verify strategy recommendations
            assert len(learning.strategy_updates) == 3
            assert "Use more targeted search queries" in learning.strategy_updates[0]
            assert "quantitative analysis tools" in learning.strategy_updates[1]
            
            # Verify task transcript
            assert learning.task_transcript["execution_summary"]["success"] == True
            assert learning.task_transcript["execution_summary"]["total_steps"] == 3
            assert learning.task_transcript["execution_summary"]["execution_time"] == execution_time
            assert learning.task_transcript["execution_summary"]["plan_used"] == True
            
            # Verify reasoning steps in transcript
            assert len(learning.task_transcript["reasoning_steps"]) == 3
            assert learning.task_transcript["reasoning_steps"][0]["action"] == "web_search"
            assert learning.task_transcript["reasoning_steps"][2]["action"] == "final_answer"
            
            # Verify execution plan in transcript
            plan_transcript = learning.task_transcript["execution_plan"]
            assert plan_transcript["plan_id"] == "test_plan_123"
            assert plan_transcript["total_steps"] == 3
            assert len(plan_transcript["steps"]) == 3
            
            # Verify Weaviate storage was called
            mock_weaviate_client.collections.get.assert_called_with("AgentLearning")
            mock_collection = mock_weaviate_client.collections.get.return_value
            mock_collection.data.insert.assert_called_once()
            
            # Verify the data structure passed to Weaviate
            insert_call_args = mock_collection.data.insert.call_args[0][0]
            assert insert_call_args["learningId"] == learning.learning_id
            assert insert_call_args["originalQuery"] == original_query
            assert insert_call_args["performanceCategory"] == "good"
            assert insert_call_args["agentType"] == "production_agent"
            assert len(insert_call_args["learningInsights"]) == 2
            assert len(insert_call_args["strategyUpdates"]) == 3
            
            # Verify LLM was called for reflection
            mock_learning_llm_manager.generate_response.assert_called_once()
            reflection_call = mock_learning_llm_manager.generate_response.call_args
            assert original_query in reflection_call[1]["prompt"]
            assert "REFLECTION ANALYSIS" in reflection_call[1]["prompt"]
    
    @pytest.mark.asyncio
    async def test_agent_learning_context_application(self, mock_weaviate_client):
        """Test that agent applies learning context from past experiences."""
        
        # Mock similar learnings retrieval
        mock_similar_learnings = [
            AgentLearning(
                learning_id="past_learning_1",
                task_id="past_task_1",
                agent_type="production_agent",
                original_query="Create marketing plan for SaaS product",
                performance_category=PerformanceCategory.EXCELLENT,
                performance_metrics=PerformanceMetrics(
                    success_rate=1.0, efficiency_score=0.9, tool_usage_effectiveness=0.8,
                    planning_accuracy=0.9, execution_time_ratio=0.8, error_recovery_rate=0.9,
                    overall_score=0.88
                ),
                task_transcript={},
                reflection_analysis="Excellent performance with efficient tool usage",
                learning_insights=[
                    LearningInsight(
                        insight_id="insight_1",
                        learning_type=LearningType.EFFICIENCY_GAIN,
                        title="Use parallel research approach",
                        description="Parallel research significantly improved efficiency",
                        context="marketing strategy",
                        improvement_suggestion="Execute independent research tasks in parallel",
                        confidence_score=0.9,
                        applicable_scenarios=["marketing", "research"],
                        performance_impact="30% time reduction",
                        created_at=datetime.utcnow().isoformat()
                    )
                ],
                strategy_updates=["Use parallel execution for independent tasks"],
                created_at=datetime.utcnow().isoformat(),
                metadata={}
            )
        ]
        
        with patch('app.core.agent.ProductionLLMManager') as mock_llm_manager_class, \
             patch('app.core.agent.get_tool_registry') as mock_tool_registry, \
             patch('app.core.agent.get_task_planner') as mock_task_planner_func, \
             patch('app.core.agent.get_context_store') as mock_context_store, \
             patch('app.core.agent.MemoryManager') as mock_memory_manager:
            
            # Setup mocks
            mock_llm_manager = AsyncMock()
            mock_llm_manager_class.return_value = mock_llm_manager
            
            mock_registry = MagicMock()
            mock_registry.list_tools.return_value = ["web_search", "text_processor"]
            mock_tool_registry.return_value = mock_registry
            
            mock_task_planner = MagicMock()
            mock_task_planner_func.return_value = mock_task_planner
            
            mock_context_store.return_value = MagicMock()
            mock_memory_manager.return_value = MagicMock()
            
            # Create agent with mocked Weaviate client
            agent = ProductionAgent(
                max_iterations=5,
                max_execution_time=300,
                planning_threshold=0.3,
                weaviate_client=mock_weaviate_client
            )
            
            # Mock the learning service to return similar learnings
            agent.learning_service.retrieve_similar_learnings = AsyncMock(return_value=mock_similar_learnings)
            
            # Test learning context application
            query = "Develop marketing strategy for new productivity app"
            learning_context = await agent._apply_learning_context(query)
            
            # Verify learning context was generated
            assert learning_context != ""
            assert "Based on 1 similar past tasks" in learning_context
            assert "Use parallel research approach" in learning_context
            assert "Execute independent research tasks in parallel" in learning_context
            assert "Use parallel execution for independent tasks" in learning_context
            
            # Verify the learning service was called correctly
            agent.learning_service.retrieve_similar_learnings.assert_called_once_with(
                query=query, limit=3
            )
    
    @pytest.mark.asyncio
    async def test_learning_service_performance_analysis(self, mock_weaviate_client, sample_agent_result):
        """Test the learning service performance analysis functionality."""
        
        # Mock LLM response for reflection
        mock_reflection_response = json.dumps({
            "performance_assessment": {
                "overall_rating": "excellent",
                "strengths": ["Efficient execution", "Good tool selection"],
                "weaknesses": ["Minor optimization opportunities"],
                "efficiency_score": 0.9,
                "tool_effectiveness": 0.85,
                "planning_quality": 0.95
            },
            "learning_insights": [
                {
                    "type": "success_pattern",
                    "title": "Effective planning approach",
                    "description": "The systematic planning approach led to efficient execution",
                    "improvement_suggestion": "Continue using structured planning for complex tasks",
                    "confidence": 0.95,
                    "applicable_scenarios": ["complex planning", "multi-step tasks"],
                    "impact": "Maintains high success rate"
                }
            ],
            "strategy_recommendations": [
                "Maintain systematic planning approach for complex tasks"
            ],
            "reflection_summary": "Excellent performance demonstrating effective planning and execution."
        })
        
        with patch('app.core.agent_learning.ProductionLLMManager') as mock_llm_manager_class:
            # Setup learning service LLM mock
            mock_llm_manager = AsyncMock()
            mock_llm_manager_class.return_value = mock_llm_manager
            mock_llm_manager.generate_response.return_value = mock_reflection_response
            
            # Create learning service
            learning_service = AgentLearningService(mock_weaviate_client)
            
            # Test performance analysis
            original_query = "Create comprehensive marketing strategy"
            execution_time = 120.0
            
            learning = await learning_service.analyze_performance(
                agent_result=sample_agent_result,
                original_query=original_query,
                execution_time=execution_time
            )
            
            # Verify learning analysis
            assert learning is not None
            assert learning.original_query == original_query
            assert learning.performance_category == PerformanceCategory.EXCELLENT
            assert learning.performance_metrics.overall_score > 0.8
            
            # Verify insights extraction
            assert len(learning.learning_insights) == 1
            insight = learning.learning_insights[0]
            assert insight.learning_type == LearningType.SUCCESS_PATTERN
            assert insight.title == "Effective planning approach"
            assert insight.confidence_score == 0.95
            
            # Verify LLM was called for reflection
            mock_llm_manager.generate_response.assert_called_once()
            
            # Verify Weaviate storage
            mock_collection = mock_weaviate_client.collections.get.return_value
            stored = await learning_service.store_learning(learning)
            assert stored == True
            mock_collection.data.insert.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
