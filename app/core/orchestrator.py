"""
Enhanced Orchestrator for Phase 5 - Agent Orchestration & Scalability.
Coordinates between different system components and manages asynchronous task execution.
"""

import logging
import time
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from dataclasses import dataclass
from app.core.multi_agent import multi_agent_orchestrator
from app.core.rag_system import production_rag_system

logger = logging.getLogger(__name__)

class TaskType(Enum):
    """Enumeration of available task types."""
    AGENT_CHAT = "agent_chat"
    MULTI_AGENT_WORKFLOW = "multi_agent_workflow"
    DOCUMENT_SEARCH = "document_search"
    RAG_QUERY = "rag_query"
    DOCUMENT_PROCESSING = "document_processing"
    SYSTEM_ANALYSIS = "system_analysis"
    COMPREHENSIVE_WORKFLOW = "comprehensive_workflow"
    HEALTH_CHECK = "health_check"
    DATA_CLEANUP = "data_cleanup"

class ExecutionMode(Enum):
    """Enumeration of execution modes."""
    SYNCHRONOUS = "sync"
    ASYNCHRONOUS = "async"

@dataclass
class TaskRequest:
    """Data class for task requests."""
    task_type: TaskType
    payload: Dict[str, Any]
    execution_mode: ExecutionMode = ExecutionMode.SYNCHRONOUS
    priority: int = 1
    timeout: Optional[int] = None

@dataclass
class TaskResult:
    """Data class for task results."""
    task_id: Optional[str]
    status: str
    result: Optional[Dict[str, Any]]
    execution_time: float
    error: Optional[str] = None

