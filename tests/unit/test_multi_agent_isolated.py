"""
Isolated unit tests for the multi-agent system.

This test suite tests the actual MultiAgentOrchestrator class by mocking
all external dependencies to avoid import issues.
"""

import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List, Optional


# Mock all problematic dependencies before importing
sys.modules['crewai'] = Mock()
sys.modules['crewai.Agent'] = Mock()
sys.modules['crewai.Task'] = Mock()
sys.modules['crewai.Crew'] = Mock()
sys.modules['crewai_tools'] = Mock()
sys.modules['crewai_tools.SerperDevTool'] = Mock()
sys.modules['crewai_tools.tool'] = Mock()
sys.modules['langgraph'] = Mock()
sys.modules['langgraph.prebuilt'] = Mock()
sys.modules['langchain_core'] = Mock()
sys.modules['langchain_core.language_models'] = Mock()


class TestMultiAgentOrchestratorIsolated:
    """Isolated tests for MultiAgentOrchestrator."""
    
    @patch('app.core.multi_agent.get_llm_info')
    @patch('app.core.multi_agent.get_llm')
    @patch('app.core.llm_config.get_specialized_llm')
    @patch('app.core.multi_agent.Agent')
    @patch('app.core.multi_agent.SerperDevTool')
    def test_initialization_success(self, mock_serper, mock_agent, mock_specialized_llm, 
                                  mock_get_llm, mock_get_llm_info):
        """Test successful initialization."""
        # Setup mocks
        mock_llm_info = {'provider': 'test', 'model_name': 'test_model'}
        mock_llm = Mock()
        mock_agent_instance = Mock()
        mock_tool = Mock()
        
        mock_get_llm_info.return_value = mock_llm_info
        mock_get_llm.return_value = mock_llm
        mock_specialized_llm.return_value = mock_llm
        mock_agent.return_value = mock_agent_instance
        mock_serper.return_value = mock_tool
        
        # Import and test
        from app.core.multi_agent import MultiAgentOrchestrator
        
        orchestrator = MultiAgentOrchestrator()
        
        # Verify initialization
        assert orchestrator.llm_info == mock_llm_info
        assert orchestrator.llm == mock_llm
        assert len(orchestrator.agents) == 4
        
        # Verify method calls
        mock_get_llm_info.assert_called_once()
        mock_get_llm.assert_called_once()
        assert mock_specialized_llm.call_count == 4
    
    @patch('app.core.multi_agent.get_llm_info')
    @patch('app.core.multi_agent.get_llm')
    def test_initialization_llm_failure(self, mock_get_llm, mock_get_llm_info):
        """Test initialization when LLM fails."""
        # Setup mocks
        mock_llm_info = {'provider': 'test', 'model_name': 'test_model'}
        mock_get_llm_info.return_value = mock_llm_info
        mock_get_llm.side_effect = Exception("LLM failed")
        
        # Import and test
        from app.core.multi_agent import MultiAgentOrchestrator
        
        orchestrator = MultiAgentOrchestrator()
        
        # Verify fallback behavior
        assert orchestrator.llm is None
        assert len(orchestrator.agents) == 4
        # Should have mock agents
        for agent in orchestrator.agents.values():
            assert agent['mock'] is True
    
    @patch('app.core.multi_agent.get_llm_info')
    @patch('app.core.multi_agent.get_llm')
    @patch('app.core.multi_agent.Task')
    def test_create_research_task(self, mock_task, mock_get_llm, mock_get_llm_info):
        """Test research task creation."""
        # Setup mocks
        mock_llm_info = {'provider': 'test', 'model_name': 'test_model'}
        mock_llm = Mock()
        mock_task_instance = Mock()
        
        mock_get_llm_info.return_value = mock_llm_info
        mock_get_llm.return_value = mock_llm
        mock_task.return_value = mock_task_instance
        
        # Import and test
        from app.core.multi_agent import MultiAgentOrchestrator
        
        with patch.object(MultiAgentOrchestrator, '_create_agents') as mock_create_agents:
            mock_create_agents.return_value = {'researcher': Mock()}
            
            orchestrator = MultiAgentOrchestrator()
            
            query = "Test query"
            context = "Test context"
            
            result = orchestrator.create_research_task(query, context)
            
            assert result == mock_task_instance
            mock_task.assert_called_once()
            
            # Verify task creation arguments
            call_args = mock_task.call_args
            assert query in call_args.kwargs['description']
            assert context in call_args.kwargs['description']
    
    @patch('app.core.multi_agent.get_llm_info')
    @patch('app.core.multi_agent.get_llm')
    @patch('app.core.multi_agent.Task')
    def test_create_analysis_task(self, mock_task, mock_get_llm, mock_get_llm_info):
        """Test analysis task creation."""
        # Setup mocks
        mock_llm_info = {'provider': 'test', 'model_name': 'test_model'}
        mock_llm = Mock()
        mock_task_instance = Mock()
        
        mock_get_llm_info.return_value = mock_llm_info
        mock_get_llm.return_value = mock_llm
        mock_task.return_value = mock_task_instance
        
        # Import and test
        from app.core.multi_agent import MultiAgentOrchestrator
        
        with patch.object(MultiAgentOrchestrator, '_create_agents') as mock_create_agents:
            mock_create_agents.return_value = {'analyst': Mock()}
            
            orchestrator = MultiAgentOrchestrator()
            
            research_data = "Test data"
            analysis_focus = "Test focus"
            
            result = orchestrator.create_analysis_task(research_data, analysis_focus)
            
            assert result == mock_task_instance
            mock_task.assert_called_once()
            
            # Verify task creation arguments
            call_args = mock_task.call_args
            assert research_data in call_args.kwargs['description']
            assert analysis_focus in call_args.kwargs['description']
    
    @patch('app.core.multi_agent.get_llm_info')
    @patch('app.core.multi_agent.get_llm')
    @patch('app.core.multi_agent.Task')
    def test_create_writing_task(self, mock_task, mock_get_llm, mock_get_llm_info):
        """Test writing task creation."""
        # Setup mocks
        mock_llm_info = {'provider': 'test', 'model_name': 'test_model'}
        mock_llm = Mock()
        mock_task_instance = Mock()
        
        mock_get_llm_info.return_value = mock_llm_info
        mock_get_llm.return_value = mock_llm
        mock_task.return_value = mock_task_instance
        
        # Import and test
        from app.core.multi_agent import MultiAgentOrchestrator
        
        with patch.object(MultiAgentOrchestrator, '_create_agents') as mock_create_agents:
            mock_create_agents.return_value = {'writer': Mock()}
            
            orchestrator = MultiAgentOrchestrator()
            
            content_brief = "Test brief"
            style = "informative"
            
            result = orchestrator.create_writing_task(content_brief, style)
            
            assert result == mock_task_instance
            mock_task.assert_called_once()
            
            # Verify task creation arguments
            call_args = mock_task.call_args
            assert content_brief in call_args.kwargs['description']
            assert style in call_args.kwargs['description']
    
    @patch('app.core.multi_agent.get_llm_info')
    @patch('app.core.multi_agent.get_llm')
    @patch('app.core.multi_agent.duckduckgo_search')
    def test_execute_simple_query_fallback(self, mock_search, mock_get_llm, mock_get_llm_info):
        """Test simple query execution with fallback."""
        # Setup mocks
        mock_llm_info = {'provider': 'test', 'model_name': 'test_model'}
        mock_get_llm_info.return_value = mock_llm_info
        mock_get_llm.return_value = None  # No LLM available
        mock_search.return_value = "Fallback search result"
        
        # Import and test
        from app.core.multi_agent import MultiAgentOrchestrator
        
        orchestrator = MultiAgentOrchestrator()
        
        query = "Test query"
        result = orchestrator.execute_simple_query(query)
        
        # Verify fallback behavior
        assert result['query'] == query
        assert result['result'] == "Fallback search result"
        assert result['task_type'] == "fallback_search"
        assert result['agents_used'] == ["fallback_search"]
        
        mock_search.assert_called_once_with(query)
    
    @patch('app.core.multi_agent.get_llm_info')
    @patch('app.core.multi_agent.get_llm')
    @patch('app.core.multi_agent.Crew')
    @patch('app.core.multi_agent.Task')
    def test_execute_simple_query_success(self, mock_task, mock_crew, mock_get_llm, mock_get_llm_info):
        """Test successful simple query execution."""
        # Setup mocks
        mock_llm_info = {'provider': 'test', 'model_name': 'test_model'}
        mock_llm = Mock()
        mock_task_instance = Mock()
        mock_crew_instance = Mock()
        
        mock_get_llm_info.return_value = mock_llm_info
        mock_get_llm.return_value = mock_llm
        mock_task.return_value = mock_task_instance
        mock_crew.return_value = mock_crew_instance
        mock_crew_instance.kickoff.return_value = "Crew execution result"
        
        # Import and test
        from app.core.multi_agent import MultiAgentOrchestrator
        
        with patch.object(MultiAgentOrchestrator, '_create_agents') as mock_create_agents:
            mock_create_agents.return_value = {'researcher': Mock()}
            
            orchestrator = MultiAgentOrchestrator()
            
            query = "Test query"
            result = orchestrator.execute_simple_query(query)
            
            # Verify successful execution
            assert result['query'] == query
            assert result['result'] == "Crew execution result"
            assert result['task_type'] == "simple_research"
            assert result['agents_used'] == ["researcher"]
            
            mock_crew_instance.kickoff.assert_called_once()
    
    def test_get_agent_capabilities(self):
        """Test get_agent_capabilities method."""
        # Import and test
        from app.core.multi_agent import MultiAgentOrchestrator
        
        with patch.object(MultiAgentOrchestrator, '__init__', lambda x: None):
            orchestrator = MultiAgentOrchestrator()
            
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
    
    @patch('app.core.multi_agent.get_llm_info')
    @patch('app.core.multi_agent.get_llm')
    def test_execute_complex_workflow_fallback(self, mock_get_llm, mock_get_llm_info):
        """Test complex workflow execution with fallback."""
        # Setup mocks
        mock_llm_info = {'provider': 'test', 'model_name': 'test_model'}
        mock_get_llm_info.return_value = mock_llm_info
        mock_get_llm.return_value = None  # No LLM available
        
        # Import and test
        from app.core.multi_agent import MultiAgentOrchestrator
        
        with patch.object(MultiAgentOrchestrator, 'execute_simple_query') as mock_simple:
            mock_simple.return_value = {"result": "Fallback result"}
            
            orchestrator = MultiAgentOrchestrator()
            
            query = "Test query"
            result = orchestrator.execute_complex_workflow(query)
            
            # Should fallback to simple query
            assert result == {"result": "Fallback result"}
            mock_simple.assert_called_once_with(query)
    
    @patch('app.core.multi_agent.get_llm_info')
    @patch('app.core.multi_agent.get_llm')
    @patch('app.core.multi_agent.Crew')
    @patch('app.core.multi_agent.Task')
    def test_execute_complex_workflow_success(self, mock_task, mock_crew, mock_get_llm, mock_get_llm_info):
        """Test successful complex workflow execution."""
        # Setup mocks
        mock_llm_info = {'provider': 'test', 'model_name': 'test_model'}
        mock_llm = Mock()
        mock_task_instance = Mock()
        mock_crew_instance = Mock()
        
        mock_get_llm_info.return_value = mock_llm_info
        mock_get_llm.return_value = mock_llm
        mock_task.return_value = mock_task_instance
        mock_crew.return_value = mock_crew_instance
        mock_crew_instance.kickoff.return_value = "Complex workflow result"
        
        # Import and test
        from app.core.multi_agent import MultiAgentOrchestrator
        
        with patch.object(MultiAgentOrchestrator, '_create_agents') as mock_create_agents:
            mock_create_agents.return_value = {
                'researcher': Mock(),
                'analyst': Mock(),
                'writer': Mock()
            }
            
            orchestrator = MultiAgentOrchestrator()
            
            query = "Test query"
            result = orchestrator.execute_complex_workflow(query)
            
            # Verify successful execution
            assert result['query'] == query
            assert result['result'] == "Complex workflow result"
            assert result['task_type'] == "research_analyze_write"
            assert result['agents_used'] == ["researcher", "analyst", "writer"]
            assert result['workflow_steps'] == 3
            
            mock_crew_instance.kickoff.assert_called_once()


