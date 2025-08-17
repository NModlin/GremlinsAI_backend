# tests/integration/test_crew_ai.py
"""
Integration tests for CrewAI multi-agent system.

Tests cover:
- Full crew initialization and execution
- Agent specialization verification
- Complex multi-step task coordination
- Tool integration across agents
- Measurable specialization for blind testing
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, MagicMock

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from app.core.crew_manager import CrewManager, CrewResult, CREWAI_AVAILABLE
    from app.core.llm_manager import ProductionLLMManager
    from app.tools import get_tool_registry
except ImportError as e:
    pytest.skip(f"CrewAI dependencies not available: {e}", allow_module_level=True)


@pytest.mark.skipif(not CREWAI_AVAILABLE, reason="CrewAI not available")
class TestCrewAIIntegration:
    """Integration tests for CrewAI multi-agent system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        try:
            self.crew_manager = CrewManager()
        except Exception as e:
            pytest.skip(f"Could not initialize CrewManager: {e}")
    
    def test_crew_manager_initialization(self):
        """Test that CrewManager initializes correctly."""
        assert self.crew_manager is not None
        assert hasattr(self.crew_manager, 'agents')
        assert hasattr(self.crew_manager, 'tools')
        assert hasattr(self.crew_manager, 'crew')
        
        # Check that all required agents are created
        expected_agents = ['researcher', 'analyst', 'writer', 'coordinator']
        for agent_name in expected_agents:
            assert agent_name in self.crew_manager.agents
        
        # Check that tools are available
        assert len(self.crew_manager.tools) > 0
        
        # Check that crew is properly configured
        assert self.crew_manager.crew is not None
        assert len(self.crew_manager.crew.agents) == 4
    
    def test_agent_specialization(self):
        """Test that agents have measurable specialization."""
        capabilities = self.crew_manager.get_agent_capabilities()
        
        # Test that all agents exist
        expected_agents = ['researcher', 'analyst', 'writer', 'coordinator']
        for agent_name in expected_agents:
            assert agent_name in capabilities
        
        # Test researcher specialization
        researcher = capabilities['researcher']
        assert 'research' in researcher['role'].lower()
        assert len(researcher['tools']) > 0
        assert any('search' in tool for tool in researcher['tools'])
        
        # Test analyst specialization
        analyst = capabilities['analyst']
        assert 'analyst' in analyst['role'].lower()
        assert len(analyst['tools']) > 0
        analyst_tools = analyst['tools']
        assert any('calculator' in tool or 'code' in tool for tool in analyst_tools)
        
        # Test writer specialization
        writer = capabilities['writer']
        assert 'writer' in writer['role'].lower()
        assert len(writer['tools']) > 0
        assert any('text' in tool for tool in writer['tools'])
        
        # Test coordinator specialization
        coordinator = capabilities['coordinator']
        assert 'coordinator' in coordinator['role'].lower()
        assert coordinator['can_delegate'] is True
        
        # Test specialization scores
        for agent_name, agent_caps in capabilities.items():
            assert 'specialization_score' in agent_caps
            assert 0.0 <= agent_caps['specialization_score'] <= 1.0
    
    def test_blind_specialization_testing(self):
        """Test measurable specialization for blind testing requirements."""
        specialization_results = self.crew_manager.test_agent_specialization()
        
        # Test individual agent specializations
        assert specialization_results['researcher_has_search_tools'] is True
        assert specialization_results['researcher_specialization_score'] is True
        
        assert specialization_results['analyst_has_calculation_tools'] is True
        assert specialization_results['analyst_specialization_score'] is True
        
        assert specialization_results['writer_has_text_tools'] is True
        assert specialization_results['writer_specialization_score'] is True
        
        assert specialization_results['coordinator_can_delegate'] is True
        assert specialization_results['coordinator_specialization_score'] is True
        
        # Test overall specialization
        assert specialization_results['all_agents_specialized'] is True
        assert specialization_results['agents_have_distinct_roles'] is True
    
    def test_tool_integration(self):
        """Test that tools are properly integrated with agents."""
        # Test that tool wrappers are created
        assert 'web_search' in self.crew_manager.tools
        assert 'calculator' in self.crew_manager.tools
        assert 'code_interpreter' in self.crew_manager.tools
        assert 'text_processor' in self.crew_manager.tools
        assert 'json_processor' in self.crew_manager.tools
        
        # Test tool wrapper functionality
        web_search_tool = self.crew_manager.tools['web_search']
        assert hasattr(web_search_tool, '_run')
        assert web_search_tool.tool_name == 'web_search'
        assert 'search' in web_search_tool.description.lower()
        
        calculator_tool = self.crew_manager.tools['calculator']
        assert hasattr(calculator_tool, '_run')
        assert calculator_tool.tool_name == 'calculator'
        assert 'mathematical' in calculator_tool.description.lower()
    
    def test_collaborative_task_creation(self):
        """Test that collaborative tasks are created correctly for queries."""
        query = "What are the benefits of renewable energy?"
        tasks = self.crew_manager._create_collaborative_tasks(query)

        assert len(tasks) == 4  # Research, Analysis, Writing, Coordination

        # Check task assignments
        task_agents = [task.agent.role for task in tasks]
        expected_roles = ['Research Specialist', 'Data Analyst', 'Content Writer', 'Project Coordinator']

        for expected_role in expected_roles:
            assert expected_role in task_agents

        # Check task dependencies (context)
        research_task, analysis_task, writing_task, coordination_task = tasks

        # Analysis should depend on research
        assert research_task in analysis_task.context

        # Writing should depend on research and analysis
        assert research_task in writing_task.context
        assert analysis_task in writing_task.context

        # Coordination should depend on all previous tasks
        assert research_task in coordination_task.context
        assert analysis_task in coordination_task.context
        assert writing_task in coordination_task.context

        # Check for collaboration keywords in task descriptions
        collaboration_keywords = ['DELEGATE', 'REQUEST', 'COLLABORATE', 'COORDINATE']
        collaborative_tasks = 0

        for task in tasks:
            if any(keyword in task.description for keyword in collaboration_keywords):
                collaborative_tasks += 1

        assert collaborative_tasks >= 3, "At least 3 tasks should have collaboration instructions"

    def test_agent_delegation_capabilities(self):
        """Test that agents have proper delegation capabilities."""
        capabilities = self.crew_manager.get_agent_capabilities()

        # Check that multiple agents can delegate (not just coordinator)
        delegation_agents = [name for name, caps in capabilities.items() if caps.get('can_delegate', False)]
        assert len(delegation_agents) >= 3, "At least 3 agents should be able to delegate"

        # Verify specific agents can delegate
        assert capabilities['researcher']['can_delegate'] is True
        assert capabilities['analyst']['can_delegate'] is True
        assert capabilities['writer']['can_delegate'] is True
        assert capabilities['coordinator']['can_delegate'] is True

    def test_collaborative_workflow_validation(self):
        """Test collaborative workflow capabilities."""
        workflow_results = self.crew_manager.test_collaborative_workflow()

        # Test core collaboration features
        assert workflow_results['delegation_enabled'] is True
        assert workflow_results['collaborative_agents'] >= 3
        assert workflow_results['task_interconnection'] is True
        assert workflow_results['information_flow'] is True
        assert workflow_results['multi_agent_coordination'] is True

        # Test collaboration metrics
        assert workflow_results['collaboration_score'] >= 0.8  # 80% or higher
        assert workflow_results['workflow_complexity'] >= 4  # At least 4 tasks
        assert workflow_results['delegation_coverage'] >= 0.75  # 75% of agents can delegate
    
    @pytest.mark.asyncio
    @patch('app.tools.web_search.web_search')
    @patch('app.tools.calculator.calculate')
    @patch('app.tools.text_processor.process_text')
    async def test_simple_query_execution(self, mock_text_processor, mock_calculator, mock_web_search):
        """Test execution of a simple query with mocked tools."""
        # Mock tool responses
        from app.tools.base_tool import ToolResult
        
        mock_web_search.return_value = ToolResult(
            success=True,
            result=[{
                'title': 'Renewable Energy Benefits',
                'url': 'https://example.com/renewable',
                'snippet': 'Renewable energy provides clean, sustainable power with environmental benefits.'
            }]
        )
        
        mock_calculator.return_value = ToolResult(
            success=True,
            result=42.5
        )
        
        mock_text_processor.return_value = ToolResult(
            success=True,
            result="Processed text about renewable energy benefits"
        )
        
        # Mock CrewAI execution
        with patch.object(self.crew_manager.crew, 'kickoff') as mock_kickoff:
            mock_kickoff.return_value = "Renewable energy offers significant environmental and economic benefits including reduced carbon emissions, energy independence, and long-term cost savings."
            
            # Execute query
            result = await self.crew_manager.execute_query("What are the benefits of renewable energy?")
            
            # Verify result
            assert isinstance(result, CrewResult)
            assert result.success is True
            assert len(result.result) > 0
            assert 'renewable energy' in result.result.lower()
            assert result.execution_time > 0
            assert len(result.agent_outputs) > 0
    
    @pytest.mark.asyncio
    @patch('app.tools.web_search.web_search')
    @patch('app.tools.calculator.calculate')
    @patch('app.tools.code_interpreter.execute_python_code')
    async def test_complex_collaborative_workflow(self, mock_code_interpreter, mock_calculator, mock_web_search):
        """Test execution of a complex collaborative workflow requiring all three agents."""
        # Mock tool responses for collaborative analysis
        from app.tools.base_tool import ToolResult

        # Researcher's web search results
        mock_web_search.return_value = ToolResult(
            success=True,
            result=[
                {
                    'title': 'AI Model Performance Benchmarks 2024',
                    'url': 'https://example.com/ai-benchmarks',
                    'snippet': 'Comprehensive analysis of GPT-4, Claude 3, and Gemini Pro performance across multiple domains.'
                },
                {
                    'title': 'Large Language Model Comparison Study',
                    'url': 'https://example.com/llm-comparison',
                    'snippet': 'GPT-4 achieves 85% accuracy in reasoning, Claude 3 leads in safety with 92% satisfaction, Gemini Pro excels in multimodal tasks.'
                },
                {
                    'title': 'Enterprise AI Adoption Report 2024',
                    'url': 'https://example.com/enterprise-ai',
                    'snippet': 'Organizations report varying success rates with different AI models based on use case requirements.'
                }
            ]
        )

        # Analyst's calculation results
        mock_calculator.return_value = ToolResult(
            success=True,
            result=88.3  # Average performance score across models
        )

        # Analyst's code execution results
        mock_code_interpreter.return_value = ToolResult(
            success=True,
            result="""
Performance Analysis Results:
- GPT-4: 85% reasoning accuracy, 78% safety score
- Claude 3: 82% reasoning accuracy, 92% safety score
- Gemini Pro: 87% reasoning accuracy, 85% safety score
- Average overall performance: 88.3%
- Best for reasoning: Gemini Pro (87%)
- Best for safety: Claude 3 (92%)
- Most balanced: GPT-4 (81.5% average)
            """
        )

        # Mock CrewAI execution for collaborative workflow
        with patch.object(self.crew_manager.crew, 'kickoff') as mock_kickoff:
            mock_kickoff.return_value = """
            # Comprehensive AI Model Analysis: Top 3 Models of 2024

            ## Research Findings (Research Specialist)
            Based on comprehensive research across multiple sources, the top 3 AI models of 2024 are:
            - GPT-4: Leading general-purpose language model
            - Claude 3: Safety-focused conversational AI
            - Gemini Pro: Multimodal AI with strong reasoning capabilities

            ## Quantitative Analysis (Data Analyst)
            Performance metrics analysis reveals:
            - Average performance score: 88.3% across all models
            - GPT-4: 85% reasoning accuracy, 78% safety score
            - Claude 3: 82% reasoning accuracy, 92% safety score
            - Gemini Pro: 87% reasoning accuracy, 85% safety score

            ## Key Strengths Summary (Content Writer)
            **GPT-4 Strengths:**
            - Superior general intelligence and reasoning
            - Excellent performance across diverse tasks
            - Strong creative and analytical capabilities

            **Claude 3 Strengths:**
            - Industry-leading safety and helpfulness (92% satisfaction)
            - Excellent for sensitive or regulated applications
            - Strong ethical reasoning and harm prevention

            **Gemini Pro Strengths:**
            - Outstanding multimodal capabilities
            - Best-in-class reasoning accuracy (87%)
            - Efficient performance and resource utilization

            ## Conclusion (Project Coordinator)
            This analysis demonstrates successful collaboration between research, analysis, and writing teams. Each model excels in different areas, with the choice depending on specific use case requirements: GPT-4 for general intelligence, Claude 3 for safety-critical applications, and Gemini Pro for multimodal reasoning tasks.
            """

            # Execute complex collaborative query
            result = await self.crew_manager.execute_query(
                "Research the performance of the top 3 AI models in 2024, analyze their key strengths using quantitative methods, and write a comprehensive summary that reflects the contributions of all team members."
            )

            # Verify collaborative result
            assert isinstance(result, CrewResult)
            assert result.success is True
            assert len(result.result) > 200  # Should be a substantial collaborative response

            # Check that result contains contributions from all agents
            result_lower = result.result.lower()

            # Research contributions
            assert any(model in result_lower for model in ['gpt-4', 'claude', 'gemini'])
            assert 'research' in result_lower

            # Analysis contributions
            assert 'analysis' in result_lower or 'performance' in result_lower
            assert '88.3' in result.result or 'average' in result_lower

            # Writing contributions
            assert 'summary' in result_lower or 'conclusion' in result_lower
            assert 'strengths' in result_lower

            # Coordination contributions
            assert 'collaboration' in result_lower or 'team' in result_lower

            # Verify collaboration metrics
            assert hasattr(result, 'collaboration_metrics')
            collab_metrics = result.collaboration_metrics
            assert collab_metrics['total_agents_involved'] >= 3
            assert collab_metrics['delegation_enabled_agents'] >= 3
            assert collab_metrics['task_dependencies'] > 0
            assert len(collab_metrics['collaboration_patterns']) > 0

            # Check agent outputs for collaboration indicators
            assert len(result.agent_outputs) >= 3

            # Verify each agent's contribution
            agent_outputs = result.agent_outputs
            for agent_name, output in agent_outputs.items():
                assert output['can_delegate'] is True or agent_name == 'project_coordinator'
                if agent_name != 'research_specialist':  # Non-research agents should have context
                    assert output['has_context'] is True

            assert result.execution_time > 0
    
    def test_error_handling(self):
        """Test error handling in crew execution."""
        # Test with invalid query that might cause issues
        with patch.object(self.crew_manager.crew, 'kickoff') as mock_kickoff:
            mock_kickoff.side_effect = Exception("Simulated crew execution error")
            
            # This should be run in an async context
            async def run_test():
                result = await self.crew_manager.execute_query("Invalid query that causes errors")
                
                assert isinstance(result, CrewResult)
                assert result.success is False
                assert result.error_message is not None
                assert "crew execution failed" in result.error_message.lower()
                assert result.execution_time > 0
            
            # Run the async test
            asyncio.run(run_test())
    
    def test_crew_manager_singleton(self):
        """Test that crew manager can be used as singleton."""
        from app.core.crew_manager import get_crew_manager
        
        manager1 = get_crew_manager()
        manager2 = get_crew_manager()
        
        # Should return the same instance
        assert manager1 is manager2
        assert isinstance(manager1, CrewManager)


