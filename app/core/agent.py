# app/core/agent.py
"""
Production Agent with ReAct (Reasoning and Acting) Pattern Implementation

This module implements a production-grade agent that uses the ReAct pattern:
1. Reason about the user's query to decide on a course of action
2. Act by selecting and using a tool
3. Observe the result and repeat until the query is answered

The agent supports multi-step reasoning and can handle complex problems
requiring multiple tool calls.
"""

import logging
import re
import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Union, Any, Tuple
from datetime import datetime

from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from typing import TypedDict, Annotated
import operator

from app.core.tools import duckduckgo_search, sanitize_input
from app.core.llm_manager import ProductionLLMManager, ConversationContext
from app.core.context_store import get_context_store
from app.monitoring.metrics import metrics
from app.core.memory_manager import MemoryManager
from app.tools import get_tool_registry
from app.core.task_planner import get_task_planner, ExecutionPlan, PlanStep, PlanStepStatus
from app.core.agent_learning import get_learning_service, AgentLearning

logger = logging.getLogger(__name__)

@dataclass
class ReasoningStep:
    """Represents a single step in the ReAct reasoning process."""
    step_number: int
    thought: str
    action: Optional[str] = None
    action_input: Optional[str] = None
    observation: Optional[str] = None
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class AgentResult:
    """Result of agent execution."""
    final_answer: str
    reasoning_steps: List[ReasoningStep]
    total_steps: int
    success: bool
    error_message: Optional[str] = None
    execution_plan: Optional[ExecutionPlan] = None
    plan_used: bool = False


class AgentState(TypedDict):
    """State for the agent graph."""
    messages: Annotated[list[BaseMessage], operator.add]
    agent_outcome: Union[AgentAction, AgentFinish, None]
    reasoning_steps: List[ReasoningStep]
    current_step: int

