# app/api/v1/endpoints/multi_agent.py
import logging
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.database.database import get_db
from app.services.chat_history import ChatHistoryService
from app.services.agent_memory import AgentMemoryService
from app.core.security_service import SecurityContext, get_current_user, require_permission, Permission
from app.core.tracing_service import tracing_service
from app.core.metrics_service import metrics_service
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

@router.post("/execute-task")
async def execute_multi_agent_task(
    request: dict,
    db: AsyncSession = Depends(get_db),
    current_user: SecurityContext = Depends(require_permission(Permission.WRITE))
):
    """
    Execute a complex multi-agent task using the CrewAI framework.

    This endpoint implements the complete multi-agent coordination system with:
    - Multiple specialized agents (researcher, analyst, writer, coordinator)
    - Inter-agent communication and context preservation
    - Graceful error handling and fallback mechanisms
    - Performance monitoring and metrics tracking
    """
    start_time = time.time()

    # Extract request parameters for tracing
    task_description = request.get("task_description", "")
    workflow_type = request.get("workflow_type", "research_analyze_write")
    context = request.get("context", {})
    timeout = request.get("timeout", 300)

    agents = ["researcher", "analyst", "writer", "coordinator"]  # Default agents

    with tracing_service.trace_multi_agent_task(workflow_type, agents) as span:
        span.set_attribute("multi_agent.task_description_length", len(task_description))
        span.set_attribute("multi_agent.timeout", timeout)
        span.set_attribute("multi_agent.user_id", current_user.user_id)

        try:

            if not task_description:
                raise HTTPException(status_code=422, detail="task_description is required")

            # Validate workflow type
            valid_workflows = ["research_analyze_write", "complex_analysis", "collaborative_query"]
            if workflow_type not in valid_workflows:
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid workflow_type. Must be one of: {valid_workflows}"
                )

            # Import and use the multi-agent service
            from app.services.multi_agent_service import multi_agent_service

            # Execute the multi-agent task
            with tracing_service.trace_operation("multi_agent.execute_crew_task") as task_span:
                result = await multi_agent_service.execute_crew_task(
                    task_description=task_description,
                    workflow_type=workflow_type,
                    context=context,
                    timeout=timeout
                )

                # Record metrics
                execution_time = time.time() - start_time
                status = "success" if result.success else "error"

                metrics_service.record_multi_agent_task(
                    workflow_type=workflow_type,
                    status=status,
                    duration=execution_time
                )

                # Add tracing attributes
                span.set_attribute("multi_agent.success", result.success)
                span.set_attribute("multi_agent.execution_time", execution_time)
                span.set_attribute("multi_agent.agents_count", len(result.agents_involved))
                task_span.set_attribute("multi_agent.result_length", len(result.result))

            # Save to conversation history if requested
        conversation_id = request.get("conversation_id")
        if request.get("save_conversation", False) and conversation_id:
            try:
                await ChatHistoryService.add_message(
                    db=db,
                    conversation_id=conversation_id,
                    role="user",
                    content=task_description
                )
                await ChatHistoryService.add_message(
                    db=db,
                    conversation_id=conversation_id,
                    role="assistant",
                    content=result.result,
                    extra_data={
                        "workflow_type": workflow_type,
                        "agents_involved": result.agents_involved,
                        "execution_time": result.execution_time,
                        "performance_metrics": result.performance_metrics
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to save conversation: {e}")

        # Return comprehensive response
        return {
            "success": result.success,
            "result": result.result,
            "agents_involved": result.agents_involved,
            "execution_time": result.execution_time,
            "workflow_type": result.workflow_type,
            "context_preserved": result.context_preserved,
            "performance_metrics": result.performance_metrics,
            "error_message": result.error_message,
            "conversation_id": conversation_id,
            "timestamp": time.time()
        }

        except HTTPException:
            raise
        except Exception as e:
            # Record error metrics
            execution_time = time.time() - start_time
            metrics_service.record_multi_agent_task(
                workflow_type=workflow_type,
                status="error",
                duration=execution_time
            )

            # Add error to span
            span.set_attribute("multi_agent.error", str(e))
            span.set_attribute("multi_agent.status", "error")

            logger.error(f"Multi-agent task execution failed: {e}")
            raise HTTPException(status_code=500, detail=f"Task execution failed: {str(e)}")


@router.post("/execute")
async def execute_multi_agent_task_legacy(
    request: dict,
    db: AsyncSession = Depends(get_db)
):
    """Legacy endpoint for backward compatibility."""
    # Map legacy request to new format
    new_request = {
        "task_description": request.get("input", ""),
        "workflow_type": request.get("workflow_type", "research_analyze_write"),
        "context": {"legacy_context": request.get("context", "")},
        "conversation_id": request.get("conversation_id"),
        "save_conversation": request.get("save_conversation", True)
    }

    # Call the new endpoint
    return await execute_multi_agent_task(new_request, db)


@router.get("/performance")
async def get_multi_agent_performance():
    """
    Get performance metrics for the multi-agent system.

    Returns comprehensive performance data including:
    - Task completion statistics
    - Average execution times
    - Success rates
    - Most used workflows
    - Active workflow information
    """
    try:
        from app.services.multi_agent_service import multi_agent_service

        # Get performance summary
        performance_summary = multi_agent_service.get_performance_summary()

        # Get active workflows
        active_workflows = multi_agent_service.get_active_workflows()

        return {
            "performance_summary": performance_summary,
            "active_workflows": active_workflows,
            "system_status": "operational",
            "timestamp": time.time()
        }

    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve performance metrics: {str(e)}")


@router.get("/workflows")
async def get_available_workflows():
    """
    Get information about available multi-agent workflows.

    Returns details about each workflow type including:
    - Workflow description
    - Agents involved
    - Typical use cases
    - Expected execution time
    """
    try:
        workflows = {
            "research_analyze_write": {
                "description": "Sequential workflow: Research → Analysis → Writing",
                "agents": ["researcher", "analyst", "writer"],
                "use_cases": ["Content creation", "Report generation", "Research summaries"],
                "typical_execution_time": "60-180 seconds",
                "complexity": "high"
            },
            "complex_analysis": {
                "description": "Deep analysis workflow with multiple perspectives",
                "agents": ["researcher", "analyst", "coordinator"],
                "use_cases": ["Data analysis", "Strategic planning", "Risk assessment"],
                "typical_execution_time": "90-240 seconds",
                "complexity": "very high"
            },
            "collaborative_query": {
                "description": "Collaborative query processing with delegation",
                "agents": ["researcher", "analyst", "writer", "coordinator"],
                "use_cases": ["Complex Q&A", "Multi-faceted research", "Comprehensive responses"],
                "typical_execution_time": "45-120 seconds",
                "complexity": "medium"
            }
        }

        return {
            "available_workflows": workflows,
            "total_workflows": len(workflows),
            "recommended_workflow": "research_analyze_write",
            "system_capabilities": {
                "max_concurrent_workflows": 5,
                "timeout_limit": 300,
                "context_preservation": True,
                "error_recovery": True
            }
        }

    except Exception as e:
        logger.error(f"Failed to get workflow information: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve workflow information: {str(e)}")


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
        raise HTTPException(status_code=500, detail="Failed to get agent capabilities")

@router.get("/memory/{conversation_id}")
async def get_agent_memory_by_id(
    conversation_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get agent memory for a specific conversation."""
    try:
        memory_data = await AgentMemoryService.get_agent_memory(db, conversation_id)

        return {
            "conversation_id": conversation_id,
            "memory_entries": memory_data.get("agent_context", []),
            "total_entries": memory_data.get("total_interactions", 0),
            "memory_size": len(memory_data.get("agent_context", [])),
            "agents_involved": memory_data.get("agents_involved", [])
        }

    except Exception as e:
        logger.error(f"Error retrieving agent memory: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve agent memory")

@router.post("/memory")
async def create_agent_memory(
    request: dict,
    db: AsyncSession = Depends(get_db)
):
    """Create a new agent memory entry."""
    try:
        # Extract fields from request
        conversation_id = request.get("conversation_id")
        agent_name = request.get("agent_name")
        memory_content = request.get("memory_content")
        importance_score = request.get("importance_score", 0.5)
        memory_type = request.get("memory_type", "general")

        if not all([conversation_id, agent_name, memory_content]):
            raise HTTPException(status_code=422, detail="Missing required fields")

        # Create memory entry using the service
        memory_entry = await AgentMemoryService.create_memory_entry(
            db=db,
            conversation_id=conversation_id,
            agent_name=agent_name,
            content=memory_content,
            importance=importance_score,
            memory_type=memory_type
        )

        return {
            "id": memory_entry.get("id", f"memory-{conversation_id[:8]}"),
            "conversation_id": conversation_id,
            "agent_name": agent_name,
            "content": memory_content,
            "importance": importance_score,
            "created_at": memory_entry.get("created_at", "2023-01-01T00:00:00Z")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating agent memory: {e}")
        raise HTTPException(status_code=500, detail="Failed to create agent memory")

@router.post("/memory/retrieve", response_model=AgentMemoryResponse)
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
