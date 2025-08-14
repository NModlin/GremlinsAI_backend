# app/core/multi_agent.py
import logging
from typing import Dict, Any, List, Optional
from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool, WebsiteSearchTool
from langchain_openai import ChatOpenAI
from app.core.tools import duckduckgo_search

logger = logging.getLogger(__name__)

class MultiAgentOrchestrator:
    """
    Multi-agent orchestrator using CrewAI for complex reasoning and task coordination.
    Manages specialized agents for different types of tasks.
    """
    
    def __init__(self, llm_model: str = "gpt-3.5-turbo", temperature: float = 0.1):
        """Initialize the multi-agent orchestrator."""
        self.llm_model = llm_model
        self.temperature = temperature
        self.llm = self._initialize_llm()
        self.agents = self._create_agents()
        
    def _initialize_llm(self):
        """Initialize the language model for agents."""
        try:
            # Try to use OpenAI if API key is available
            return ChatOpenAI(
                model=self.llm_model,
                temperature=self.temperature
            )
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI LLM: {e}")
            # Fallback to a mock LLM for development/testing
            return None
    
    def _create_agents(self) -> Dict[str, Agent]:
        """Create specialized agents for different tasks."""
        agents = {}

        # Only create agents if we have a valid LLM
        if self.llm is None:
            logger.warning("No LLM available, creating mock agents")
            return self._create_mock_agents()

        # Research Agent - Specializes in information gathering
        agents['researcher'] = Agent(
            role='Research Specialist',
            goal='Gather comprehensive and accurate information on given topics',
            backstory="""You are an expert researcher with years of experience in
            information gathering and fact-checking. You excel at finding reliable
            sources and synthesizing information from multiple perspectives.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
            tools=[self._create_search_tool()]
        )
        
        # Analyst Agent - Specializes in data analysis and insights
        agents['analyst'] = Agent(
            role='Data Analyst',
            goal='Analyze information and provide insights and recommendations',
            backstory="""You are a skilled data analyst with expertise in pattern 
            recognition, critical thinking, and drawing meaningful conclusions from 
            complex information. You excel at identifying trends and relationships.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
        
        # Writer Agent - Specializes in content creation and communication
        agents['writer'] = Agent(
            role='Content Writer',
            goal='Create clear, engaging, and well-structured content',
            backstory="""You are an experienced writer and communicator who excels 
            at taking complex information and presenting it in a clear, engaging, 
            and accessible manner. You adapt your writing style to the audience.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
        
        # Coordinator Agent - Manages workflow and task delegation
        agents['coordinator'] = Agent(
            role='Project Coordinator',
            goal='Coordinate tasks and ensure efficient workflow between agents',
            backstory="""You are an experienced project manager who excels at 
            breaking down complex tasks, coordinating team efforts, and ensuring 
            quality deliverables. You understand how to leverage each team member's strengths.""",
            verbose=True,
            allow_delegation=True,
            llm=self.llm
        )
        
        return agents
    
    def _create_search_tool(self):
        """Create a search tool for the research agent."""
        from langchain.tools import BaseTool
        from typing import Type

        class DDGSearchTool(BaseTool):
            name: str = "duckduckgo_search"
            description: str = "Search the web using DuckDuckGo for current information"

            def _run(self, query: str) -> str:
                """Execute the search."""
                return duckduckgo_search(query)

            async def _arun(self, query: str) -> str:
                """Async version of the search."""
                return duckduckgo_search(query)

        return DDGSearchTool()

    def _create_mock_agents(self) -> Dict[str, Any]:
        """Create mock agents when no LLM is available."""
        return {
            'researcher': {'role': 'Research Specialist', 'mock': True},
            'analyst': {'role': 'Data Analyst', 'mock': True},
            'writer': {'role': 'Content Writer', 'mock': True},
            'coordinator': {'role': 'Project Coordinator', 'mock': True}
        }
    
    def create_research_task(self, query: str, context: str = "") -> Task:
        """Create a research task for the research agent."""
        return Task(
            description=f"""
            Research the following topic thoroughly: {query}
            
            Context: {context}
            
            Your task is to:
            1. Gather comprehensive information about the topic
            2. Find multiple reliable sources
            3. Identify key facts, trends, and perspectives
            4. Provide a well-structured research summary
            
            Focus on accuracy and comprehensiveness.
            """,
            agent=self.agents['researcher'],
            expected_output="A comprehensive research summary with key findings and sources"
        )
    
    def create_analysis_task(self, research_data: str, analysis_focus: str = "") -> Task:
        """Create an analysis task for the analyst agent."""
        return Task(
            description=f"""
            Analyze the following research data and provide insights:
            
            Research Data: {research_data}
            Analysis Focus: {analysis_focus}
            
            Your task is to:
            1. Identify key patterns and trends
            2. Draw meaningful conclusions
            3. Provide actionable insights
            4. Highlight important implications
            5. Suggest recommendations if applicable
            
            Focus on critical thinking and practical insights.
            """,
            agent=self.agents['analyst'],
            expected_output="Detailed analysis with insights, conclusions, and recommendations"
        )
    
    def create_writing_task(self, content_brief: str, style: str = "informative") -> Task:
        """Create a writing task for the writer agent."""
        return Task(
            description=f"""
            Create well-written content based on the following brief:
            
            Content Brief: {content_brief}
            Writing Style: {style}
            
            Your task is to:
            1. Structure the content logically
            2. Write in a clear and engaging manner
            3. Adapt the tone to the specified style
            4. Ensure accuracy and completeness
            5. Make the content accessible to the target audience
            
            Focus on clarity, engagement, and value to the reader.
            """,
            agent=self.agents['writer'],
            expected_output="Well-structured, engaging content that meets the brief requirements"
        )
    
    def execute_simple_query(self, query: str, context: str = "") -> Dict[str, Any]:
        """Execute a simple query using the research agent."""
        try:
            logger.info(f"Executing simple query: {query}")

            # Check if we have real agents or mock agents
            if self.llm is None or self.agents.get('researcher', {}).get('mock', False):
                logger.info("Using fallback search due to missing LLM")
                search_result = duckduckgo_search(query)
                return {
                    "query": query,
                    "result": search_result,
                    "agents_used": ["fallback_search"],
                    "task_type": "fallback_search",
                    "note": "Used fallback search due to missing LLM configuration"
                }

            # Create a research task
            research_task = self.create_research_task(query, context)

            # Create a crew with just the researcher
            crew = Crew(
                agents=[self.agents['researcher']],
                tasks=[research_task],
                verbose=True,
                process=Process.sequential
            )

            # Execute the task
            result = crew.kickoff()

            return {
                "query": query,
                "result": str(result),
                "agents_used": ["researcher"],
                "task_type": "simple_research"
            }

        except Exception as e:
            logger.error(f"Error executing simple query: {e}")
            # Fallback to basic search if CrewAI fails
            search_result = duckduckgo_search(query)
            return {
                "query": query,
                "result": search_result,
                "agents_used": ["fallback_search"],
                "task_type": "fallback_search",
                "error": str(e)
            }
    
    def execute_complex_workflow(self, query: str, workflow_type: str = "research_analyze_write") -> Dict[str, Any]:
        """Execute a complex multi-agent workflow."""
        try:
            logger.info(f"Executing complex workflow: {workflow_type} for query: {query}")

            # Check if we have real agents or mock agents
            if self.llm is None or self.agents.get('researcher', {}).get('mock', False):
                logger.info("Falling back to simple query due to missing LLM")
                return self.execute_simple_query(query)

            tasks = []
            agents_used = []

            if workflow_type == "research_analyze_write":
                # Step 1: Research
                research_task = self.create_research_task(query)
                tasks.append(research_task)
                agents_used.append("researcher")

                # Step 2: Analysis (depends on research)
                analysis_task = Task(
                    description=f"""
                    Analyze the research findings from the previous task about: {query}

                    Provide insights, identify patterns, and draw conclusions.
                    Focus on practical implications and actionable insights.
                    """,
                    agent=self.agents['analyst'],
                    expected_output="Detailed analysis with insights and recommendations"
                )
                tasks.append(analysis_task)
                agents_used.append("analyst")

                # Step 3: Writing (depends on analysis)
                writing_task = Task(
                    description=f"""
                    Create a comprehensive, well-structured response based on the research
                    and analysis from previous tasks about: {query}

                    Make it informative, engaging, and accessible to a general audience.
                    Include key findings, insights, and practical implications.
                    """,
                    agent=self.agents['writer'],
                    expected_output="Well-written, comprehensive response"
                )
                tasks.append(writing_task)
                agents_used.append("writer")

            # Create and execute the crew
            crew = Crew(
                agents=[self.agents[agent] for agent in agents_used],
                tasks=tasks,
                verbose=True,
                process=Process.sequential
            )

            result = crew.kickoff()

            return {
                "query": query,
                "result": str(result),
                "agents_used": agents_used,
                "task_type": workflow_type,
                "workflow_steps": len(tasks)
            }

        except Exception as e:
            logger.error(f"Error executing complex workflow: {e}")
            # Fallback to simple query
            return self.execute_simple_query(query)
    
    def get_agent_capabilities(self) -> Dict[str, Dict[str, str]]:
        """Get information about available agents and their capabilities."""
        return {
            "researcher": {
                "role": "Research Specialist",
                "capabilities": "Information gathering, fact-checking, source verification",
                "tools": "Web search, data collection"
            },
            "analyst": {
                "role": "Data Analyst", 
                "capabilities": "Pattern recognition, critical analysis, insights generation",
                "tools": "Data analysis, trend identification"
            },
            "writer": {
                "role": "Content Writer",
                "capabilities": "Content creation, communication, audience adaptation",
                "tools": "Writing, editing, content structuring"
            },
            "coordinator": {
                "role": "Project Coordinator",
                "capabilities": "Task management, workflow coordination, quality assurance",
                "tools": "Project management, delegation, coordination"
            }
        }


# Global instance for use across the application
multi_agent_orchestrator = MultiAgentOrchestrator()
