# app/api/v1/endpoints/agent.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.agent import agent_graph_app
from app.database.database import get_db
from app.services.chat_history import ChatHistoryService
from app.api.v1.schemas.chat_history import AgentConversationRequest, AgentConversationResponse
from langchain_core.messages import HumanMessage, AIMessage

router = APIRouter()

# Keep the original simple endpoint for backward compatibility
@router.post("/invoke")
async def invoke_agent_simple(request: dict):
    """Simple agent invocation (backward compatibility)."""
    input_text = request.get("input", "")
    human_message = HumanMessage(content=input_text)
    inputs = {"messages": [human_message]}

    final_state = {}
    for s in agent_graph_app.stream(inputs):
        final_state.update(s)

    return {"output": final_state}


@router.post("/chat", response_model=AgentConversationResponse)
async def invoke_agent_with_conversation(
    request: AgentConversationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Invoke agent with conversation context and history management."""
    try:
        conversation_id = request.conversation_id
        context_used = False

        # Get or create conversation
        if conversation_id:
            conversation = await ChatHistoryService.get_conversation(
                db=db,
                conversation_id=conversation_id,
                include_messages=False
            )
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
        else:
            # Create new conversation
            conversation = await ChatHistoryService.create_conversation(
                db=db,
                title=f"Chat: {request.input[:50]}...",
                initial_message=None  # We'll add the message separately
            )
            conversation_id = conversation.id

        # Add user message to conversation if saving is enabled
        user_message = None
        if request.save_conversation:
            user_message = await ChatHistoryService.add_message(
                db=db,
                conversation_id=conversation_id,
                role="user",
                content=request.input
            )

        # Get conversation context for the agent
        context_messages = []
        if conversation_id:
            context = await ChatHistoryService.get_conversation_context(
                db=db,
                conversation_id=conversation_id,
                max_messages=10  # Limit context to last 10 messages
            )

            if context:
                context_used = True
                # Convert context to LangChain messages
                for ctx_msg in context[:-1]:  # Exclude the message we just added
                    if ctx_msg["role"] == "user":
                        context_messages.append(HumanMessage(content=ctx_msg["content"]))
                    elif ctx_msg["role"] == "assistant":
                        context_messages.append(AIMessage(content=ctx_msg["content"]))

        # Add current user message
        context_messages.append(HumanMessage(content=request.input))

        # Invoke the agent with context
        inputs = {"messages": context_messages}
        final_state = {}
        for s in agent_graph_app.stream(inputs):
            final_state.update(s)

        # Extract agent response
        agent_response = ""
        if "agent_outcome" in final_state:
            outcome = final_state["agent_outcome"]
            if hasattr(outcome, 'return_values') and 'output' in outcome.return_values:
                agent_response = outcome.return_values['output']

        # Save agent response to conversation if saving is enabled
        response_message = None
        if request.save_conversation and agent_response:
            response_message = await ChatHistoryService.add_message(
                db=db,
                conversation_id=conversation_id,
                role="assistant",
                content=agent_response,
                extra_data={"agent_state": final_state}
            )

        return AgentConversationResponse(
            output=final_state,
            conversation_id=conversation_id,
            message_id=response_message.id if response_message else "",
            context_used=context_used
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent invocation failed: {str(e)}")
