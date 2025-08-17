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


class AgentState(TypedDict):
    """State for the agent graph."""
    messages: Annotated[list[BaseMessage], operator.add]
    agent_outcome: Union[AgentAction, AgentFinish, None]
    reasoning_steps: List[ReasoningStep]
    current_step: int

class ProductionAgent:
    """
    Production-grade agent implementing the ReAct pattern.

    The agent follows a reasoning loop:
    1. Thought: Analyze the problem and decide what to do
    2. Action: Execute a tool or provide final answer
    3. Observation: Process the result and continue or finish

    Features:
    - Multi-step reasoning capability
    - Tool selection and execution
    - Error handling and recovery
    - Conversation context management
    - Performance monitoring
    """

    def __init__(self, max_iterations: int = 10, max_execution_time: int = 300):
        """
        Initialize the ProductionAgent with memory capabilities.

        Args:
            max_iterations: Maximum number of reasoning steps
            max_execution_time: Maximum execution time in seconds
        """
        self.llm_manager = ProductionLLMManager()
        self.max_iterations = max_iterations
        self.max_execution_time = max_execution_time

        # Memory and context management
        self.context_store = get_context_store()
        self.memory_manager = MemoryManager()

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

        logger.info(f"ProductionAgent initialized with {len(self.tools)} tools and memory system")

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

    def _create_memory_aware_prompt(self, user_query: str, context: ConversationContext) -> str:
        """Create a ReAct prompt that includes memory context."""
        # Get memory context for the prompt
        memory_context = self.memory_manager.get_memory_context_for_prompt(context)

        # Format the prompt with memory context
        if memory_context:
            memory_section = f"\n=== MEMORY CONTEXT ===\n{memory_context}\n=== END MEMORY CONTEXT ===\n"
        else:
            memory_section = ""

        return self.react_prompt.format(
            user_query=user_query,
            memory_context=memory_section
        )

    async def reason_and_act(self, user_query: str, conversation_id: Optional[str] = None) -> AgentResult:
        """
        Execute the ReAct reasoning loop for the given query with memory awareness.

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
                    prompt = self._create_memory_aware_prompt(user_query, context)
                else:
                    prompt = self.react_prompt.format(user_query=user_query, memory_context="")

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

                        return AgentResult(
                            final_answer=final_answer,
                            reasoning_steps=reasoning_steps,
                            total_steps=step_num,
                            success=True
                        )
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
                error_message=error_msg
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
                error_message=error_msg
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
