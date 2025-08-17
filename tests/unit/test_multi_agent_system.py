"""
Comprehensive unit tests for the multi-agent system.

Tests cover:
- MultiAgentOrchestrator initialization and configuration
- Agent creation and management
- Workflow execution and orchestration
- Error handling and fallback mechanisms
- Tool integration and search capabilities
- Mock isolation from external dependencies
"""

import pytest
import asyncio
import sys
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any, List, Optional

# Mock problematic imports before importing the module
with patch.dict('sys.modules', {
    'langgraph': Mock(),
    'langgraph.prebuilt': Mock(),
    'langchain_core': Mock(),
    'langchain_core.language_models': Mock(),
    'crewai': Mock(),
    'crewai_tools': Mock()
}):
    # Import the classes under test
    from app.core.multi_agent import MultiAgentOrchestrator


class TestMultiAgentOrchestrator:
    """Test suite for MultiAgentOrchestrator class."""
    
    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM for testing."""
        llm = Mock()
        llm.invoke = Mock(return_value="Mock LLM response")
        return llm
    
    @pytest.fixture
    def mock_llm_info(self):
        """Create mock LLM info."""
        return {
            'provider': 'test_provider',
            'model_name': 'test_model',
            'temperature': 0.7,
            'max_tokens': 1000
        }
    
    @pytest.fixture
    def mock_agent(self):
        """Create a mock CrewAI agent."""
        agent = Mock()
        agent.role = "Test Agent"
        agent.goal = "Test goal"
        agent.backstory = "Test backstory"
        agent.verbose = True
        agent.allow_delegation = False
        return agent
    
    @pytest.fixture
    def mock_task(self):
        """Create a mock CrewAI task."""
        task = Mock()
        task.description = "Test task description"
        task.expected_output = "Test expected output"
        return task
    
    @pytest.fixture
    def mock_crew(self):
        """Create a mock CrewAI crew."""
        crew = Mock()
        crew.kickoff = Mock(return_value="Mock crew result")
        return crew
    
    @patch('app.core.multi_agent.get_llm_info')
    @patch('app.core.multi_agent.get_llm')
    def test_initialization_success(self, mock_get_llm, mock_get_llm_info, mock_llm, mock_llm_info):
        """Test successful initialization of MultiAgentOrchestrator."""
        # Setup mocks
        mock_get_llm_info.return_value = mock_llm_info
        mock_get_llm.return_value = mock_llm
        
        with patch.object(MultiAgentOrchestrator, '_create_agents') as mock_create_agents:
            mock_create_agents.return_value = {
                'researcher': Mock(),
                'analyst': Mock(),
                'writer': Mock(),
                'coordinator': Mock()
            }
            
            # Initialize orchestrator
            orchestrator = MultiAgentOrchestrator()
            
            # Verify initialization
            assert orchestrator.llm_info == mock_llm_info
            assert orchestrator.llm == mock_llm
            assert len(orchestrator.agents) == 4
            assert 'researcher' in orchestrator.agents
            assert 'analyst' in orchestrator.agents
            assert 'writer' in orchestrator.agents
            assert 'coordinator' in orchestrator.agents
            
            # Verify method calls
            mock_get_llm_info.assert_called_once()
            mock_get_llm.assert_called_once()
            mock_create_agents.assert_called_once()
    
    @patch('app.core.multi_agent.get_llm_info')
    @patch('app.core.multi_agent.get_llm')
    def test_initialization_llm_failure(self, mock_get_llm, mock_get_llm_info, mock_llm_info):
        """Test initialization when LLM fails to load."""
        # Setup mocks
        mock_get_llm_info.return_value = mock_llm_info
        mock_get_llm.side_effect = Exception("LLM initialization failed")
        
        with patch.object(MultiAgentOrchestrator, '_create_agents') as mock_create_agents:
            mock_create_agents.return_value = {
                'researcher': {'role': 'Research Specialist', 'mock': True},
                'analyst': {'role': 'Data Analyst', 'mock': True},
                'writer': {'role': 'Content Writer', 'mock': True},
                'coordinator': {'role': 'Project Coordinator', 'mock': True}
            }
            
            # Initialize orchestrator
            orchestrator = MultiAgentOrchestrator()
            
            # Verify fallback behavior
            assert orchestrator.llm is None
            assert orchestrator.agents['researcher']['mock'] is True
            mock_create_agents.assert_called_once()
    
    @patch('app.core.multi_agent.get_llm_info')
    @patch('app.core.multi_agent.get_llm')
    @patch('app.core.llm_config.get_specialized_llm')
    @patch('crewai.Agent')
    def test_create_agents_success(self, mock_agent_class, mock_get_specialized_llm,
                                 mock_get_llm, mock_get_llm_info, mock_llm, mock_llm_info, mock_agent):
        """Test successful agent creation."""
        # Setup mocks
        mock_get_llm_info.return_value = mock_llm_info
        mock_get_llm.return_value = mock_llm
        mock_get_specialized_llm.return_value = mock_llm
        mock_agent_class.return_value = mock_agent
        
        with patch.object(MultiAgentOrchestrator, '_create_search_tool') as mock_create_search_tool:
            mock_create_search_tool.return_value = Mock()
            
            # Initialize orchestrator
            orchestrator = MultiAgentOrchestrator()
            
            # Verify agents were created
            assert len(orchestrator.agents) == 4
            assert all(isinstance(agent, Mock) for agent in orchestrator.agents.values())
            
            # Verify specialized LLM calls
            assert mock_get_specialized_llm.call_count == 4
            mock_get_specialized_llm.assert_any_call('researcher')
            mock_get_specialized_llm.assert_any_call('analyst')
            mock_get_specialized_llm.assert_any_call('writer')
            mock_get_specialized_llm.assert_any_call('coordinator')
    
    @patch('app.core.multi_agent.get_llm_info')
    @patch('app.core.multi_agent.get_llm')
    @patch('app.core.llm_config.get_specialized_llm')
    def test_create_agents_failure(self, mock_get_specialized_llm, mock_get_llm,
                                 mock_get_llm_info, mock_llm, mock_llm_info):
        """Test agent creation failure and fallback to mock agents."""
        # Setup mocks
        mock_get_llm_info.return_value = mock_llm_info
        mock_get_llm.return_value = mock_llm
        mock_get_specialized_llm.side_effect = Exception("Agent creation failed")
        
        # Initialize orchestrator
        orchestrator = MultiAgentOrchestrator()
        
        # Verify fallback to mock agents
        assert len(orchestrator.agents) == 4
        assert orchestrator.agents['researcher']['mock'] is True
        assert orchestrator.agents['analyst']['mock'] is True
        assert orchestrator.agents['writer']['mock'] is True
        assert orchestrator.agents['coordinator']['mock'] is True
    
    @patch('app.core.multi_agent.SerperDevTool')
    def test_create_search_tool_serper_success(self, mock_serper_tool):
        """Test successful creation of SerperDevTool."""
        mock_tool = Mock()
        mock_serper_tool.return_value = mock_tool
        
        orchestrator = MultiAgentOrchestrator.__new__(MultiAgentOrchestrator)
        result = orchestrator._create_search_tool()
        
        assert result == mock_tool
        mock_serper_tool.assert_called_once()
    
    @patch('crewai_tools.SerperDevTool')
    @patch('crewai_tools.tool')
    @patch('app.core.multi_agent.duckduckgo_search')
    def test_create_search_tool_fallback_to_duckduckgo(self, mock_duckduckgo_search,
                                                     mock_tool_decorator, mock_serper_tool):
        """Test fallback to DuckDuckGo search when SerperDevTool fails."""
        # Setup mocks
        mock_serper_tool.side_effect = Exception("SerperDevTool failed")
        mock_search_tool = Mock()
        mock_tool_decorator.return_value = mock_search_tool
        mock_duckduckgo_search.return_value = "Search results"
        
        orchestrator = MultiAgentOrchestrator.__new__(MultiAgentOrchestrator)
        result = orchestrator._create_search_tool()
        
        assert result == mock_search_tool
        mock_tool_decorator.assert_called_once_with("DuckDuckGo Search")
    
    @patch('crewai_tools.SerperDevTool')
    @patch('crewai_tools.tool')
    def test_create_search_tool_complete_failure(self, mock_tool_decorator, mock_serper_tool):
        """Test complete search tool creation failure."""
        # Setup mocks to fail
        mock_serper_tool.side_effect = Exception("SerperDevTool failed")
        mock_tool_decorator.side_effect = Exception("DuckDuckGo tool failed")
        
        orchestrator = MultiAgentOrchestrator.__new__(MultiAgentOrchestrator)
        result = orchestrator._create_search_tool()
        
        assert result is None
    
    def test_create_mock_agents(self):
        """Test creation of mock agents."""
        orchestrator = MultiAgentOrchestrator.__new__(MultiAgentOrchestrator)
        mock_agents = orchestrator._create_mock_agents()
        
        assert len(mock_agents) == 4
        assert mock_agents['researcher']['role'] == 'Research Specialist'
        assert mock_agents['researcher']['mock'] is True
        assert mock_agents['analyst']['role'] == 'Data Analyst'
        assert mock_agents['analyst']['mock'] is True
        assert mock_agents['writer']['role'] == 'Content Writer'
        assert mock_agents['writer']['mock'] is True
        assert mock_agents['coordinator']['role'] == 'Project Coordinator'
        assert mock_agents['coordinator']['mock'] is True
    
    def test_create_research_task(self, mock_task):
        """Test creation of research task."""
        # Create orchestrator with mock agent
        orchestrator = MultiAgentOrchestrator.__new__(MultiAgentOrchestrator)
        mock_agent = Mock()
        orchestrator.agents = {'researcher': mock_agent}

        query = "Test research query"
        context = "Test context"

        # Mock the Task constructor to avoid CrewAI validation issues
        with patch('app.core.multi_agent.Task') as mock_task_class:
            mock_task_class.return_value = mock_task

            result = orchestrator.create_research_task(query, context)

            assert result == mock_task
            mock_task_class.assert_called_once()

            # Verify task creation arguments
            call_args = mock_task_class.call_args
            assert query in call_args.kwargs['description']
            assert context in call_args.kwargs['description']
            assert call_args.kwargs['agent'] == orchestrator.agents['researcher']
            assert "research summary" in call_args.kwargs['expected_output'].lower()
    
    def test_create_analysis_task(self, mock_task):
        """Test creation of analysis task."""
        # Create orchestrator with mock agent
        orchestrator = MultiAgentOrchestrator.__new__(MultiAgentOrchestrator)
        mock_agent = Mock()
        orchestrator.agents = {'analyst': mock_agent}

        research_data = "Test research data"
        analysis_focus = "Test analysis focus"

        # Mock the Task constructor to avoid CrewAI validation issues
        with patch('app.core.multi_agent.Task') as mock_task_class:
            mock_task_class.return_value = mock_task

            result = orchestrator.create_analysis_task(research_data, analysis_focus)

            assert result == mock_task
            mock_task_class.assert_called_once()

            # Verify task creation arguments
            call_args = mock_task_class.call_args
            assert research_data in call_args.kwargs['description']
            assert analysis_focus in call_args.kwargs['description']
            assert call_args.kwargs['agent'] == orchestrator.agents['analyst']
            assert "analysis" in call_args.kwargs['expected_output'].lower()
    
    def test_create_writing_task(self, mock_task):
        """Test creation of writing task."""
        # Create orchestrator with mock agent
        orchestrator = MultiAgentOrchestrator.__new__(MultiAgentOrchestrator)
        mock_agent = Mock()
        orchestrator.agents = {'writer': mock_agent}

        content_brief = "Test content brief"
        style = "informative"

        # Mock the Task constructor to avoid CrewAI validation issues
        with patch('app.core.multi_agent.Task') as mock_task_class:
            mock_task_class.return_value = mock_task

            result = orchestrator.create_writing_task(content_brief, style)

            assert result == mock_task
            mock_task_class.assert_called_once()

            # Verify task creation arguments
            call_args = mock_task_class.call_args
            assert content_brief in call_args.kwargs['description']
            assert style in call_args.kwargs['description']
            assert call_args.kwargs['agent'] == orchestrator.agents['writer']
            assert "content" in call_args.kwargs['expected_output'].lower()

    @patch('app.core.multi_agent.duckduckgo_search')
    def test_execute_simple_query_with_mock_agents(self, mock_duckduckgo_search):
        """Test execute_simple_query with mock agents (fallback behavior)."""
        mock_duckduckgo_search.return_value = "Fallback search results"

        # Create orchestrator with no LLM (triggers mock agents)
        orchestrator = MultiAgentOrchestrator.__new__(MultiAgentOrchestrator)
        orchestrator.llm = None
        orchestrator.agents = {'researcher': {'role': 'Research Specialist', 'mock': True}}

        query = "Test query"
        context = "Test context"

        result = orchestrator.execute_simple_query(query, context)

        # Verify fallback behavior
        assert result['query'] == query
        assert result['result'] == "Fallback search results"
        assert result['agents_used'] == ["fallback_search"]
        assert result['task_type'] == "fallback_search"
        assert "fallback search" in result['note']

        mock_duckduckgo_search.assert_called_once_with(query)

    @patch('crewai.Crew')
    @patch('crewai.Task')
    def test_execute_simple_query_with_real_agents(self, mock_task_class, mock_crew_class,
                                                  mock_task, mock_crew):
        """Test execute_simple_query with real agents."""
        # Setup mocks
        mock_task_class.return_value = mock_task
        mock_crew_class.return_value = mock_crew
        mock_crew.kickoff.return_value = "Crew execution result"

        # Create orchestrator with real LLM and agents
        orchestrator = MultiAgentOrchestrator.__new__(MultiAgentOrchestrator)
        orchestrator.llm = Mock()
        orchestrator.agents = {'researcher': Mock()}

        # Mock the create_research_task method
        with patch.object(orchestrator, 'create_research_task') as mock_create_research_task:
            mock_create_research_task.return_value = mock_task

            query = "Test query"
            context = "Test context"

            result = orchestrator.execute_simple_query(query, context)

            # Verify successful execution
            assert result['query'] == query
            assert result['result'] == "Crew execution result"
            assert result['agents_used'] == ["researcher"]
            assert result['task_type'] == "simple_research"

            # Verify method calls
            mock_create_research_task.assert_called_once_with(query, context)
            mock_crew_class.assert_called_once()
            mock_crew.kickoff.assert_called_once()

    @patch('crewai.Crew')
    @patch('app.core.multi_agent.duckduckgo_search')
    def test_execute_simple_query_crew_failure(self, mock_duckduckgo_search, mock_crew_class):
        """Test execute_simple_query when crew execution fails."""
        # Setup mocks
        mock_crew_class.side_effect = Exception("Crew execution failed")
        mock_duckduckgo_search.return_value = "Fallback search results"

        # Create orchestrator with real LLM and agents
        orchestrator = MultiAgentOrchestrator.__new__(MultiAgentOrchestrator)
        orchestrator.llm = Mock()
        orchestrator.agents = {'researcher': Mock()}

        # Mock the create_research_task method
        with patch.object(orchestrator, 'create_research_task') as mock_create_research_task:
            mock_create_research_task.return_value = Mock()

            query = "Test query"

            result = orchestrator.execute_simple_query(query)

            # Verify fallback behavior
            assert result['query'] == query
            assert result['result'] == "Fallback search results"
            assert result['agents_used'] == ["fallback_search"]
            assert result['task_type'] == "fallback_search"
            assert 'error' in result

            mock_duckduckgo_search.assert_called_once_with(query)

    def test_execute_complex_workflow_with_mock_agents(self):
        """Test execute_complex_workflow with mock agents (fallback behavior)."""
        # Create orchestrator with no LLM (triggers mock agents)
        orchestrator = MultiAgentOrchestrator.__new__(MultiAgentOrchestrator)
        orchestrator.llm = None
        orchestrator.agents = {'researcher': {'role': 'Research Specialist', 'mock': True}}

        # Mock the execute_simple_query method
        with patch.object(orchestrator, 'execute_simple_query') as mock_execute_simple:
            mock_execute_simple.return_value = {"result": "Simple query result"}

            query = "Test complex query"
            workflow_type = "research_analyze_write"

            result = orchestrator.execute_complex_workflow(query, workflow_type)

            # Verify fallback to simple query
            assert result == {"result": "Simple query result"}
            mock_execute_simple.assert_called_once_with(query)

    @patch('crewai.Crew')
    @patch('crewai.Task')
    def test_execute_complex_workflow_research_analyze_write(self, mock_task_class, mock_crew_class,
                                                           mock_task, mock_crew):
        """Test execute_complex_workflow with research_analyze_write workflow."""
        # Setup mocks
        mock_task_class.return_value = mock_task
        mock_crew_class.return_value = mock_crew
        mock_crew.kickoff.return_value = "Complex workflow result"

        # Create orchestrator with real LLM and agents
        orchestrator = MultiAgentOrchestrator.__new__(MultiAgentOrchestrator)
        orchestrator.llm = Mock()
        orchestrator.agents = {
            'researcher': Mock(),
            'analyst': Mock(),
            'writer': Mock()
        }

        # Mock the create_research_task method
        with patch.object(orchestrator, 'create_research_task') as mock_create_research_task:
            mock_create_research_task.return_value = mock_task

            query = "Test complex query"
            workflow_type = "research_analyze_write"

            result = orchestrator.execute_complex_workflow(query, workflow_type)

            # Verify successful execution
            assert result['query'] == query
            assert result['result'] == "Complex workflow result"
            assert result['agents_used'] == ["researcher", "analyst", "writer"]
            assert result['task_type'] == workflow_type
            assert result['workflow_steps'] == 3

            # Verify method calls
            mock_create_research_task.assert_called_once_with(query)
            mock_crew_class.assert_called_once()
            mock_crew.kickoff.assert_called_once()

            # Verify crew was created with correct agents and tasks
            crew_call_args = mock_crew_class.call_args
            assert len(crew_call_args.kwargs['agents']) == 3
            assert len(crew_call_args.kwargs['tasks']) == 3

    @patch('crewai.Crew')
    def test_execute_complex_workflow_failure(self, mock_crew_class):
        """Test execute_complex_workflow when crew execution fails."""
        # Setup mocks
        mock_crew_class.side_effect = Exception("Complex workflow failed")

        # Create orchestrator with real LLM and agents
        orchestrator = MultiAgentOrchestrator.__new__(MultiAgentOrchestrator)
        orchestrator.llm = Mock()
        orchestrator.agents = {
            'researcher': Mock(),
            'analyst': Mock(),
            'writer': Mock()
        }

        # Mock the execute_simple_query method for fallback
        with patch.object(orchestrator, 'execute_simple_query') as mock_execute_simple:
            mock_execute_simple.return_value = {"result": "Fallback result"}

            query = "Test complex query"

            result = orchestrator.execute_complex_workflow(query)

            # Verify fallback to simple query
            assert result == {"result": "Fallback result"}
            mock_execute_simple.assert_called_once_with(query)

    def test_get_agent_capabilities(self):
        """Test get_agent_capabilities method."""
        orchestrator = MultiAgentOrchestrator.__new__(MultiAgentOrchestrator)

        capabilities = orchestrator.get_agent_capabilities()

        # Verify structure and content
        assert isinstance(capabilities, dict)
        assert len(capabilities) == 4

        # Check each agent capability
        for agent_name in ['researcher', 'analyst', 'writer', 'coordinator']:
            assert agent_name in capabilities
            agent_info = capabilities[agent_name]
            assert 'role' in agent_info
            assert 'capabilities' in agent_info
            assert 'tools' in agent_info
            assert isinstance(agent_info['role'], str)
            assert isinstance(agent_info['capabilities'], str)
            assert isinstance(agent_info['tools'], str)

        # Verify specific agent roles
        assert capabilities['researcher']['role'] == "Research Specialist"
        assert capabilities['analyst']['role'] == "Data Analyst"
        assert capabilities['writer']['role'] == "Content Writer"
        assert capabilities['coordinator']['role'] == "Project Coordinator"


class TestMultiAgentOrchestrator_EdgeCases:
    """Test edge cases and error scenarios for MultiAgentOrchestrator."""

    def test_execute_simple_query_empty_query(self):
        """Test execute_simple_query with empty query."""
        orchestrator = MultiAgentOrchestrator.__new__(MultiAgentOrchestrator)
        orchestrator.llm = None
        orchestrator.agents = {'researcher': {'mock': True}}

        with patch('app.core.multi_agent.duckduckgo_search') as mock_search:
            mock_search.return_value = "Empty query search result"

            result = orchestrator.execute_simple_query("")

            assert result['query'] == ""
            assert result['task_type'] == "fallback_search"
            mock_search.assert_called_once_with("")

    def test_execute_simple_query_none_query(self):
        """Test execute_simple_query with None query."""
        orchestrator = MultiAgentOrchestrator.__new__(MultiAgentOrchestrator)
        orchestrator.llm = None
        orchestrator.agents = {'researcher': {'mock': True}}

        with patch('app.core.multi_agent.duckduckgo_search') as mock_search:
            mock_search.return_value = "None query search result"

            result = orchestrator.execute_simple_query(None)

            assert result['query'] is None
            assert result['task_type'] == "fallback_search"
            mock_search.assert_called_once_with(None)

    def test_execute_complex_workflow_unknown_workflow_type(self):
        """Test execute_complex_workflow with unknown workflow type."""
        orchestrator = MultiAgentOrchestrator.__new__(MultiAgentOrchestrator)
        orchestrator.llm = Mock()
        orchestrator.agents = {'researcher': Mock()}

        with patch.object(orchestrator, 'execute_simple_query') as mock_execute_simple:
            mock_execute_simple.return_value = {"result": "Fallback result"}

            query = "Test query"
            unknown_workflow = "unknown_workflow_type"

            result = orchestrator.execute_complex_workflow(query, unknown_workflow)

            # Should fallback to simple query for unknown workflow types
            assert result == {"result": "Fallback result"}
            mock_execute_simple.assert_called_once_with(query)

    def test_create_research_task_with_empty_context(self):
        """Test create_research_task with empty context."""
        mock_task = Mock()

        orchestrator = MultiAgentOrchestrator.__new__(MultiAgentOrchestrator)
        mock_agent = Mock()
        orchestrator.agents = {'researcher': mock_agent}

        query = "Test query"
        context = ""

        # Mock the Task constructor to avoid CrewAI validation issues
        with patch('app.core.multi_agent.Task') as mock_task_class:
            mock_task_class.return_value = mock_task

            result = orchestrator.create_research_task(query, context)

            assert result == mock_task
            call_args = mock_task_class.call_args
            assert query in call_args.kwargs['description']
            assert context in call_args.kwargs['description']

    def test_create_analysis_task_with_empty_focus(self):
        """Test create_analysis_task with empty analysis focus."""
        mock_task = Mock()

        orchestrator = MultiAgentOrchestrator.__new__(MultiAgentOrchestrator)
        mock_agent = Mock()
        orchestrator.agents = {'analyst': mock_agent}

        research_data = "Test research data"
        analysis_focus = ""

        # Mock the Task constructor to avoid CrewAI validation issues
        with patch('app.core.multi_agent.Task') as mock_task_class:
            mock_task_class.return_value = mock_task

            result = orchestrator.create_analysis_task(research_data, analysis_focus)

            assert result == mock_task
            call_args = mock_task_class.call_args
            assert research_data in call_args.kwargs['description']
            assert analysis_focus in call_args.kwargs['description']

    def test_create_writing_task_default_style(self):
        """Test create_writing_task with default style."""
        mock_task = Mock()

        orchestrator = MultiAgentOrchestrator.__new__(MultiAgentOrchestrator)
        mock_agent = Mock()
        orchestrator.agents = {'writer': mock_agent}

        content_brief = "Test content brief"

        # Mock the Task constructor to avoid CrewAI validation issues
        with patch('app.core.multi_agent.Task') as mock_task_class:
            mock_task_class.return_value = mock_task

            result = orchestrator.create_writing_task(content_brief)

            assert result == mock_task
            call_args = mock_task_class.call_args
            assert content_brief in call_args.kwargs['description']
            assert "informative" in call_args.kwargs['description']  # Default style

    def test_agents_property_access(self):
        """Test accessing agents property when not initialized."""
        orchestrator = MultiAgentOrchestrator.__new__(MultiAgentOrchestrator)

        # Should not raise an error even if agents not initialized
        try:
            agents = orchestrator.agents
            # If agents is not set, it should be None or empty dict
            assert agents is None or isinstance(agents, dict)
        except AttributeError:
            # This is acceptable behavior for uninitialized orchestrator
            pass

    def test_llm_property_access(self):
        """Test accessing llm property when not initialized."""
        orchestrator = MultiAgentOrchestrator.__new__(MultiAgentOrchestrator)

        # Should not raise an error even if llm not initialized
        try:
            llm = orchestrator.llm
            # If llm is not set, it should be None
            assert llm is None or hasattr(llm, 'invoke')
        except AttributeError:
            # This is acceptable behavior for uninitialized orchestrator
            pass


class TestMultiAgentOrchestrator_Integration:
    """Integration tests for MultiAgentOrchestrator with real-like scenarios."""

    @patch('app.core.multi_agent.get_llm_info')
    @patch('app.core.multi_agent.get_llm')
    @patch('app.core.llm_config.get_specialized_llm')
    @patch('crewai.Agent')
    @patch('crewai.Task')
    @patch('crewai.Crew')
    def test_full_workflow_integration(self, mock_crew_class, mock_task_class, mock_agent_class,
                                     mock_get_specialized_llm, mock_get_llm, mock_get_llm_info):
        """Test full workflow integration from initialization to execution."""
        # Setup mocks
        mock_llm_info = {'provider': 'test', 'model_name': 'test_model'}
        mock_llm = Mock()
        mock_agent = Mock()
        mock_task = Mock()
        mock_crew = Mock()

        mock_get_llm_info.return_value = mock_llm_info
        mock_get_llm.return_value = mock_llm
        mock_get_specialized_llm.return_value = mock_llm
        mock_agent_class.return_value = mock_agent
        mock_task_class.return_value = mock_task
        mock_crew_class.return_value = mock_crew
        mock_crew.kickoff.return_value = "Integration test result"

        with patch.object(MultiAgentOrchestrator, '_create_search_tool') as mock_create_search_tool:
            mock_create_search_tool.return_value = Mock()

            # Full integration test
            orchestrator = MultiAgentOrchestrator()

            # Test simple query execution
            simple_result = orchestrator.execute_simple_query("Test simple query")
            assert simple_result['result'] == "Integration test result"
            assert simple_result['task_type'] == "simple_research"

            # Test complex workflow execution
            complex_result = orchestrator.execute_complex_workflow("Test complex query")
            assert complex_result['result'] == "Integration test result"
            assert complex_result['task_type'] == "research_analyze_write"
            assert complex_result['workflow_steps'] == 3

            # Verify all components were called
            assert mock_get_llm.called
            assert mock_get_specialized_llm.called
            assert mock_agent_class.called
            assert mock_crew_class.called

    @patch('app.core.multi_agent.duckduckgo_search')
    def test_complete_fallback_scenario(self, mock_duckduckgo_search):
        """Test complete fallback scenario when all components fail."""
        mock_duckduckgo_search.return_value = "Fallback search result"

        # Create orchestrator that will fail at every step
        with patch('app.core.multi_agent.get_llm') as mock_get_llm:
            mock_get_llm.side_effect = Exception("LLM failed")

            orchestrator = MultiAgentOrchestrator()

            # Should fallback to search for both simple and complex queries
            simple_result = orchestrator.execute_simple_query("Test query")
            assert simple_result['task_type'] == "fallback_search"
            assert simple_result['result'] == "Fallback search result"

            complex_result = orchestrator.execute_complex_workflow("Test query")
            assert complex_result['task_type'] == "fallback_search"
            assert complex_result['result'] == "Fallback search result"

    def test_agent_capabilities_consistency(self):
        """Test that agent capabilities are consistent with actual agent creation."""
        orchestrator = MultiAgentOrchestrator.__new__(MultiAgentOrchestrator)

        capabilities = orchestrator.get_agent_capabilities()
        expected_agents = ['researcher', 'analyst', 'writer', 'coordinator']

        # Verify all expected agents are present
        for agent_name in expected_agents:
            assert agent_name in capabilities

        # Verify capabilities structure is consistent
        for agent_name, agent_info in capabilities.items():
            assert 'role' in agent_info
            assert 'capabilities' in agent_info
            assert 'tools' in agent_info
            assert len(agent_info['role']) > 0
            assert len(agent_info['capabilities']) > 0
            assert len(agent_info['tools']) > 0


# Test the global instance
class TestGlobalMultiAgentOrchestrator:
    """Test the global multi_agent_orchestrator instance."""

    def test_global_instance_exists(self):
        """Test that global instance exists and is accessible."""
        from app.core.multi_agent import multi_agent_orchestrator

        assert multi_agent_orchestrator is not None
        assert isinstance(multi_agent_orchestrator, MultiAgentOrchestrator)

    def test_global_instance_has_required_methods(self):
        """Test that global instance has all required methods."""
        from app.core.multi_agent import multi_agent_orchestrator

        required_methods = [
            'execute_simple_query',
            'execute_complex_workflow',
            'create_research_task',
            'create_analysis_task',
            'create_writing_task',
            'get_agent_capabilities'
        ]

        for method_name in required_methods:
            assert hasattr(multi_agent_orchestrator, method_name)
            assert callable(getattr(multi_agent_orchestrator, method_name))
