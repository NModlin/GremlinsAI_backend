# app/api/v1/endpoints/multi_agent.py
import logging
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.database.database import get_db
from app.services.chat_history import ChatHistoryService
from app.services.agent_memory import AgentMemoryService
from app.core.multi_agent import multi_agent_orchestrator
from app.api.v1.schemas.multi_agent import (
    MultiAgentRequest,
    MultiAgentResponse,
    AgentCapabilitiesResponse,
    AgentMemoryRequest,
    AgentMemoryResponse,
    ConversationSummaryResponse,
    AgentPerformanceResponse,
    WorkflowType
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/workflow", response_model=MultiAgentResponse)
async def execute_multi_agent_workflow(
    request: MultiAgentRequest,
    db: AsyncSession = Depends(get_db)
):
    """Execute a multi-agent workflow with the specified parameters."""
    start_time = time.time()
    
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
                title=f"Multi-Agent: {request.input[:50]}...",
                initial_message=None
            )
            conversation_id = conversation.id
        
        # Add user message if saving is enabled
        user_message = None
        if request.save_conversation:
            user_message = await ChatHistoryService.add_message(
                db=db,
                conversation_id=conversation_id,
                role="user",
                content=request.input
            )
        
        # Create context-aware prompt if conversation exists
        context_prompt = request.input
        if conversation_id:
            context_prompt = await AgentMemoryService.create_agent_context_prompt(
                db=db,
                conversation_id=conversation_id,
                current_query=request.input
            )
            context_used = True
        
        # Execute the appropriate workflow
        if request.workflow_type == WorkflowType.SIMPLE_RESEARCH:
            result = multi_agent_orchestrator.execute_simple_query(
                query=context_prompt,
                context=""
            )
        else:
            result = multi_agent_orchestrator.execute_complex_workflow(
                query=context_prompt,
                workflow_type=request.workflow_type.value
            )
        
        execution_time = time.time() - start_time
        
        # Store agent interactions in memory
        message_ids = []
        if request.save_conversation:
            # Create serializable extra_data (avoid complex objects)
            extra_data = {
                "workflow_type": request.workflow_type.value,
                "agents_used": result.get("agents_used", []),
                "execution_time": execution_time,
                "task_type": result.get("task_type", "unknown"),
                "workflow_steps": result.get("workflow_steps", 1)
            }

            # Store the agent workflow result
            agent_message = await ChatHistoryService.add_message(
                db=db,
                conversation_id=conversation_id,
                role="assistant",
                content=str(result.get("result", "")),
                extra_data=extra_data
            )
            
            if agent_message:
                message_ids.append(agent_message.id)
            
            # Store individual agent interactions with serializable data
            for agent_name in result.get("agents_used", []):
                # Create serializable input and output data
                input_data = {
                    "query": request.input,
                    "context_prompt": context_prompt[:500] if context_prompt else ""  # Truncate long context
                }
                output_data = {
                    "query": result.get("query", ""),
                    "result": str(result.get("result", ""))[:1000],  # Truncate long results
                    "agents_used": result.get("agents_used", []),
                    "task_type": result.get("task_type", "unknown"),
                    "note": result.get("note", "")
                }

                interaction_id = await AgentMemoryService.store_agent_interaction(
                    db=db,
                    conversation_id=conversation_id,
                    agent_name=agent_name,
                    task_type=request.workflow_type.value,
                    input_data=input_data,
                    output_data=output_data,
                    metadata={"execution_time": execution_time}
                )
                if interaction_id:
                    message_ids.append(interaction_id)
        
        # Extract string result from multi-agent response
        result_text = ""
        if isinstance(result, dict):
            if "output" in result:
                result_text = str(result["output"])
            elif "result" in result:
                result_text = str(result["result"])
            else:
                result_text = str(result.get("response", "Multi-agent workflow completed"))
        else:
            result_text = str(result)

        return MultiAgentResponse(
            result=result_text,
            conversation_id=conversation_id,
            workflow_type=request.workflow_type.value,
            agents_used=result.get("agents_used", []) if isinstance(result, dict) else [],
            workflow_steps=result.get("workflow_steps", 1) if isinstance(result, dict) else 1,
            execution_time=execution_time,
            context_used=context_used,
            message_ids=message_ids
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Multi-agent workflow execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {str(e)}")

@router.get("/capabilities", response_model=AgentCapabilitiesResponse)
async def get_agent_capabilities():
    """Get information about available agents and their capabilities."""
    try:
        agent_capabilities = multi_agent_orchestrator.get_agent_capabilities()
        
        workflows = {
            "simple_research": "Single agent research task using web search",
            "research_analyze_write": "Multi-step workflow: research → analyze → write",
            "complex_analysis": "Deep analysis workflow with multiple perspectives",
            "collaborative_writing": "Collaborative content creation with multiple agents"
        }
        
        return AgentCapabilitiesResponse(
            agents=agent_capabilities,
            workflows=workflows,
            total_agents=len(agent_capabilities)
        )
        
    except Exception as e:
        logger.error(f"Error getting agent capabilities: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve agent capabilities")

@router.post("/memory", response_model=AgentMemoryResponse)
async def get_agent_memory(
    request: AgentMemoryRequest,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve agent memory and context for a conversation."""
    try:
        agent_context = await AgentMemoryService.get_agent_context(
            db=db,
            conversation_id=request.conversation_id,
            agent_name=request.agent_name,
            task_type=request.task_type,
            max_interactions=request.max_interactions
        )
        
        # Get list of agents involved
        agents_involved = list(set(
            interaction.get("agent_name", "unknown") 
            for interaction in agent_context
            if interaction.get("agent_name")
        ))
        
        return AgentMemoryResponse(
            conversation_id=request.conversation_id,
            agent_context=agent_context,
            total_interactions=len(agent_context),
            agents_involved=agents_involved
        )
        
    except Exception as e:
        logger.error(f"Error retrieving agent memory: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve agent memory")

@router.get("/conversations/{conversation_id}/summary", response_model=ConversationSummaryResponse)
async def get_conversation_summary(
    conversation_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a comprehensive summary of a conversation including agent interactions."""
    try:
        summary = await AgentMemoryService.get_conversation_summary(
            db=db,
            conversation_id=conversation_id,
            include_agent_actions=True
        )
        
        if not summary:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return ConversationSummaryResponse(**summary)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve conversation summary")

@router.get("/performance/{agent_name}", response_model=AgentPerformanceResponse)
async def get_agent_performance(
    agent_name: str,
    days_back: int = 7,
    db: AsyncSession = Depends(get_db)
):
    """Get performance metrics for a specific agent."""
    try:
        metrics = await AgentMemoryService.get_agent_performance_metrics(
            db=db,
            agent_name=agent_name,
            days_back=days_back
        )
        
        if not metrics:
            metrics = {
                "agent_name": agent_name,
                "period_days": days_back,
                "total_tasks": 0,
                "successful_tasks": 0,
                "average_response_time": 0.0,
                "error_rate": 0.0,
                "note": "No performance data available"
            }
        
        return AgentPerformanceResponse(**metrics)
        
    except Exception as e:
        logger.error(f"Error getting agent performance: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve agent performance metrics")

@router.get("/performance", response_model=AgentPerformanceResponse)
async def get_overall_performance(
    days_back: int = 7,
    db: AsyncSession = Depends(get_db)
):
    """Get overall performance metrics for all agents."""
    try:
        metrics = await AgentMemoryService.get_agent_performance_metrics(
            db=db,
            agent_name=None,
            days_back=days_back
        )
        
        if not metrics:
            metrics = {
                "agent_name": "all",
                "period_days": days_back,
                "total_tasks": 0,
                "successful_tasks": 0,
                "average_response_time": 0.0,
                "error_rate": 0.0,
                "note": "No performance data available"
            }
        
        return AgentPerformanceResponse(**metrics)
        
    except Exception as e:
        logger.error(f"Error getting overall performance: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve performance metrics")

@router.delete("/memory/{conversation_id}")
async def cleanup_agent_memory(
    conversation_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Clean up agent memory for a specific conversation."""
    try:
        # This would typically involve cleaning up agent-specific data
        # For now, we'll rely on the conversation cleanup mechanisms
        
        # Verify conversation exists
        conversation = await ChatHistoryService.get_conversation(
            db=db,
            conversation_id=conversation_id,
            include_messages=False
        )
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # In a production system, you might want to:
        # 1. Remove agent-specific system messages
        # 2. Clear cached agent context
        # 3. Update performance metrics
        
        return {"message": f"Agent memory cleanup initiated for conversation {conversation_id}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning up agent memory: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup agent memory")
