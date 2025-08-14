"""
API endpoints for the enhanced orchestrator in Phase 5.
Provides task management and orchestration capabilities.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any, List, Optional
from app.api.v1.schemas.orchestrator import (
    TaskRequest as TaskRequestSchema,
    TaskResponse,
    TaskStatusResponse,
    OrchestratorCapabilities,
    WorkflowRequest,
    WorkflowResponse,
    HealthCheckResponse
)
from app.core.orchestrator import enhanced_orchestrator, TaskType, ExecutionMode, TaskRequest

router = APIRouter()

@router.post("/execute", response_model=TaskResponse)
async def execute_task(request: TaskRequestSchema):
    """
    Execute a task through the orchestrator.

    Args:
        request: Task request containing type, payload, and execution mode

    Returns:
        TaskResponse with execution results
    """
    try:
        # Convert schema to internal task request
        task_request = TaskRequest(
            task_type=TaskType(request.task_type),
            payload=request.payload,
            execution_mode=ExecutionMode(request.execution_mode),
            priority=request.priority,
            timeout=request.timeout
        )

        # Execute task
        result = await enhanced_orchestrator.execute_task(task_request)

        # Broadcast real-time task update
        try:
            from app.api.v1.websocket.endpoints import broadcast_task_progress
            progress = 1.0 if result.status == "completed" else 0.5
            await broadcast_task_progress(
                result.task_id,
                progress,
                result.status,
                result.result if result.status == "completed" else None
            )
        except Exception as e:
            logger.warning(f"Failed to broadcast task update: {e}")

        return TaskResponse(
            task_id=result.task_id,
            status=result.status,
            result=result.result,
            execution_time=result.execution_time,
            error=result.error
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid task type or execution mode: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Task execution failed: {str(e)}")

@router.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Get the status of an asynchronous task.

    Args:
        task_id: The task ID to check

    Returns:
        TaskStatusResponse with current task status
    """
    try:
        status_info = await enhanced_orchestrator.get_task_status(task_id)

        return TaskStatusResponse(
            task_id=task_id,
            status=status_info.get("status", "unknown"),
            result=status_info.get("result"),
            info=status_info.get("info"),
            ready=status_info.get("ready", False),
            successful=status_info.get("successful"),
            failed=status_info.get("failed"),
            error=status_info.get("error")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")

@router.get("/capabilities", response_model=OrchestratorCapabilities)
async def get_orchestrator_capabilities():
    """
    Get orchestrator capabilities and supported features.

    Returns:
        OrchestratorCapabilities with system capabilities
    """
    try:
        capabilities = enhanced_orchestrator.get_capabilities()

        return OrchestratorCapabilities(
            supported_tasks=capabilities["supported_tasks"],
            execution_modes=capabilities["execution_modes"],
            features=capabilities["features"],
            version=capabilities["version"]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get capabilities: {str(e)}")

@router.post("/workflow", response_model=WorkflowResponse)
async def execute_workflow(request: WorkflowRequest):
    """
    Execute a comprehensive workflow combining multiple system capabilities.

    Args:
        request: Workflow request with configuration and steps

    Returns:
        WorkflowResponse with workflow execution results
    """
    try:
        # Create task request for comprehensive workflow
        task_request = TaskRequest(
            task_type=TaskType.COMPREHENSIVE_WORKFLOW,
            payload={
                "name": request.name,
                "input": request.input,
                "steps": [step.dict() for step in request.steps],
                "conversation_id": request.conversation_id,
                "save_conversation": request.save_conversation
            },
            execution_mode=ExecutionMode(request.execution_mode),
            priority=request.priority
        )

        # Execute workflow
        result = await enhanced_orchestrator.execute_task(task_request)

        return WorkflowResponse(
            workflow_name=request.name,
            task_id=result.task_id,
            status=result.status,
            result=result.result,
            execution_time=result.execution_time,
            error=result.error
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {str(e)}")

@router.post("/health-check", response_model=HealthCheckResponse)
async def perform_health_check(async_mode: bool = False):
    """
    Perform a system health check.

    Args:
        async_mode: Whether to perform the health check asynchronously

    Returns:
        HealthCheckResponse with system health status
    """
    try:
        execution_mode = ExecutionMode.ASYNCHRONOUS if async_mode else ExecutionMode.SYNCHRONOUS

        task_request = TaskRequest(
            task_type=TaskType.HEALTH_CHECK,
            payload={},
            execution_mode=execution_mode
        )

        result = await enhanced_orchestrator.execute_task(task_request)

        return HealthCheckResponse(
            task_id=result.task_id,
            status=result.status,
            health_data=result.result,
            execution_time=result.execution_time,
            async_mode=async_mode
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@router.post("/agent/enhanced-chat")
async def enhanced_agent_chat(
    input: str,
    conversation_id: Optional[str] = None,
    use_multi_agent: bool = False,
    use_rag: bool = False,
    save_conversation: bool = True,
    async_mode: bool = False
):
    """
    Execute an enhanced agent chat with optional multi-agent and RAG capabilities.

    Args:
        input: User input message
        conversation_id: Optional conversation ID to continue
        use_multi_agent: Whether to use multi-agent processing
        use_rag: Whether to use RAG for document context
        save_conversation: Whether to save the conversation
        async_mode: Whether to execute asynchronously

    Returns:
        Enhanced chat response
    """
    try:
        execution_mode = ExecutionMode.ASYNCHRONOUS if async_mode else ExecutionMode.SYNCHRONOUS

        task_request = TaskRequest(
            task_type=TaskType.AGENT_CHAT,
            payload={
                "input": input,
                "conversation_id": conversation_id,
                "use_multi_agent": use_multi_agent,
                "use_rag": use_rag,
                "save_conversation": save_conversation
            },
            execution_mode=execution_mode
        )

        result = await enhanced_orchestrator.execute_task(task_request)

        return {
            "task_id": result.task_id,
            "status": result.status,
            "response": result.result,
            "execution_time": result.execution_time,
            "async_mode": async_mode,
            "error": result.error
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enhanced chat failed: {str(e)}")

@router.post("/multi-agent/workflow")
async def execute_multi_agent_workflow(
    workflow_type: str,
    input: str,
    conversation_id: Optional[str] = None,
    save_conversation: bool = True,
    async_mode: bool = False
):
    """
    Execute a multi-agent workflow.

    Args:
        workflow_type: Type of workflow to execute
        input: Input data for the workflow
        conversation_id: Optional conversation ID
        save_conversation: Whether to save the conversation
        async_mode: Whether to execute asynchronously

    Returns:
        Multi-agent workflow response
    """
    try:
        execution_mode = ExecutionMode.ASYNCHRONOUS if async_mode else ExecutionMode.SYNCHRONOUS

        task_request = TaskRequest(
            task_type=TaskType.MULTI_AGENT_WORKFLOW,
            payload={
                "workflow_type": workflow_type,
                "input": input,
                "conversation_id": conversation_id,
                "save_conversation": save_conversation
            },
            execution_mode=execution_mode
        )

        result = await enhanced_orchestrator.execute_task(task_request)

        return {
            "task_id": result.task_id,
            "status": result.status,
            "workflow_result": result.result,
            "execution_time": result.execution_time,
            "async_mode": async_mode,
            "error": result.error
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Multi-agent workflow failed: {str(e)}")

@router.post("/documents/rag")
async def execute_rag_query(
    query: str,
    search_limit: int = 5,
    use_multi_agent: bool = False,
    conversation_id: Optional[str] = None,
    save_conversation: bool = True,
    async_mode: bool = False
):
    """
    Execute a RAG query with optional multi-agent processing.

    Args:
        query: The query to process
        search_limit: Number of documents to retrieve
        use_multi_agent: Whether to use multi-agent processing
        conversation_id: Optional conversation ID
        save_conversation: Whether to save the conversation
        async_mode: Whether to execute asynchronously

    Returns:
        RAG query response
    """
    try:
        execution_mode = ExecutionMode.ASYNCHRONOUS if async_mode else ExecutionMode.SYNCHRONOUS

        task_request = TaskRequest(
            task_type=TaskType.RAG_QUERY,
            payload={
                "query": query,
                "search_limit": search_limit,
                "use_multi_agent": use_multi_agent,
                "conversation_id": conversation_id,
                "save_conversation": save_conversation
            },
            execution_mode=execution_mode
        )

        result = await enhanced_orchestrator.execute_task(task_request)

        return {
            "task_id": result.task_id,
            "status": result.status,
            "rag_result": result.result,
            "execution_time": result.execution_time,
            "async_mode": async_mode,
            "error": result.error
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG query failed: {str(e)}")

@router.post("/system/cleanup")
async def cleanup_system_data(days_old: int = 30):
    """
    Clean up old system data asynchronously.

    Args:
        days_old: Number of days old data should be to be considered for cleanup

    Returns:
        Cleanup task response
    """
    try:
        task_request = TaskRequest(
            task_type=TaskType.DATA_CLEANUP,
            payload={"days_old": days_old},
            execution_mode=ExecutionMode.ASYNCHRONOUS
        )

        result = await enhanced_orchestrator.execute_task(task_request)

        return {
            "task_id": result.task_id,
            "status": result.status,
            "message": f"Data cleanup task dispatched for data older than {days_old} days",
            "execution_time": result.execution_time
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data cleanup failed: {str(e)}")

@router.get("/system/status")
async def get_system_status():
    """
    Get comprehensive system status.

    Returns:
        System status information
    """
    try:
        task_request = TaskRequest(
            task_type=TaskType.SYSTEM_ANALYSIS,
            payload={"analysis_type": "basic"},
            execution_mode=ExecutionMode.SYNCHRONOUS
        )

        result = await enhanced_orchestrator.execute_task(task_request)

        return {
            "status": result.status,
            "system_info": result.result,
            "execution_time": result.execution_time,
            "orchestrator_version": "5.0.0"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"System status check failed: {str(e)}")