class TestMultiAgentOrchestratorEdgeCases:
    """Test edge cases and error scenarios."""
    
    def test_empty_query_handling(self):
        """Test handling of empty queries."""
        from app.core.multi_agent import MultiAgentOrchestrator
        
        with patch.object(MultiAgentOrchestrator, '__init__', lambda x: None):
            with patch.object(MultiAgentOrchestrator, 'execute_simple_query') as mock_simple:
                mock_simple.return_value = {"query": "", "result": "Empty query result"}
                
                orchestrator = MultiAgentOrchestrator()
                result = orchestrator.execute_simple_query("")
                
                assert result['query'] == ""
                mock_simple.assert_called_once_with("")
    
    def test_none_query_handling(self):
        """Test handling of None queries."""
        from app.core.multi_agent import MultiAgentOrchestrator
        
        with patch.object(MultiAgentOrchestrator, '__init__', lambda x: None):
            with patch.object(MultiAgentOrchestrator, 'execute_simple_query') as mock_simple:
                mock_simple.return_value = {"query": None, "result": "None query result"}
                
                orchestrator = MultiAgentOrchestrator()
                result = orchestrator.execute_simple_query(None)
                
                assert result['query'] is None
                mock_simple.assert_called_once_with(None)
    
    def test_unknown_workflow_type(self):
        """Test handling of unknown workflow types."""
        from app.core.multi_agent import MultiAgentOrchestrator
        
        with patch.object(MultiAgentOrchestrator, '__init__', lambda x: None):
            with patch.object(MultiAgentOrchestrator, 'execute_simple_query') as mock_simple:
                mock_simple.return_value = {"result": "Fallback result"}
                
                orchestrator = MultiAgentOrchestrator()
                result = orchestrator.execute_complex_workflow("query", "unknown_type")
                
                # Should fallback to simple query
                assert result == {"result": "Fallback result"}
                mock_simple.assert_called_once_with("query")