class ProductionAgent:
    """
    Production-grade agent implementing advanced planning with ReAct execution.

    The agent now follows an enhanced reasoning loop:
    1. Planning: Analyze complex goals and create structured execution plans
    2. Execution: Execute plan steps using appropriate tools
    3. Monitoring: Track progress and adjust plans as needed
    4. Fallback: Use traditional ReAct pattern for simple queries

    Features:
    - Advanced goal decomposition and planning
    - Multi-step plan execution with dependency management
    - Dynamic plan adjustment based on execution results
    - Tool selection and execution
    - Error handling and recovery
    - Conversation context management
    - Performance monitoring
    """

    def __init__(self, max_iterations: int = 10, max_execution_time: int = 300,
                 planning_threshold: float = 0.3, weaviate_client=None):
        """
        Initialize the ProductionAgent with planning, memory, and learning capabilities.

        Args:
            max_iterations: Maximum number of reasoning steps
            max_execution_time: Maximum execution time in seconds
            planning_threshold: Complexity threshold for using planning vs ReAct
            weaviate_client: Optional Weaviate client for learning storage
        """
        self.llm_manager = ProductionLLMManager()
        self.max_iterations = max_iterations
        self.max_execution_time = max_execution_time
        self.planning_threshold = planning_threshold

        # Memory and context management
        self.context_store = get_context_store()
        self.memory_manager = MemoryManager()

        # Task planner for complex goals
        self.task_planner = get_task_planner()

        # Learning service for adaptation
        self.learning_service = get_learning_service(weaviate_client)

        # Get tool registry
        self.tool_registry = get_tool_registry()

        # Available tools (legacy + new comprehensive tools)
        self.tools = {
            "search": self._search_tool,
            "final_answer": self._final_answer_tool,
            # Add all registered tools
            **{name: self._create_tool_wrapper(name) for name in self.tool_registry.list_tools()}
        }

        # ReAct prompt template
        self.react_prompt = self._create_react_prompt()

        logger.info(f"ProductionAgent initialized with {len(self.tools)} tools, planning, memory, and learning system")

    async def _assess_query_complexity(self, query: str) -> float:
        """
        Assess the complexity of a query to determine if planning is needed.

        Args:
            query: The user query to assess

        Returns:
            Complexity score between 0.0 and 1.0
        """
        try:
            # Use LLM to assess complexity
            complexity_prompt = f"""Analyze the following query and assess its complexity on a scale of 0.0 to 1.0:

0.0-0.2: Simple queries (basic facts, single calculations, direct questions)
0.3-0.5: Moderate queries (research tasks, comparisons, multi-step problems)
0.6-0.8: Complex queries (analysis, planning, creative tasks, multi-domain problems)
0.9-1.0: Very complex queries (strategic planning, comprehensive research, multi-step projects)

Consider these factors:
- Number of steps required
- Domain knowledge needed
- Tools and resources required
- Time and effort involved
- Interdependencies between tasks

Query: "{query}"

Respond with only a number between 0.0 and 1.0 representing the complexity score."""

            response = await self.llm_manager.generate_response(
                prompt=complexity_prompt,
                max_tokens=50,
                temperature=0.1
            )

            # Extract numeric score
            import re
            score_match = re.search(r'(\d+\.?\d*)', response.strip())
            if score_match:
                score = float(score_match.group(1))
                return min(max(score, 0.0), 1.0)  # Clamp between 0.0 and 1.0
            else:
                logger.warning(f"Could not parse complexity score from: {response}")
                return 0.5  # Default to moderate complexity

        except Exception as e:
            logger.error(f"Error assessing query complexity: {e}")
            return 0.5  # Default to moderate complexity

    def _create_tool_wrapper(self, tool_name: str):
        """Create a wrapper function for a registered tool."""
        async def tool_wrapper(*args, **kwargs):
            try:
                result = await self.tool_registry.execute_tool(tool_name, *args, **kwargs)
                if result.success:
                    return f"Tool '{tool_name}' result: {result.result}"
                else:
                    return f"Tool '{tool_name}' error: {result.error_message}"
            except Exception as e:
                logger.error(f"Error executing tool {tool_name}: {e}")
                return f"Tool '{tool_name}' execution failed: {str(e)}"

        return tool_wrapper

    def _create_react_prompt(self) -> str:
        """Create the ReAct prompt template with all available tools."""
        # Get tool descriptions
        tool_descriptions = []
        tool_descriptions.append("- search: Search for information using DuckDuckGo")
        tool_descriptions.append("- final_answer: Provide the final answer to the user's question")

        # Add descriptions for all registered tools
        for tool_name in self.tool_registry.list_tools():
            tool_info = self.tool_registry.get_tool(tool_name)
            if tool_info:
                tool_descriptions.append(f"- {tool_name}: {tool_info.description}")

        tools_text = "\n".join(tool_descriptions)

        return f"""You are a helpful AI assistant that uses the ReAct (Reasoning and Acting) pattern to solve problems.

You have access to the following tools:
{tools_text}

{{memory_context}}

Use the following format for your reasoning:

Thought: [Your reasoning about what to do next, considering any relevant information from previous interactions]
Action: [The action to take - choose from the available tools above]
Action Input: [The input for the action]

You will then receive an observation with the result of your action.

Continue this process until you can provide a final answer. You can use multiple tools in sequence to solve complex problems.

IMPORTANT: Consider any user preferences, past interactions, and key information from the memory context when reasoning and providing answers.

Examples:

User: What is the capital of France?
Thought: This is a straightforward question about geography. I should search for information about France's capital.
Action: search
Action Input: capital of France

Observation: Paris is the capital and most populous city of France...

Thought: I have found the answer. Paris is the capital of France.
Action: final_answer
Action Input: The capital of France is Paris.

User: Calculate the square root of 144 and then encode the result in base64
Thought: I need to calculate the square root of 144 first.
Action: calculator
Action Input: sqrt(144)

Observation: Tool 'calculator' result: 12.0

Thought: Now I need to encode "12.0" in base64.
Action: base64_tool
Action Input: encode 12.0

Observation: Tool 'base64_tool' result: MTIuMA==

Thought: I have calculated the square root and encoded it. The answer is complete.
Action: final_answer
Action Input: The square root of 144 is 12.0, and when encoded in base64, it becomes "MTIuMA==".

User: {{user_query}}"""

    def _search_tool(self, query: str) -> str:
        """Execute search tool."""
        import time
        start_time = time.time()
        success = True

        try:
            sanitized_query = sanitize_input(query)
            result = duckduckgo_search(sanitized_query)
            return f"Search results: {result}"
        except Exception as e:
            logger.error(f"Search tool error: {e}")
            success = False
            return f"Search failed: {str(e)}"
        finally:
            duration = time.time() - start_time
            metrics.record_tool_usage(
                agent_type="production_agent",
                tool_name="search",
                duration=duration,
                success=success
            )

    def _final_answer_tool(self, answer: str) -> str:
        """Provide final answer."""
        return f"Final Answer: {answer}"

    def _parse_llm_response(self, response: str) -> Tuple[str, Optional[str], Optional[str]]:
        """
        Parse LLM response to extract thought, action, and action input.

        Returns:
            Tuple of (thought, action, action_input)
        """
        thought_match = re.search(r'Thought:\s*(.*?)(?=Action:|$)', response, re.DOTALL | re.IGNORECASE)
        action_match = re.search(r'Action:\s*(.*?)(?=Action Input:|$)', response, re.DOTALL | re.IGNORECASE)
        action_input_match = re.search(r'Action Input:\s*(.*?)(?=Observation:|$)', response, re.DOTALL | re.IGNORECASE)

        thought = thought_match.group(1).strip() if thought_match else ""
        action = action_match.group(1).strip() if action_match else None
        action_input = action_input_match.group(1).strip() if action_input_match else None

        return thought, action, action_input

    async def _execute_action(self, action: str, action_input: str) -> str:
        """Execute the specified action with the given input."""
        if action not in self.tools:
            available_tools = list(self.tools.keys())
            return f"Error: Unknown action '{action}'. Available actions: {', '.join(available_tools[:10])}{'...' if len(available_tools) > 10 else ''}"

        try:
            tool_func = self.tools[action]

            # Handle legacy tools (search, final_answer)
            if action in ["search", "final_answer"]:
                return tool_func(action_input)

            # Handle new comprehensive tools
            # Parse action_input for tool parameters
            if action in self.tool_registry.list_tools():
                # For most tools, the action_input is the primary parameter
                # Some tools may need special parsing
                if action == "calculator":
                    result = await tool_func(action_input)
                elif action == "web_search":
                    result = await tool_func(action_input)
                elif action == "code_interpreter":
                    result = await tool_func(action_input)
                elif action == "api_caller":
                    result = await tool_func(action_input)
                elif action == "text_processor":
                    # Parse operation and text from action_input
                    parts = action_input.split(" ", 1)
                    if len(parts) >= 2:
                        operation, text = parts[0], parts[1]
                        result = await tool_func(text, operation)
                    else:
                        result = f"Error: text_processor requires 'operation text' format"
                elif action == "datetime_tool":
                    result = await tool_func(action_input)
                elif action == "json_processor":
                    # Parse operation and data from action_input
                    parts = action_input.split(" ", 1)
                    if len(parts) >= 2:
                        operation, data = parts[0], parts[1]
                        result = await tool_func(operation, data)
                    else:
                        result = await tool_func(action_input)
                elif action == "hash_generator":
                    # Parse algorithm and text
                    parts = action_input.split(" ", 1)
                    if len(parts) >= 2:
                        algorithm, text = parts[0], parts[1]
                        result = await tool_func(text, algorithm)
                    else:
                        result = await tool_func(action_input)
                elif action == "url_validator":
                    # Parse operation and URL
                    parts = action_input.split(" ", 1)
                    if len(parts) >= 2:
                        operation, url = parts[0], parts[1]
                        result = await tool_func(url, operation)
                    else:
                        result = await tool_func(action_input)
                elif action == "base64_tool":
                    # Parse operation and data
                    parts = action_input.split(" ", 1)
                    if len(parts) >= 2:
                        operation, data = parts[0], parts[1]
                        result = await tool_func(operation, data)
                    else:
                        result = f"Error: base64_tool requires 'operation data' format"
                elif action == "regex_tool":
                    # Parse operation, text, and pattern
                    parts = action_input.split(" ", 2)
                    if len(parts) >= 3:
                        operation, text, pattern = parts[0], parts[1], parts[2]
                        result = await tool_func(operation, text, pattern)
                    else:
                        result = f"Error: regex_tool requires 'operation text pattern' format"
                else:
                    # Default: pass action_input as first parameter
                    result = await tool_func(action_input)

                return result
            else:
                return tool_func(action_input)

        except Exception as e:
            logger.error(f"Error executing action '{action}': {e}")
            return f"Error executing action '{action}': {str(e)}"

    def _should_continue(self, action: str, observation: str) -> bool:
        """Determine if the agent should continue reasoning."""
        if action == "final_answer":
            return False

        if "Error:" in observation:
            # Continue on errors to allow recovery
            return True

        return True

    def _load_conversation_context(self, conversation_id: str) -> ConversationContext:
        """Load conversation context with memory from storage."""
        try:
            context = self.context_store.get_context(conversation_id)
            logger.info(f"Loaded conversation context for {conversation_id} with {len(context.messages)} messages")
            return context
        except Exception as e:
            logger.error(f"Error loading conversation context: {e}")
            return ConversationContext(conversation_id=conversation_id)

    def _save_conversation_context(self, context: ConversationContext):
        """Save conversation context with memory to storage."""
        try:
            self.context_store.update_context(context.conversation_id, context)
            logger.info(f"Saved conversation context for {context.conversation_id}")
        except Exception as e:
            logger.error(f"Error saving conversation context: {e}")

    async def _create_memory_aware_prompt(self, user_query: str, context: ConversationContext) -> str:
        """Create a ReAct prompt that includes memory and learning context."""
        # Get memory context for the prompt
        memory_context = self.memory_manager.get_memory_context_for_prompt(context)

        # Get learning context from past experiences
        learning_context = await self._apply_learning_context(user_query)

        # Format the prompt with memory and learning context
        context_sections = []

        if memory_context:
            context_sections.append(f"=== MEMORY CONTEXT ===\n{memory_context}\n=== END MEMORY CONTEXT ===")

        if learning_context:
            context_sections.append(f"=== LEARNING CONTEXT ===\n{learning_context}\n=== END LEARNING CONTEXT ===")

        combined_context = "\n\n".join(context_sections) if context_sections else ""

        return self.react_prompt.format(
            user_query=user_query,
            memory_context=combined_context
        )

    async def _execute_plan(self, plan: ExecutionPlan, conversation_id: Optional[str] = None) -> AgentResult:
        """
        Execute a structured plan step by step.

        Args:
            plan: The execution plan to follow
            conversation_id: Optional conversation ID for context

        Returns:
            AgentResult with execution results
        """
        reasoning_steps = []
        start_time = datetime.utcnow()

        try:
            logger.info(f"Executing plan {plan.plan_id} with {plan.total_steps} steps")

            step_count = 0
            max_plan_steps = min(plan.total_steps, self.max_iterations)

            while not self.task_planner.is_plan_complete(plan) and step_count < max_plan_steps:
                # Check execution time limit
                elapsed_time = (datetime.utcnow() - start_time).total_seconds()
                if elapsed_time > self.max_execution_time:
                    error_msg = f"Plan execution timeout after {elapsed_time:.1f} seconds"
                    logger.warning(error_msg)
                    break

                # Get next executable step
                next_step = self.task_planner.get_next_executable_step(plan)
                if not next_step:
                    logger.warning("No executable steps available, checking for failures")
                    break

                # Update step status to in progress
                self.task_planner.update_step_status(plan, next_step.step_id, PlanStepStatus.IN_PROGRESS)

                # Execute the step
                step_start_time = datetime.utcnow()
                step_result = await self._execute_plan_step(next_step)
                step_execution_time = (datetime.utcnow() - step_start_time).total_seconds()

                # Create reasoning step for tracking
                reasoning_step = ReasoningStep(
                    step_number=step_count + 1,
                    thought=f"Executing plan step: {next_step.title}",
                    action=next_step.required_tools[0] if next_step.required_tools else "direct_execution",
                    action_input=next_step.description,
                    observation=step_result
                )
                reasoning_steps.append(reasoning_step)

                # Update step status based on result
                if "Error:" in step_result or "Failed:" in step_result:
                    self.task_planner.update_step_status(
                        plan, next_step.step_id, PlanStepStatus.FAILED,
                        actual_output=step_result,
                        execution_time=step_execution_time,
                        error_message=step_result
                    )

                    # Attempt plan adjustment for critical failures
                    if step_count < 3:  # Only adjust early in execution
                        logger.info("Attempting plan adjustment due to step failure")
                        adjusted_plan = await self.task_planner.adjust_plan(
                            plan,
                            {"failed_step": next_step.step_id, "error": step_result},
                            f"Step {next_step.step_id} failed: {step_result}"
                        )
                        if adjusted_plan.total_steps != plan.total_steps:
                            plan = adjusted_plan
                            logger.info(f"Plan adjusted to {plan.total_steps} steps")
                else:
                    self.task_planner.update_step_status(
                        plan, next_step.step_id, PlanStepStatus.COMPLETED,
                        actual_output=step_result,
                        execution_time=step_execution_time
                    )

                step_count += 1

            # Generate final answer based on plan execution
            progress = self.task_planner.get_plan_progress(plan)

            if progress["completion_percentage"] >= 80:
                # Plan mostly completed successfully
                completed_outputs = []
                for step in plan.steps:
                    if step.status == PlanStepStatus.COMPLETED and step.actual_output:
                        completed_outputs.append(f"- {step.title}: {step.actual_output}")

                final_answer = f"""I have successfully executed a structured plan to address your request: "{plan.goal}"

Plan Execution Summary:
- Total Steps: {plan.total_steps}
- Completed: {progress['completed_steps']} ({progress['completion_percentage']:.1f}%)
- Failed: {progress['failed_steps']}

Key Results:
{chr(10).join(completed_outputs) if completed_outputs else "Plan execution completed with mixed results."}

The structured approach allowed me to break down your complex request into manageable steps and execute them systematically."""

                success = True
            else:
                # Plan execution had significant issues
                final_answer = f"""I attempted to execute a structured plan for your request: "{plan.goal}", but encountered some challenges.

Plan Execution Summary:
- Total Steps: {plan.total_steps}
- Completed: {progress['completed_steps']} ({progress['completion_percentage']:.1f}%)
- Failed: {progress['failed_steps']}

While I wasn't able to complete all planned steps, I've provided the best results possible based on the successful portions of the plan."""

                success = progress["completed_steps"] > 0

            # Record successful agent query metrics
            metrics.record_agent_query(
                agent_type="production_agent_planned",
                reasoning_steps=len(reasoning_steps),
                success=success
            )

            return AgentResult(
                final_answer=final_answer,
                reasoning_steps=reasoning_steps,
                total_steps=len(reasoning_steps),
                success=success,
                execution_plan=plan,
                plan_used=True
            )

        except Exception as e:
            error_msg = f"Plan execution error: {str(e)}"
            logger.error(error_msg, exc_info=True)

            return AgentResult(
                final_answer=f"I apologize, but an error occurred while executing the plan: {str(e)}",
                reasoning_steps=reasoning_steps,
                total_steps=len(reasoning_steps),
                success=False,
                error_message=error_msg,
                execution_plan=plan,
                plan_used=True
            )

    async def _execute_plan_step(self, step: PlanStep) -> str:
        """
        Execute a single plan step using the appropriate tools.

        Args:
            step: The plan step to execute

        Returns:
            Result of step execution
        """
        try:
            logger.info(f"Executing step: {step.title}")

            # If no tools specified, use web search as default
            if not step.required_tools:
                step.required_tools = ["web_search"]

            # Execute using the first available tool
            for tool_name in step.required_tools:
                if tool_name in self.tools:
                    tool_func = self.tools[tool_name]

                    # Prepare tool input based on step description
                    tool_input = step.description

                    # Execute the tool
                    if tool_name == "final_answer":
                        result = tool_func(step.expected_output)
                    else:
                        result = await self._execute_tool(tool_name, tool_input)

                    return f"Step completed: {result}"

            # If no tools available, return description as result
            return f"Step noted: {step.description} (Expected: {step.expected_output})"

        except Exception as e:
            error_msg = f"Error executing step {step.step_id}: {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

    async def self_reflection(self, agent_result: AgentResult, original_query: str,
                            execution_time: float) -> Optional[AgentLearning]:
        """
        Perform self-reflection on completed task to extract learning insights.

        This method analyzes the agent's performance on a completed task,
        identifies areas for improvement, and stores learning insights for
        future adaptation.

        Args:
            agent_result: The result from agent execution
            original_query: The original user query
            execution_time: Total execution time in seconds

        Returns:
            AgentLearning object with analysis and insights, or None if reflection fails
        """
        try:
            logger.info(f"Starting self-reflection on task: {original_query[:100]}...")

            # Only perform reflection on complex tasks or failures
            should_reflect = (
                agent_result.plan_used or  # Complex tasks that used planning
                not agent_result.success or  # Failed tasks to learn from errors
                agent_result.total_steps >= 5 or  # Multi-step tasks
                execution_time > 30  # Long-running tasks
            )

            if not should_reflect:
                logger.info("Task too simple for reflection, skipping learning")
                return None

            # Analyze performance and extract insights
            learning = await self.learning_service.analyze_performance(
                agent_result=agent_result,
                original_query=original_query,
                execution_time=execution_time
            )

            # Store learning in Weaviate for future reference
            stored = await self.learning_service.store_learning(learning)

            if stored:
                logger.info(f"Learning insights stored: {learning.learning_id}")
                logger.info(f"Performance category: {learning.performance_category.value}")
                logger.info(f"Insights extracted: {len(learning.learning_insights)}")

                # Log key insights for monitoring
                for insight in learning.learning_insights[:3]:  # Top 3 insights
                    logger.info(f"Insight: {insight.title} (confidence: {insight.confidence_score:.2f})")
            else:
                logger.warning("Failed to store learning insights")

            return learning

        except Exception as e:
            logger.error(f"Error during self-reflection: {e}", exc_info=True)
            return None

    async def _apply_learning_context(self, query: str) -> str:
        """
        Apply learning context to improve task execution.

        Retrieves similar past learnings and incorporates insights
        into the current task execution.

        Args:
            query: The current user query

        Returns:
            Enhanced context with learning insights
        """
        try:
            # Retrieve similar learnings
            similar_learnings = await self.learning_service.retrieve_similar_learnings(
                query=query,
                limit=3
            )

            if not similar_learnings:
                return ""

            # Generate learning context
            learning_summary = self.learning_service.get_learning_summary(similar_learnings)

            context_parts = []

            # Add performance insights
            if learning_summary["total_learnings"] > 0:
                context_parts.append(f"Based on {learning_summary['total_learnings']} similar past tasks:")

                # Add top insights
                for insight in learning_summary["top_insights"][:3]:
                    context_parts.append(
                        f"- {insight['title']}: {insight['suggestion']} "
                        f"(confidence: {insight['confidence']:.1f})"
                    )

                # Add strategy recommendations
                if learning_summary["strategy_recommendations"]:
                    context_parts.append("Key strategies to consider:")
                    for rec in learning_summary["strategy_recommendations"][:2]:
                        context_parts.append(f"- {rec}")

            learning_context = "\n".join(context_parts)

            if learning_context:
                logger.info(f"Applied learning context from {len(similar_learnings)} past experiences")
                return f"\n\nLEARNING CONTEXT (from past experiences):\n{learning_context}\n"

            return ""

        except Exception as e:
            logger.error(f"Error applying learning context: {e}")
            return ""

    async def reason_and_act(self, user_query: str, conversation_id: Optional[str] = None) -> AgentResult:
        """
        Execute the enhanced reasoning loop with planning for complex queries.

        Args:
            user_query: The user's question or request
            conversation_id: Optional conversation ID for context and memory

        Returns:
            AgentResult with the final answer and reasoning steps
        """
        reasoning_steps = []
        start_time = datetime.utcnow()

        # Load conversation context and memory
        context = None
        if conversation_id:
            context = self._load_conversation_context(conversation_id)
            # Add user query to context
            context.messages.append({
                'role': 'user',
                'content': user_query,
                'timestamp': datetime.utcnow().isoformat()
            })

        try:
            # Apply learning context from past experiences
            learning_context = await self._apply_learning_context(user_query)

            # Assess query complexity to determine approach
            complexity_score = await self._assess_query_complexity(user_query)
            logger.info(f"Query complexity assessed: {complexity_score:.2f}")

            # Use planning approach for complex queries
            if complexity_score >= self.planning_threshold:
                logger.info("Using planning approach for complex query")

                # Generate execution plan
                execution_plan = await self.task_planner.analyze_and_plan(user_query)

                # Execute the plan
                result = await self._execute_plan(execution_plan, conversation_id)

                # Process memory and save context
                if context:
                    # Add assistant response to context
                    context.messages.append({
                        'role': 'assistant',
                        'content': result.final_answer,
                        'timestamp': datetime.utcnow().isoformat()
                    })

                    # Process memory from this conversation turn
                    context = self.memory_manager.process_conversation_turn(context, result.total_steps)

                    # Save updated context with memory
                    self._save_conversation_context(context)

                # Perform self-reflection for learning and adaptation
                learning = await self.self_reflection(result, user_query,
                                                    (datetime.utcnow() - start_time).total_seconds())
                if learning:
                    logger.info(f"Self-reflection completed: {learning.performance_category.value}")

                return result

            # Use traditional ReAct approach for simple queries
            logger.info("Using traditional ReAct approach for simple query")
            # Initialize conversation context
            conversation_history = ""

            for step_num in range(1, self.max_iterations + 1):
                # Check execution time limit
                elapsed_time = (datetime.utcnow() - start_time).total_seconds()
                if elapsed_time > self.max_execution_time:
                    error_msg = f"Agent execution timeout after {elapsed_time:.1f} seconds"
                    logger.warning(error_msg)
                    return AgentResult(
                        final_answer=f"I apologize, but I couldn't complete the task within the time limit. {error_msg}",
                        reasoning_steps=reasoning_steps,
                        total_steps=step_num - 1,
                        success=False,
                        error_message=error_msg
                    )

                # Create memory-aware prompt with conversation history
                if context:
                    prompt = await self._create_memory_aware_prompt(user_query, context)
                else:
                    # Apply learning context even without conversation context
                    learning_context = await self._apply_learning_context(user_query)
                    context_section = f"\n\n{learning_context}" if learning_context else ""
                    prompt = self.react_prompt.format(user_query=user_query, memory_context=context_section)

                if conversation_history:
                    prompt += f"\n\nPrevious steps:\n{conversation_history}"

                # Generate reasoning step
                logger.info(f"Step {step_num}: Generating reasoning")
                llm_response = await self.llm_manager.generate_response(
                    prompt,
                    conversation_id=conversation_id
                )

                # Parse the response
                thought, action, action_input = self._parse_llm_response(llm_response.content)

                # Create reasoning step
                current_step = ReasoningStep(
                    step_number=step_num,
                    thought=thought,
                    action=action,
                    action_input=action_input
                )

                logger.info(f"Step {step_num}: Thought='{thought[:100]}...', Action='{action}', Input='{action_input[:50] if action_input else None}...'")

                # Execute action if provided
                if action and action_input:
                    observation = await self._execute_action(action, action_input)
                    current_step.observation = observation

                    logger.info(f"Step {step_num}: Observation='{observation[:100]}...'")

                    # Update conversation history
                    conversation_history += f"\nStep {step_num}:\nThought: {thought}\nAction: {action}\nAction Input: {action_input}\nObservation: {observation}\n"

                    # Check if we should continue
                    if not self._should_continue(action, observation):
                        reasoning_steps.append(current_step)

                        # Extract final answer from observation
                        final_answer = observation.replace("Final Answer: ", "") if observation.startswith("Final Answer: ") else observation

                        # Process memory and save context before returning
                        if context:
                            # Add assistant response to context
                            context.messages.append({
                                'role': 'assistant',
                                'content': final_answer,
                                'timestamp': datetime.utcnow().isoformat()
                            })

                            # Process memory from this conversation turn
                            context = self.memory_manager.process_conversation_turn(context, step_num)

                            # Save updated context with memory
                            self._save_conversation_context(context)

                        # Record successful agent query metrics
                        metrics.record_agent_query(
                            agent_type="production_agent",
                            reasoning_steps=step_num,
                            success=True
                        )

                        result = AgentResult(
                            final_answer=final_answer,
                            reasoning_steps=reasoning_steps,
                            total_steps=step_num,
                            success=True,
                            plan_used=False
                        )

                        # Perform self-reflection for learning and adaptation
                        learning = await self.self_reflection(result, user_query,
                                                            (datetime.utcnow() - start_time).total_seconds())
                        if learning:
                            logger.info(f"Self-reflection completed: {learning.performance_category.value}")

                        return result
                else:
                    # No action provided, treat as error
                    current_step.observation = "Error: No valid action provided"
                    logger.warning(f"Step {step_num}: No valid action provided in LLM response")

                reasoning_steps.append(current_step)

            # Max iterations reached
            error_msg = f"Agent reached maximum iterations ({self.max_iterations}) without completing the task"
            logger.warning(error_msg)

            # Process memory even for incomplete tasks
            if context:
                # Add a partial response to context
                context.messages.append({
                    'role': 'assistant',
                    'content': "I apologize, but I couldn't complete the task within the maximum number of reasoning steps.",
                    'timestamp': datetime.utcnow().isoformat()
                })

                # Process memory from this conversation turn
                context = self.memory_manager.process_conversation_turn(context, self.max_iterations)

                # Save updated context with memory
                self._save_conversation_context(context)

            # Record failed agent query metrics
            metrics.record_agent_query(
                agent_type="production_agent",
                reasoning_steps=len(reasoning_steps),
                success=False
            )

            return AgentResult(
                final_answer="I apologize, but I couldn't complete the task within the maximum number of reasoning steps.",
                reasoning_steps=reasoning_steps,
                total_steps=self.max_iterations,
                success=False,
                error_message=error_msg,
                plan_used=False
            )

        except Exception as e:
            error_msg = f"Agent execution error: {str(e)}"
            logger.error(error_msg, exc_info=True)

            # Record failed agent query metrics
            metrics.record_agent_query(
                agent_type="production_agent",
                reasoning_steps=len(reasoning_steps),
                success=False
            )

            return AgentResult(
                final_answer=f"I apologize, but an error occurred while processing your request: {str(e)}",
                reasoning_steps=reasoning_steps,
                total_steps=len(reasoning_steps),
                success=False,
                error_message=error_msg,
                plan_used=False
            )

