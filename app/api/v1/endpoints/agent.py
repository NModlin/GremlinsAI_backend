# app/api/v1/endpoints/agent.py
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.agent import agent_graph_app
from app.core.multi_agent import multi_agent_orchestrator
from app.database.database import get_db
from app.services.chat_history import ChatHistoryService
from app.services.agent_memory import AgentMemoryService
from app.api.v1.schemas.chat_history import AgentConversationRequest, AgentConversationResponse
from app.api.v1.schemas.multi_agent import LegacyAgentRequest, LegacyAgentResponse
from langchain_core.messages import HumanMessage, AIMessage
from app.core.exceptions import (
    AgentProcessingException,
    ValidationException,
    ValidationErrorDetail,
    ExternalServiceException
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Keep the original simple endpoint for backward compatibility
@router.post("/invoke")
async def invoke_agent_simple(request: dict):
    """Simple agent invocation (backward compatibility)."""
    try:
        input_text = request.get("input", "")

        # Validate input
        if not input_text or not input_text.strip():
            raise ValidationException(
                error_message="Input text is required",
                validation_errors=[ValidationErrorDetail(
                    field="input",
                    message="Input text cannot be empty",
                    invalid_value=input_text,
                    expected_type="non-empty string"
                )]
            )

        human_message = HumanMessage(content=input_text)
        inputs = {"messages": [human_message]}

        try:
            final_state = {}
            for s in agent_graph_app.stream(inputs):
                final_state.update(s)

            return {"output": final_state}

        except Exception as e:
            logger.error(f"Agent processing failed: {e}")
            raise AgentProcessingException(
                error_message="Agent processing failed",
                error_details=str(e),
                processing_step="agent_execution"
            )

    except (ValidationException, AgentProcessingException):
        raise
    except Exception as e:
        logger.error(f"Unexpected error in agent endpoint: {e}")
        raise AgentProcessingException(
            error_message="Unexpected error in agent processing",
            error_details=str(e),
            processing_step="endpoint_handling"
        )


@router.post("/chat", response_model=AgentConversationResponse)
async def invoke_agent_with_conversation(
    request: AgentConversationRequest,
    use_multi_agent: bool = Query(False, description="Use multi-agent system for enhanced reasoning"),
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

        # Choose between single-agent and multi-agent processing
        if use_multi_agent:
            # Use multi-agent system for enhanced reasoning
            logger.info(f"Using multi-agent system for query: {request.input}")

            # Create context-aware prompt
            context_prompt = await AgentMemoryService.create_agent_context_prompt(
                db=db,
                conversation_id=conversation_id,
                current_query=request.input
            ) if conversation_id else request.input

            # Execute simple multi-agent workflow
            multi_result = multi_agent_orchestrator.execute_simple_query(
                query=context_prompt,
                context=""
            )

            agent_response = str(multi_result.get("result", ""))
            # Create a simple dict structure instead of a dynamic object
            final_state = {
                "multi_agent_result": multi_result,
                "agent_outcome": {
                    'return_values': {'output': agent_response}
                }
            }
            context_used = True

        else:
            # Use original single-agent system
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
                if isinstance(outcome, dict) and 'return_values' in outcome:
                    agent_response = outcome['return_values'].get('output', '')
                elif hasattr(outcome, 'return_values') and 'output' in outcome.return_values:
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