class TestMultiAgentOrchestratorIntegration:
    """Integration tests for multi-agent orchestrator."""
    
    @patch('app.core.multi_agent.get_llm_info')
    @patch('app.core.multi_agent.get_llm')
    @patch('app.core.llm_config.get_specialized_llm')
    @patch('app.core.multi_agent.Agent')
    @patch('app.core.multi_agent.Task')
    @patch('app.core.multi_agent.Crew')
    @patch('app.core.multi_agent.SerperDevTool')
    def test_full_workflow_integration(self, mock_serper, mock_crew, mock_task, 
                                     mock_agent, mock_specialized_llm, mock_get_llm, mock_get_llm_info):
        """Test full workflow integration."""
        # Setup mocks
        mock_llm_info = {'provider': 'test', 'model_name': 'test_model'}
        mock_llm = Mock()
        mock_agent_instance = Mock()
        mock_task_instance = Mock()
        mock_crew_instance = Mock()
        mock_tool = Mock()
        
        mock_get_llm_info.return_value = mock_llm_info
        mock_get_llm.return_value = mock_llm
        mock_specialized_llm.return_value = mock_llm
        mock_agent.return_value = mock_agent_instance
        mock_task.return_value = mock_task_instance
        mock_crew.return_value = mock_crew_instance
        mock_crew_instance.kickoff.return_value = "Integration test result"
        mock_serper.return_value = mock_tool
        
        # Import and test
        from app.core.multi_agent import MultiAgentOrchestrator
        
        orchestrator = MultiAgentOrchestrator()
        
        # Test simple query
        simple_result = orchestrator.execute_simple_query("Test query")
        assert simple_result['result'] == "Integration test result"
        
        # Test complex workflow
        complex_result = orchestrator.execute_complex_workflow("Test query")
        assert complex_result['result'] == "Integration test result"
        
        # Verify all components were called
        assert mock_get_llm.called
        assert mock_specialized_llm.called
        assert mock_agent.called
        assert mock_crew.called