# Global agent instance
_production_agent = None

def get_production_agent() -> ProductionAgent:
    """Get the global ProductionAgent instance."""
    global _production_agent
    if _production_agent is None:
        _production_agent = ProductionAgent()
    return _production_agent


async def run_agent(data: AgentState) -> dict:
    """
    Execute the ProductionAgent with ReAct reasoning pattern.

    This function integrates the new ProductionAgent with the existing
    LangGraph workflow structure.
    """
    messages = data.get('messages', [])
    reasoning_steps = data.get('reasoning_steps', [])
    current_step = data.get('current_step', 0)

    if not messages:
        return {
            "agent_outcome": AgentFinish(
                return_values={"output": "No input provided"},
                log=""
            ),
            "reasoning_steps": reasoning_steps,
            "current_step": current_step
        }

    last_message = messages[-1]
    if isinstance(last_message, HumanMessage):
        query = last_message.content
        logger.info(f"ProductionAgent processing query: {query}")

        try:
            # Get the production agent and execute ReAct reasoning
            agent = get_production_agent()
            result = await agent.reason_and_act(query)

            # Create response message
            response_message = AIMessage(content=result.final_answer)

            # Log reasoning steps for debugging
            logger.info(f"Agent completed with {result.total_steps} reasoning steps")
            for step in result.reasoning_steps:
                logger.debug(f"Step {step.step_number}: {step.thought[:100]}... -> {step.action}")

            return {
                "messages": [response_message],
                "agent_outcome": AgentFinish(
                    return_values={
                        "output": result.final_answer,
                        "reasoning_steps": [
                            {
                                "step": step.step_number,
                                "thought": step.thought,
                                "action": step.action,
                                "action_input": step.action_input,
                                "observation": step.observation,
                                "timestamp": step.timestamp
                            }
                            for step in result.reasoning_steps
                        ],
                        "total_steps": result.total_steps,
                        "success": result.success
                    },
                    log=f"ReAct reasoning completed in {result.total_steps} steps"
                ),
                "reasoning_steps": result.reasoning_steps,
                "current_step": result.total_steps
            }

        except Exception as e:
            error_msg = f"Agent execution failed: {str(e)}"
            logger.error(error_msg, exc_info=True)

            response_message = AIMessage(content=f"I apologize, but I encountered an error while processing your request: {str(e)}")

            return {
                "messages": [response_message],
                "agent_outcome": AgentFinish(
                    return_values={"output": response_message.content},
                    log=error_msg
                ),
                "reasoning_steps": reasoning_steps,
                "current_step": current_step
            }

    return {
        "agent_outcome": AgentFinish(
            return_values={"output": "Unable to process request"},
            log="Invalid message type"
        ),
        "reasoning_steps": reasoning_steps,
        "current_step": current_step
    }

def should_continue(data: AgentState) -> str:
    """Determines whether to continue the loop or end."""
    if isinstance(data.get('agent_outcome'), AgentFinish):
        return "end"
    else:
        return "continue"


# Create the agent workflow graph
def create_agent_workflow():
    """Create and return the agent workflow graph."""
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", run_agent)
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {"continue": "agent", "end": END}
    )
    return workflow.compile()


# Global workflow instance
agent_graph_app = create_agent_workflow()


# Convenience function for direct agent usage
async def process_query(query: str, conversation_id: Optional[str] = None) -> AgentResult:
    """
    Process a query directly using the ProductionAgent.

    Args:
        query: The user's question or request
        conversation_id: Optional conversation ID for context

    Returns:
        AgentResult with the final answer and reasoning steps
    """
    agent = get_production_agent()
    return await agent.reason_and_act(query, conversation_id)