class EnhancedOrchestrator:
    """
    Enhanced orchestrator that coordinates between all system components
    and manages both synchronous and asynchronous task execution.
    """
    
    def __init__(self):
        self.supported_tasks = {
            TaskType.AGENT_CHAT: self._handle_agent_chat,
            TaskType.MULTI_AGENT_WORKFLOW: self._handle_multi_agent_workflow,
            TaskType.DOCUMENT_SEARCH: self._handle_document_search,
            TaskType.RAG_QUERY: self._handle_rag_query,
            TaskType.DOCUMENT_PROCESSING: self._handle_document_processing,
            TaskType.SYSTEM_ANALYSIS: self._handle_system_analysis,
            TaskType.COMPREHENSIVE_WORKFLOW: self._handle_comprehensive_workflow,
            TaskType.HEALTH_CHECK: self._handle_health_check,
            TaskType.DATA_CLEANUP: self._handle_data_cleanup,
        }
    
    async def execute_task(self, task_request: TaskRequest) -> TaskResult:
        """
        Execute a task request either synchronously or asynchronously.
        
        Args:
            task_request: The task request to execute
        
        Returns:
            TaskResult containing execution results
        """
        start_time = time.time()
        
        try:
            logger.info(f"Executing task: {task_request.task_type.value} in {task_request.execution_mode.value} mode")
            
            # Check if task type is supported
            if task_request.task_type not in self.supported_tasks:
                return TaskResult(
                    task_id=None,
                    status="error",
                    result=None,
                    execution_time=time.time() - start_time,
                    error=f"Unsupported task type: {task_request.task_type.value}"
                )
            
            # Execute based on mode
            if task_request.execution_mode == ExecutionMode.ASYNCHRONOUS:
                return await self._execute_async_task(task_request, start_time)
            else:
                return await self._execute_sync_task(task_request, start_time)
                
        except Exception as e:
            logger.error(f"Task execution failed: {str(e)}")
            return TaskResult(
                task_id=None,
                status="error",
                result=None,
                execution_time=time.time() - start_time,
                error=str(e)
            )
    
    async def _execute_async_task(self, task_request: TaskRequest, start_time: float) -> TaskResult:
        """Execute task asynchronously using Celery."""
        try:
            # Import Celery tasks
            from app.tasks.agent_tasks import (
                run_multi_agent_workflow_task,
                run_enhanced_agent_chat_task,
                batch_process_conversations_task
            )
            from app.tasks.document_tasks import (
                process_document_batch_task,
                rebuild_vector_index_task,
                run_complex_rag_query_task,
                analyze_document_collection_task
            )
            from app.tasks.orchestration_tasks import (
                run_comprehensive_workflow_task,
                system_health_check_task,
                cleanup_old_data_task
            )
            
            # Delegate to appropriate Celery task
            task_result = None
            
            if task_request.task_type == TaskType.MULTI_AGENT_WORKFLOW:
                task_result = run_multi_agent_workflow_task.delay(
                    workflow_type=task_request.payload.get("workflow_type", "simple_research"),
                    input_data=task_request.payload.get("input", ""),
                    conversation_id=task_request.payload.get("conversation_id"),
                    save_conversation=task_request.payload.get("save_conversation", True)
                )
            
            elif task_request.task_type == TaskType.AGENT_CHAT:
                task_result = run_enhanced_agent_chat_task.delay(
                    input_data=task_request.payload.get("input", ""),
                    conversation_id=task_request.payload.get("conversation_id"),
                    use_multi_agent=task_request.payload.get("use_multi_agent", False),
                    use_rag=task_request.payload.get("use_rag", False),
                    save_conversation=task_request.payload.get("save_conversation", True)
                )
            
            elif task_request.task_type == TaskType.RAG_QUERY:
                task_result = run_complex_rag_query_task.delay(
                    query=task_request.payload.get("query", ""),
                    search_limit=task_request.payload.get("search_limit", 5),
                    use_multi_agent=task_request.payload.get("use_multi_agent", False),
                    conversation_id=task_request.payload.get("conversation_id"),
                    save_conversation=task_request.payload.get("save_conversation", True)
                )
            
            elif task_request.task_type == TaskType.DOCUMENT_PROCESSING:
                task_result = process_document_batch_task.delay(
                    document_data_list=task_request.payload.get("documents", [])
                )
            
            elif task_request.task_type == TaskType.SYSTEM_ANALYSIS:
                analysis_type = task_request.payload.get("analysis_type", "summary")
                if analysis_type == "document_collection":
                    task_result = analyze_document_collection_task.delay(analysis_type)
                else:
                    task_result = system_health_check_task.delay()
            
            elif task_request.task_type == TaskType.COMPREHENSIVE_WORKFLOW:
                task_result = run_comprehensive_workflow_task.delay(
                    workflow_config=task_request.payload
                )
            
            elif task_request.task_type == TaskType.HEALTH_CHECK:
                task_result = system_health_check_task.delay()
            
            elif task_request.task_type == TaskType.DATA_CLEANUP:
                task_result = cleanup_old_data_task.delay(
                    days_old=task_request.payload.get("days_old", 30)
                )
            
            if task_result:
                return TaskResult(
                    task_id=task_result.id,
                    status="dispatched",
                    result={"message": "Task dispatched for asynchronous execution"},
                    execution_time=time.time() - start_time
                )
            else:
                return TaskResult(
                    task_id=None,
                    status="error",
                    result=None,
                    execution_time=time.time() - start_time,
                    error="Failed to dispatch async task"
                )
                
        except Exception as e:
            logger.error(f"Async task execution failed: {str(e)}")
            return TaskResult(
                task_id=None,
                status="error",
                result=None,
                execution_time=time.time() - start_time,
                error=f"Async execution failed: {str(e)}"
            )
    
    async def _execute_sync_task(self, task_request: TaskRequest, start_time: float) -> TaskResult:
        """Execute task synchronously."""
        try:
            # Generate a task ID for synchronous tasks
            import uuid
            task_id = f"sync-{uuid.uuid4().hex[:8]}"

            handler = self.supported_tasks[task_request.task_type]
            result = await handler(task_request.payload)

            return TaskResult(
                task_id=task_id,
                status="completed",
                result=result,
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Sync task execution failed: {str(e)}")
            # Generate a task ID even for failed tasks
            import uuid
            task_id = f"sync-{uuid.uuid4().hex[:8]}"

            return TaskResult(
                task_id=task_id,
                status="error",
                result=None,
                execution_time=time.time() - start_time,
                error=str(e)
            )
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get the status of an asynchronous task.
        
        Args:
            task_id: The Celery task ID
        
        Returns:
            Dict containing task status information
        """
        try:
            from app.core.celery_app import celery_app
            
            task_result = celery_app.AsyncResult(task_id)
            
            return {
                "task_id": task_id,
                "status": task_result.status,
                "result": task_result.result if task_result.ready() else None,
                "info": task_result.info,
                "ready": task_result.ready(),
                "successful": task_result.successful() if task_result.ready() else None,
                "failed": task_result.failed() if task_result.ready() else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get task status: {str(e)}")
            return {
                "task_id": task_id,
                "status": "unknown",
                "error": str(e)
            }
    
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get orchestrator capabilities and supported task types.
        
        Returns:
            Dict containing capabilities information
        """
        return {
            "supported_tasks": [task_type.value for task_type in self.supported_tasks.keys()],
            "execution_modes": [mode.value for mode in ExecutionMode],
            "features": {
                "asynchronous_execution": True,
                "task_monitoring": True,
                "multi_agent_coordination": True,
                "document_processing": True,
                "rag_capabilities": True,
                "system_analysis": True,
                "health_monitoring": True
            },
            "version": "5.0.0"
        }
    
    # Synchronous task handlers
    async def _handle_agent_chat(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle basic agent chat synchronously."""
        from app.core.agent import agent_graph_app
        
        agent_input = {
            "input": payload.get("input", ""),
            "chat_history": payload.get("chat_history", [])
        }
        
        final_state = {}
        for state in agent_graph_app.stream(agent_input):
            final_state = state
        
        return {
            "output": final_state,
            "input": payload.get("input", ""),
            "execution_mode": "synchronous"
        }
    
    async def _handle_multi_agent_workflow(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle multi-agent workflow synchronously."""
        workflow_result = await multi_agent_orchestrator.execute_workflow(
            workflow_type=payload.get("workflow_type", "simple_research"),
            input_data=payload.get("input", ""),
            context=payload.get("context", [])
        )
        
        return {
            "result": workflow_result.get("result", ""),
            "agents_used": workflow_result.get("agents_used", []),
            "execution_time": workflow_result.get("execution_time", 0),
            "workflow_type": payload.get("workflow_type", "simple_research"),
            "execution_mode": "synchronous"
        }
    
    async def _handle_document_search(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle document search synchronously."""
        from app.database.database import AsyncSessionLocal
        from app.services.document_service import DocumentService
        
        async with AsyncSessionLocal() as db:
            search_results, search_id = await DocumentService.semantic_search(
                db=db,
                query=payload.get("query", ""),
                limit=payload.get("limit", 5),
                score_threshold=payload.get("score_threshold", 0.1),
                search_type=payload.get("search_type", "chunks")
            )
            
            return {
                "query": payload.get("query", ""),
                "results": [
                    {
                        "content": result.content,
                        "score": result.score,
                        "document_title": result.document_title
                    }
                    for result in search_results
                ],
                "search_id": search_id,
                "total_found": len(search_results),
                "execution_mode": "synchronous"
            }
    
    async def _handle_rag_query(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle RAG query synchronously."""
        from app.database.database import AsyncSessionLocal
        
        async with AsyncSessionLocal() as db:
            # Use the new ProductionRAGSystem
            rag_result = await production_rag_system.generate_response(
                query=payload.get("query", ""),
                context_limit=payload.get("search_limit", 5),
                certainty_threshold=payload.get("score_threshold", 0.7),
                conversation_id=payload.get("conversation_id")
            )

            # Convert to expected format for backward compatibility
            rag_result = {
                "query": payload.get("query", ""),
                "response": rag_result.answer,
                "sources": rag_result.sources,
                "confidence": rag_result.confidence,
                "context_used": rag_result.context_used,
                "query_time": rag_result.query_time_ms,
                "timestamp": rag_result.timestamp
            }
            
            return {
                "query": payload.get("query", ""),
                "response": rag_result.get("response", ""),
                "retrieved_documents": rag_result.get("retrieved_documents", []),
                "context_used": rag_result.get("context_used", False),
                "execution_mode": "synchronous"
            }
    
    async def _handle_document_processing(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle document processing synchronously."""
        return {
            "message": "Document processing requires asynchronous execution",
            "recommendation": "Use async mode for document processing tasks",
            "execution_mode": "synchronous"
        }
    
    async def _handle_system_analysis(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system analysis synchronously."""
        analysis_type = payload.get("analysis_type", "basic")
        
        if analysis_type == "basic":
            return {
                "analysis_type": analysis_type,
                "timestamp": time.time(),
                "components": {
                    "orchestrator": "operational",
                    "multi_agent": "operational",
                    "rag_system": "operational",
                    "document_service": "operational"
                },
                "execution_mode": "synchronous"
            }
        else:
            return {
                "message": "Advanced system analysis requires asynchronous execution",
                "recommendation": "Use async mode for detailed system analysis",
                "execution_mode": "synchronous"
            }
    
    async def _handle_comprehensive_workflow(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle comprehensive workflow synchronously."""
        return {
            "message": "Comprehensive workflows require asynchronous execution",
            "recommendation": "Use async mode for comprehensive workflows",
            "execution_mode": "synchronous"
        }
    
    async def _handle_health_check(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle health check synchronously."""
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "orchestrator": "operational",
            "execution_mode": "synchronous"
        }
    
    async def _handle_data_cleanup(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle data cleanup synchronously."""
        return {
            "message": "Data cleanup requires asynchronous execution",
            "recommendation": "Use async mode for data cleanup tasks",
            "execution_mode": "synchronous"
        }

# Global orchestrator instance
enhanced_orchestrator = EnhancedOrchestrator()
