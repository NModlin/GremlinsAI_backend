# tests/unit/test_agent_reasoning.py
"""
Unit tests for ProductionAgent ReAct reasoning implementation

Tests cover:
- ReAct pattern execution (Reason → Act → Observe)
- Multi-step problem solving (3+ tool calls)
- Tool selection and execution
- Error handling and recovery
- LLM integration and response parsing
- Performance and timeout handling
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from app.core.agent import ProductionAgent, ReasoningStep, AgentResult, process_query
from app.core.llm_manager import LLMResponse


class TestProductionAgent:
    """Test ProductionAgent ReAct reasoning functionality."""
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Create a mock LLM manager."""
        mock_manager = AsyncMock()
        return mock_manager
    
    @pytest.fixture
    def agent_with_mock_llm(self, mock_llm_manager):
        """Create ProductionAgent with mocked LLM manager."""
        with patch('app.core.agent.ProductionLLMManager', return_value=mock_llm_manager):
            agent = ProductionAgent(max_iterations=5, max_execution_time=30)
            agent.llm_manager = mock_llm_manager
        return agent
    
    @pytest.fixture
    def sample_search_response(self):
        """Sample search tool response."""
        return "Search results: Paris is the capital and most populous city of France, located in the north-central part of the country."
    
    def test_agent_initialization(self):
        """Test ProductionAgent initialization."""
        with patch('app.core.agent.ProductionLLMManager'):
            agent = ProductionAgent(max_iterations=10, max_execution_time=60)
            
            assert agent.max_iterations == 10
            assert agent.max_execution_time == 60
            assert "search" in agent.tools
            assert "final_answer" in agent.tools
            assert agent.react_prompt is not None
    
    def test_parse_llm_response_complete(self, agent_with_mock_llm):
        """Test parsing complete LLM response with thought, action, and input."""
        response = """
        Thought: I need to search for information about the capital of France.
        Action: search
        Action Input: capital of France
        """
        
        thought, action, action_input = agent_with_mock_llm._parse_llm_response(response)
        
        assert "search for information about the capital of France" in thought
        assert action == "search"
        assert action_input == "capital of France"
    
    def test_parse_llm_response_partial(self, agent_with_mock_llm):
        """Test parsing partial LLM response with only thought."""
        response = "Thought: I need to think about this problem more carefully."
        
        thought, action, action_input = agent_with_mock_llm._parse_llm_response(response)
        
        assert "think about this problem more carefully" in thought
        assert action is None
        assert action_input is None
    
    def test_search_tool_execution(self, agent_with_mock_llm):
        """Test search tool execution."""
        with patch('app.core.agent.duckduckgo_search', return_value="Paris is the capital of France"):
            result = agent_with_mock_llm._search_tool("capital of France")
            
            assert "Search results:" in result
            assert "Paris is the capital of France" in result
    
    def test_search_tool_error_handling(self, agent_with_mock_llm):
        """Test search tool error handling."""
        with patch('app.core.agent.duckduckgo_search', side_effect=Exception("Network error")):
            result = agent_with_mock_llm._search_tool("test query")
            
            assert "Search failed:" in result
            assert "Network error" in result
    
    def test_final_answer_tool(self, agent_with_mock_llm):
        """Test final answer tool."""
        result = agent_with_mock_llm._final_answer_tool("Paris is the capital of France")
        
        assert result == "Final Answer: Paris is the capital of France"
    
    def test_execute_action_valid(self, agent_with_mock_llm):
        """Test executing valid action."""
        with patch('app.core.agent.duckduckgo_search', return_value="Test result"):
            result = agent_with_mock_llm._execute_action("search", "test query")
            
            assert "Search results:" in result
            assert "Test result" in result
    
    def test_execute_action_invalid(self, agent_with_mock_llm):
        """Test executing invalid action."""
        result = agent_with_mock_llm._execute_action("invalid_action", "test input")
        
        assert "Error: Unknown action" in result
        assert "invalid_action" in result
    
    def test_should_continue_logic(self, agent_with_mock_llm):
        """Test should continue logic."""
        # Should continue for search actions
        assert agent_with_mock_llm._should_continue("search", "Some search results")
        
        # Should not continue for final_answer
        assert not agent_with_mock_llm._should_continue("final_answer", "Final answer provided")
        
        # Should continue on errors to allow recovery
        assert agent_with_mock_llm._should_continue("search", "Error: Network timeout")
    
    @pytest.mark.asyncio
    async def test_simple_single_step_reasoning(self, agent_with_mock_llm, sample_search_response):
        """Test simple single-step reasoning (search + final answer)."""
        # Mock LLM responses for two steps
        mock_responses = [
            # Step 1: Search for information
            LLMResponse(
                content="""Thought: I need to search for the capital of France.
Action: search
Action Input: capital of France""",
                provider="mock",
                model="mock-model",
                response_time=0.1
            ),
            # Step 2: Provide final answer
            LLMResponse(
                content="""Thought: I found the information. Paris is the capital of France.
Action: final_answer
Action Input: The capital of France is Paris.""",
                provider="mock",
                model="mock-model",
                response_time=0.1
            )
        ]
        
        agent_with_mock_llm.llm_manager.generate_response.side_effect = mock_responses
        
        # Mock search tool
        with patch.object(agent_with_mock_llm, '_search_tool', return_value=sample_search_response):
            result = await agent_with_mock_llm.reason_and_act("What is the capital of France?")
        
        assert result.success is True
        assert result.total_steps == 2
        assert len(result.reasoning_steps) == 2
        assert "Paris" in result.final_answer
        
        # Verify reasoning steps
        step1 = result.reasoning_steps[0]
        assert step1.action == "search"
        assert "capital of France" in step1.action_input
        assert sample_search_response in step1.observation
        
        step2 = result.reasoning_steps[1]
        assert step2.action == "final_answer"
        assert "Paris" in step2.action_input
    
    @pytest.mark.asyncio
    async def test_multi_step_reasoning(self, agent_with_mock_llm):
        """Test multi-step reasoning requiring 3+ tool calls."""
        # Mock LLM responses for multiple steps
        mock_responses = [
            # Step 1: Search for France information
            LLMResponse(
                content="""Thought: I need to search for information about France first.
Action: search
Action Input: France country information""",
                provider="mock",
                model="mock-model",
                response_time=0.1
            ),
            # Step 2: Search specifically for capital
            LLMResponse(
                content="""Thought: I got general information about France. Now I need to search specifically for its capital.
Action: search
Action Input: France capital city""",
                provider="mock",
                model="mock-model",
                response_time=0.1
            ),
            # Step 3: Search for population information
            LLMResponse(
                content="""Thought: I know Paris is the capital. Let me get population information to provide a complete answer.
Action: search
Action Input: Paris population 2024""",
                provider="mock",
                model="mock-model",
                response_time=0.1
            ),
            # Step 4: Provide final comprehensive answer
            LLMResponse(
                content="""Thought: Now I have comprehensive information about France's capital and its population.
Action: final_answer
Action Input: The capital of France is Paris, which has a population of approximately 2.1 million people in the city proper and over 12 million in the metropolitan area.""",
                provider="mock",
                model="mock-model",
                response_time=0.1
            )
        ]
        
        agent_with_mock_llm.llm_manager.generate_response.side_effect = mock_responses
        
        # Mock search tool responses
        search_responses = [
            "France is a country in Western Europe with rich history and culture.",
            "Paris is the capital and largest city of France.",
            "Paris has a population of approximately 2.1 million in the city proper."
        ]
        
        with patch.object(agent_with_mock_llm, '_search_tool', side_effect=search_responses):
            result = await agent_with_mock_llm.reason_and_act("What is the capital of France and what is its population?")
        
        assert result.success is True
        assert result.total_steps == 4
        assert len(result.reasoning_steps) == 4
        
        # Verify all steps had search actions except the last
        for i in range(3):
            assert result.reasoning_steps[i].action == "search"
            assert result.reasoning_steps[i].observation is not None
        
        # Last step should be final answer
        assert result.reasoning_steps[3].action == "final_answer"
        assert "Paris" in result.final_answer
        assert "population" in result.final_answer
    
    @pytest.mark.asyncio
    async def test_error_recovery(self, agent_with_mock_llm):
        """Test agent recovery from tool errors."""
        mock_responses = [
            # Step 1: Initial search fails
            LLMResponse(
                content="""Thought: I need to search for information.
Action: search
Action Input: test query""",
                provider="mock",
                model="mock-model",
                response_time=0.1
            ),
            # Step 2: Retry with different approach
            LLMResponse(
                content="""Thought: The search failed. Let me try a different search query.
Action: search
Action Input: alternative test query""",
                provider="mock",
                model="mock-model",
                response_time=0.1
            ),
            # Step 3: Provide answer based on available information
            LLMResponse(
                content="""Thought: I was able to get some information on the second try.
Action: final_answer
Action Input: Based on the available information, here is what I found.""",
                provider="mock",
                model="mock-model",
                response_time=0.1
            )
        ]
        
        agent_with_mock_llm.llm_manager.generate_response.side_effect = mock_responses
        
        # Mock search tool with first failure, then success
        search_responses = [
            "Error: Network timeout",
            "Search results: Alternative information found"
        ]
        
        with patch.object(agent_with_mock_llm, '_search_tool', side_effect=search_responses):
            result = await agent_with_mock_llm.reason_and_act("Test query")
        
        assert result.success is True
        assert result.total_steps == 3
        
        # First step should have error observation
        assert "Error:" in result.reasoning_steps[0].observation
        
        # Second step should have successful observation
        assert "Alternative information found" in result.reasoning_steps[1].observation
    
    @pytest.mark.asyncio
    async def test_max_iterations_limit(self, agent_with_mock_llm):
        """Test agent respects maximum iterations limit."""
        # Create agent with low iteration limit
        agent_with_mock_llm.max_iterations = 2
        
        # Mock LLM to always return search actions (never final_answer)
        mock_response = LLMResponse(
            content="""Thought: I need to search for more information.
Action: search
Action Input: test query""",
            provider="mock",
            model="mock-model",
            response_time=0.1
        )
        agent_with_mock_llm.llm_manager.generate_response.return_value = mock_response
        
        with patch.object(agent_with_mock_llm, '_search_tool', return_value="Some results"):
            result = await agent_with_mock_llm.reason_and_act("Test query")
        
        assert result.success is False
        assert result.total_steps == 2  # Should stop at max_iterations
        assert "maximum iterations" in result.error_message
        assert "couldn't complete the task" in result.final_answer
    
    @pytest.mark.asyncio
    async def test_execution_timeout(self, agent_with_mock_llm):
        """Test agent respects execution timeout."""
        # Set very short timeout
        agent_with_mock_llm.max_execution_time = 0.1
        
        # Mock LLM with delay
        async def slow_response(*args, **kwargs):
            await asyncio.sleep(0.2)  # Longer than timeout
            return LLMResponse(content="Thought: This is slow", provider="mock", model="mock-model", response_time=0.2)
        
        agent_with_mock_llm.llm_manager.generate_response.side_effect = slow_response
        
        result = await agent_with_mock_llm.reason_and_act("Test query")
        
        assert result.success is False
        assert "timeout" in result.error_message
        assert "time limit" in result.final_answer
    
    @pytest.mark.asyncio
    async def test_llm_error_handling(self, agent_with_mock_llm):
        """Test handling of LLM errors."""
        # Mock LLM to raise exception
        agent_with_mock_llm.llm_manager.generate_response.side_effect = Exception("LLM service unavailable")
        
        result = await agent_with_mock_llm.reason_and_act("Test query")
        
        assert result.success is False
        assert "LLM service unavailable" in result.error_message
        assert "error occurred" in result.final_answer
    
    @pytest.mark.asyncio
    async def test_process_query_convenience_function(self):
        """Test the process_query convenience function."""
        with patch('app.core.agent.get_production_agent') as mock_get_agent:
            mock_agent = AsyncMock()
            mock_result = AgentResult(
                final_answer="Test answer",
                reasoning_steps=[],
                total_steps=1,
                success=True
            )
            mock_agent.reason_and_act.return_value = mock_result
            mock_get_agent.return_value = mock_agent
            
            result = await process_query("Test query", "conv-123")
            
            assert result.final_answer == "Test answer"
            assert result.success is True
            mock_agent.reason_and_act.assert_called_once_with("Test query", "conv-123")


if __name__ == "__main__":
    pytest.main([__file__])
