# app/core/agent.py
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from typing import TypedDict, Annotated, List, Union
import operator
from app.core.tools import duckduckgo_search
# from langchain_openai import ChatOpenAI # Will be used with a proper model in later phases
# from langchain_core.prompts import ChatPromptTemplate
# from langchain.agents import create_tool_calling_agent

# This would be configured with a real model in later phases
# llm = ChatOpenAI(model="gpt-4-turbo-preview", temperature=0)
# For now, we'll simulate the agent's logic

# 1. Define the state
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    agent_outcome: Union[AgentAction, AgentFinish, None]

# 2. Define a simple search function that works with the current setup
def search_function(query: str) -> str:
    """Simple wrapper for DuckDuckGo search."""
    try:
        result = duckduckgo_search(query)
        return f"Search results for '{query}': {result}"
    except Exception as e:
        return f"Search failed: {str(e)}"

# 3. Define the agent logic (simulated for now)
def run_agent(data: AgentState) -> dict:
    """Simulates an LLM call to decide the next action."""
    messages = data.get('messages', [])
    if not messages:
        return {"agent_outcome": AgentFinish(return_values={"output": "No input provided"}, log="")}

    last_message = messages[-1]
    if isinstance(last_message, HumanMessage):
        query = last_message.content
        print(f"--- Agent processing query: {query} ---")

        # For Phase 1, we'll directly perform the search and return results
        search_result = search_function(query)

        # Create a response message
        response_message = AIMessage(content=search_result)

        return {
            "messages": [response_message],
            "agent_outcome": AgentFinish(return_values={"output": search_result}, log="Search completed")
        }

    return {"agent_outcome": AgentFinish(return_values={"output": "Unable to process request"}, log="")}

# 4. Define the conditional edge logic
def should_continue(data: AgentState) -> str:
    """Determines whether to continue the loop or end."""
    if isinstance(data.get('agent_outcome'), AgentFinish):
        return "end"
    else:
        return "continue"

# 5. Define the graph
workflow = StateGraph(AgentState)
workflow.add_node("agent", run_agent)
workflow.set_entry_point("agent")
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {"continue": "agent", "end": END}
)
agent_graph_app = workflow.compile()