@pytest.mark.skipif(not CREWAI_AVAILABLE, reason="CrewAI not available")
class TestCrewAIPerformance:
    """Performance tests for CrewAI system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        try:
            self.crew_manager = CrewManager()
        except Exception as e:
            pytest.skip(f"Could not initialize CrewManager: {e}")
    
    def test_initialization_performance(self):
        """Test that crew initialization is reasonably fast."""
        start_time = time.time()
        
        # Create a new crew manager
        crew_manager = CrewManager()
        
        initialization_time = time.time() - start_time
        
        # Should initialize within 5 seconds
        assert initialization_time < 5.0
        assert crew_manager is not None
    
    def test_task_creation_performance(self):
        """Test that task creation is efficient."""
        start_time = time.time()
        
        # Create tasks for a complex query
        query = "Analyze the economic impact of artificial intelligence on global markets"
        tasks = self.crew_manager._create_tasks_for_query(query)
        
        creation_time = time.time() - start_time
        
        # Should create tasks quickly
        assert creation_time < 1.0
        assert len(tasks) == 4
    
    @pytest.mark.asyncio
    async def test_execution_timeout_handling(self):
        """Test that execution handles timeouts gracefully."""
        # Mock a slow execution
        with patch.object(self.crew_manager.crew, 'kickoff') as mock_kickoff:
            def slow_execution():
                time.sleep(0.1)  # Simulate some work
                return "Completed after delay"
            
            mock_kickoff.side_effect = slow_execution
            
            start_time = time.time()
            result = await self.crew_manager.execute_query("Test query")
            execution_time = time.time() - start_time
            
            # Should complete and measure time correctly
            assert result.success is True
            assert execution_time >= 0.1
            assert abs(result.execution_time - execution_time) < 0.1


if __name__ == "__main__":
    pytest.main([__file__])
