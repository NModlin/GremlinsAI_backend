# tests/unit/test_agent_execution.py
"""
Unit tests for agent execution functionality.

Tests verify the acceptance criteria for Phase 1, Task 1.1:
- Agent can execute tools without runtime errors
- ReAct reasoning cycle completes successfully
- Response time is under 2 seconds
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from app.core.agent import ProductionAgent, ToolNotFoundException, ReasoningStep, AgentResult
from app.tools.tool_registry import ToolRegistry, ToolInfo
from app.tools.base_tool import ToolResult


class TestAgentExecution:
    """Test suite for agent execution functionality."""

    @pytest.fixture
    def mock_tool_registry(self):
        """Create a mock tool registry for testing."""
        registry = Mock(spec=ToolRegistry)
        
        # Mock tools dictionary
        registry.tools = {
            "web_search": Mock(spec=ToolInfo),
            "calculator": Mock(spec=ToolInfo),
            "final_answer": Mock(spec=ToolInfo)
        }
        
        # Mock execute_tool method
        async def mock_execute_tool(tool_name: str, tool_input: Any) -> ToolResult:
            if tool_name == "web_search":
                return ToolResult(
                    success=True,
                    result="Search results for: " + str(tool_input.get("query", tool_input)),
                    tool_name=tool_name
                )
            elif tool_name == "calculator":
                return ToolResult(
                    success=True,
                    result="42",
                    tool_name=tool_name
                )
            else:
                return ToolResult(
                    success=False,
                    result=None,
                    error_message=f"Unknown tool: {tool_name}",
                    tool_name=tool_name
                )
        
        registry.execute_tool = AsyncMock(side_effect=mock_execute_tool)
        registry.get_tool = Mock(return_value=Mock(spec=ToolInfo))
        registry.list_tools = Mock(return_value=["web_search", "calculator", "final_answer"])

        return registry

    @pytest.fixture
    def mock_llm_manager(self):
        """Create a mock LLM manager for testing."""
        llm_manager = Mock()
        
        # Mock response counter for different stages of ReAct
        response_count = 0
        
        async def mock_generate_response(prompt: str, **kwargs):
            nonlocal response_count
            response_count += 1
            
            response = Mock()
            if "What should you think about next" in prompt:
                # Thought generation
                response.content = "I need to search for information about the user's query."
            elif "what action should you take" in prompt:
                # Action selection
                if response_count <= 2:
                    response.content = "Action: web_search\nAction Input: test query"
                else:
                    response.content = "Action: final_answer\nAction Input: Based on my search, here is the answer."
            else:
                # Default response
                response.content = "I understand the query and will help you."
            
            return response
        
        llm_manager.generate_response = AsyncMock(side_effect=mock_generate_response)
        return llm_manager

    @pytest.fixture
    def agent(self, mock_llm_manager):
        """Create a ProductionAgent instance for testing."""
        with patch('app.core.llm_manager.ProductionLLMManager', return_value=mock_llm_manager), \
             patch('app.core.context_store.get_context_store'), \
             patch('app.core.memory_manager.MemoryManager'), \
             patch('app.core.task_planner.get_task_planner'), \
             patch('app.core.agent_learning.get_learning_service'):
            agent = ProductionAgent()
            return agent

    @pytest.mark.asyncio
    async def test_execute_tool_success(self, agent, mock_tool_registry):
        """Test that _execute_tool method works without runtime errors."""
        with patch('app.core.agent.get_tool_registry', return_value=mock_tool_registry):
            # Test successful tool execution
            result = await agent._execute_tool("web_search", {"query": "test"})
            
            assert isinstance(result, str)
            assert "Search results for:" in result
            mock_tool_registry.execute_tool.assert_called_once_with("web_search", {"query": "test"})

    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self, agent, mock_tool_registry):
        """Test that _execute_tool raises ToolNotFoundException for missing tools."""
        # Remove tool from registry
        mock_tool_registry.tools = {}
        
        with patch('app.core.agent.get_tool_registry', return_value=mock_tool_registry):
            with pytest.raises(ToolNotFoundException) as exc_info:
                await agent._execute_tool("nonexistent_tool", {"query": "test"})
            
            assert "nonexistent_tool not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_tool_execution_error(self, agent, mock_tool_registry):
        """Test that _execute_tool handles execution errors gracefully."""
        # Mock tool execution to raise an exception
        mock_tool_registry.execute_tool = AsyncMock(side_effect=Exception("Tool execution failed"))
        
        with patch('app.core.agent.get_tool_registry', return_value=mock_tool_registry):
            result = await agent._execute_tool("web_search", {"query": "test"})
            
            assert isinstance(result, str)
            assert "Tool execution failed" in result

    @pytest.mark.asyncio
    async def test_react_cycle_completion(self, agent, mock_tool_registry):
        """Test that ReAct reasoning cycle completes successfully for complex queries."""
        with patch('app.core.agent.get_tool_registry', return_value=mock_tool_registry):
            query = "What is the capital of France?"
            
            result = await agent.reason_and_act(query)
            
            # Verify result structure
            assert isinstance(result, AgentResult)
            assert result.final_answer is not None
            assert len(result.reasoning_steps) > 0
            assert result.total_steps > 0
            
            # Verify reasoning steps have proper structure
            for step in result.reasoning_steps:
                assert isinstance(step, ReasoningStep)
                assert step.step_number > 0
                assert step.thought is not None
                assert step.action is not None
                assert step.observation is not None

    @pytest.mark.asyncio
    async def test_react_cycle_performance(self, agent, mock_tool_registry):
        """Test that agent response time is under 2 seconds."""
        with patch('app.core.agent.get_tool_registry', return_value=mock_tool_registry):
            query = "Simple test query"
            
            start_time = time.time()
            result = await agent.reason_and_act(query)
            end_time = time.time()
            
            execution_time = end_time - start_time
            
            # Verify performance requirement (excluding external tool execution time)
            assert execution_time < 2.0, f"Agent took {execution_time:.2f} seconds, should be under 2 seconds"
            assert result.success is not None

    @pytest.mark.asyncio
    async def test_format_tool_result_success(self, agent):
        """Test _format_tool_result with successful ToolResult."""
        tool_result = ToolResult(
            success=True,
            result="Test result",
            tool_name="test_tool"
        )
        
        formatted = agent._format_tool_result(tool_result)
        assert formatted == "Test result"

    @pytest.mark.asyncio
    async def test_format_tool_result_error(self, agent):
        """Test _format_tool_result with failed ToolResult."""
        tool_result = ToolResult(
            success=False,
            result=None,
            error_message="Tool failed",
            tool_name="test_tool"
        )
        
        formatted = agent._format_tool_result(tool_result)
        assert formatted == "Error: Tool failed"

    @pytest.mark.asyncio
    async def test_format_tool_result_direct(self, agent):
        """Test _format_tool_result with direct result."""
        direct_result = "Direct string result"
        
        formatted = agent._format_tool_result(direct_result)
        assert formatted == "Direct string result"

    @pytest.mark.asyncio
    async def test_generate_thought(self, agent):
        """Test thought generation functionality."""
        query = "Test query"
        reasoning_steps = []
        
        thought = await agent._generate_thought(query, reasoning_steps)
        
        assert isinstance(thought, str)
        assert len(thought) > 0

    @pytest.mark.asyncio
    async def test_select_action(self, agent, mock_tool_registry):
        """Test action selection functionality."""
        with patch('app.core.agent.get_tool_registry', return_value=mock_tool_registry):
            thought = "I need to search for information"
            
            action = await agent._select_action(thought)
            
            assert isinstance(action, dict)
            assert "name" in action
            assert "input" in action
            assert action["name"] in ["web_search", "calculator", "final_answer"]

    @pytest.mark.asyncio
    async def test_is_complete_final_answer(self, agent):
        """Test completion detection with final answer."""
        observation = "Final Answer: This is the final answer"
        
        is_complete = agent._is_complete(observation)
        assert is_complete is True

    @pytest.mark.asyncio
    async def test_is_complete_not_final(self, agent):
        """Test completion detection without final answer."""
        observation = "This is just a regular observation"
        
        is_complete = agent._is_complete(observation)
        assert is_complete is False

    @pytest.mark.asyncio
    async def test_generate_final_answer(self, agent):
        """Test final answer generation."""
        reasoning_steps = [
            ReasoningStep(
                step_number=1,
                thought="Test thought",
                action="web_search",
                action_input="test query",
                observation="Final Answer: Test final answer"
            )
        ]
        
        final_answer = agent._generate_final_answer(reasoning_steps)
        assert final_answer == "Test final answer"

    @pytest.mark.asyncio
    async def test_generate_final_answer_no_steps(self, agent):
        """Test final answer generation with no reasoning steps."""
        reasoning_steps = []
        
        final_answer = agent._generate_final_answer(reasoning_steps)
        assert "couldn't process" in final_answer.lower()


if __name__ == "__main__":
    pytest.main([__file__])
