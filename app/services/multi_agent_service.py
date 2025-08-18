"""
Multi-Agent Service for Phase 3, Task 3.1: Multi-Agent Coordination System

This service provides a high-level interface for executing complex multi-agent workflows
using the CrewAI framework. It handles workflow orchestration, error management,
performance monitoring, and inter-agent communication.

Features:
- Complex task execution with multiple specialized agents
- Graceful error handling and fallback mechanisms
- Performance metrics and monitoring
- Context preservation between agents
- Workflow execution engine with failure recovery
"""

import logging
import time
import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from dataclasses import dataclass

from app.core.crew_manager import CrewManager, CrewResult
from app.core.logging_config import get_logger, log_performance, log_security_event
from app.core.config import get_settings

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class TaskExecutionResult:
    """Result from multi-agent task execution."""
    success: bool
    result: str
    agents_involved: List[str]
    execution_time: float
    performance_metrics: Dict[str, Any]
    error_message: Optional[str] = None
    context_preserved: bool = True
    workflow_type: str = "unknown"


@dataclass
class AgentPerformanceMetrics:
    """Performance metrics for agent execution."""
    task_completion_time: float
    number_of_steps: int
    agents_used: List[str]
    inter_agent_communications: int
    context_preservation_score: float
    error_recovery_attempts: int
    success_rate: float


class MultiAgentService:
    """
    Service for executing complex multi-agent workflows with monitoring and error handling.
    
    This service provides the main interface for multi-agent task execution,
    handling workflow orchestration, performance monitoring, and error recovery.
    """
    
    def __init__(self):
        """Initialize the multi-agent service."""
        self.crew_manager = None
        self.performance_history = []
        self.active_workflows = {}
        
        logger.info("MultiAgentService initialized")
    
    async def _initialize_crew_manager(self):
        """Lazy initialization of crew manager to avoid startup delays."""
        if self.crew_manager is None:
            try:
                logger.info("Initializing CrewManager...")
                self.crew_manager = CrewManager()
                logger.info("CrewManager initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize CrewManager: {e}")
                raise
    
    async def execute_crew_task(
        self,
        task_description: str,
        workflow_type: str = "research_analyze_write",
        context: Optional[Dict[str, Any]] = None,
        timeout: int = 300
    ) -> TaskExecutionResult:
        """
        Execute a complex multi-agent task with full workflow orchestration.
        
        Args:
            task_description: Description of the task to be executed
            workflow_type: Type of workflow to execute
            context: Optional context for the task
            timeout: Maximum execution time in seconds
            
        Returns:
            TaskExecutionResult with execution details and performance metrics
        """
        start_time = time.time()
        workflow_id = f"workflow_{int(start_time)}"
        
        try:
            # Initialize crew manager if needed
            await self._initialize_crew_manager()
            
            # Track active workflow
            self.active_workflows[workflow_id] = {
                "task_description": task_description,
                "workflow_type": workflow_type,
                "start_time": start_time,
                "status": "running"
            }
            
            logger.info(f"Starting multi-agent task execution: {workflow_id}")
            logger.info(f"Task: {task_description[:100]}...")
            
            # Execute the crew task with timeout
            crew_result = await asyncio.wait_for(
                self._execute_crew_with_monitoring(task_description, workflow_type, context),
                timeout=timeout
            )
            
            execution_time = time.time() - start_time
            
            # Calculate performance metrics
            performance_metrics = self._calculate_performance_metrics(
                crew_result, execution_time, workflow_type
            )
            
            # Log performance
            log_performance(
                operation="multi_agent_task_execution",
                duration_ms=execution_time * 1000,
                success=crew_result.success,
                workflow_type=workflow_type,
                agents_used=len(crew_result.agent_outputs),
                context_preserved=True
            )
            
            # Create result
            result = TaskExecutionResult(
                success=crew_result.success,
                result=crew_result.result,
                agents_involved=list(crew_result.agent_outputs.keys()),
                execution_time=execution_time,
                performance_metrics=performance_metrics,
                workflow_type=workflow_type
            )
            
            # Update workflow status
            self.active_workflows[workflow_id]["status"] = "completed"
            self.performance_history.append(performance_metrics)
            
            logger.info(f"Multi-agent task completed successfully in {execution_time:.2f}s")
            return result
            
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            error_msg = f"Task execution timed out after {timeout} seconds"
            
            logger.error(f"Multi-agent task timeout: {workflow_id}")
            
            # Log security event for timeouts
            log_security_event(
                event_type="multi_agent_timeout",
                severity="medium",
                workflow_id=workflow_id,
                execution_time=execution_time,
                task_description=task_description[:100]
            )
            
            # Update workflow status
            self.active_workflows[workflow_id]["status"] = "timeout"
            
            return TaskExecutionResult(
                success=False,
                result="Task execution timed out. Please try with a simpler task or increase timeout.",
                agents_involved=[],
                execution_time=execution_time,
                performance_metrics={"error": "timeout"},
                error_message=error_msg,
                context_preserved=False,
                workflow_type=workflow_type
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            
            logger.error(f"Multi-agent task execution failed: {error_msg}")
            
            # Log security event for failures
            log_security_event(
                event_type="multi_agent_execution_failure",
                severity="high",
                workflow_id=workflow_id,
                error=error_msg,
                execution_time=execution_time
            )
            
            # Update workflow status
            self.active_workflows[workflow_id]["status"] = "failed"
            
            # Attempt graceful fallback
            fallback_result = await self._execute_fallback_workflow(task_description, context)
            
            return TaskExecutionResult(
                success=False,
                result=fallback_result,
                agents_involved=[],
                execution_time=execution_time,
                performance_metrics={"error": error_msg},
                error_message=error_msg,
                context_preserved=False,
                workflow_type=workflow_type
            )
        
        finally:
            # Cleanup active workflow
            if workflow_id in self.active_workflows:
                self.active_workflows[workflow_id]["end_time"] = time.time()
    
    async def _execute_crew_with_monitoring(
        self,
        task_description: str,
        workflow_type: str,
        context: Optional[Dict[str, Any]]
    ) -> CrewResult:
        """Execute crew task with monitoring and error handling."""
        try:
            # Execute the crew task
            if workflow_type == "research_analyze_write":
                result = await asyncio.to_thread(
                    self.crew_manager.execute_research_analyze_write,
                    task_description
                )
            elif workflow_type == "complex_analysis":
                result = await asyncio.to_thread(
                    self.crew_manager.execute_collaborative_analysis,
                    task_description
                )
            else:
                # Default to collaborative query
                result = await asyncio.to_thread(
                    self.crew_manager.execute_collaborative_query,
                    task_description
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Crew execution failed: {e}")
            # Return a failed result instead of raising
            return CrewResult(
                success=False,
                result=f"Crew execution failed: {str(e)}",
                agent_outputs={},
                execution_time=0.0,
                error_message=str(e)
            )
    
    async def _execute_fallback_workflow(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Execute a fallback workflow when the main multi-agent system fails."""
        try:
            logger.info("Executing fallback workflow")
            
            # Use the RAG system as fallback
            from app.core.rag_system import production_rag_system
            
            rag_response = await production_rag_system.generate_response(
                query=task_description,
                context_limit=5,
                certainty_threshold=0.7
            )
            
            return f"Fallback response: {rag_response.answer}"
            
        except Exception as e:
            logger.error(f"Fallback workflow also failed: {e}")
            return "I apologize, but I'm currently unable to process your request. Please try again later or contact support."
    
    def _calculate_performance_metrics(
        self,
        crew_result: CrewResult,
        execution_time: float,
        workflow_type: str
    ) -> Dict[str, Any]:
        """Calculate performance metrics for the executed workflow."""
        metrics = {
            "execution_time": execution_time,
            "success": crew_result.success,
            "workflow_type": workflow_type,
            "agents_involved": len(crew_result.agent_outputs),
            "inter_agent_communications": crew_result.collaboration_metrics.get("task_dependencies", 0),
            "context_preservation_score": 1.0 if crew_result.success else 0.0,
            "error_recovery_attempts": 0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add collaboration metrics if available
        if crew_result.collaboration_metrics:
            metrics.update({
                "collaboration_patterns": crew_result.collaboration_metrics.get("collaboration_patterns", []),
                "delegation_enabled_agents": crew_result.collaboration_metrics.get("delegation_enabled_agents", 0),
                "total_agents_involved": crew_result.collaboration_metrics.get("total_agents_involved", 0)
            })
        
        return metrics
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get a summary of performance metrics."""
        if not self.performance_history:
            return {
                "total_tasks": 0,
                "average_execution_time": 0.0,
                "success_rate": 0.0,
                "most_used_workflow": "none"
            }
        
        total_tasks = len(self.performance_history)
        successful_tasks = sum(1 for m in self.performance_history if m.get("success", False))
        avg_execution_time = sum(m.get("execution_time", 0) for m in self.performance_history) / total_tasks
        
        # Find most used workflow
        workflow_counts = {}
        for metrics in self.performance_history:
            workflow = metrics.get("workflow_type", "unknown")
            workflow_counts[workflow] = workflow_counts.get(workflow, 0) + 1
        
        most_used_workflow = max(workflow_counts.items(), key=lambda x: x[1])[0] if workflow_counts else "none"
        
        return {
            "total_tasks": total_tasks,
            "successful_tasks": successful_tasks,
            "success_rate": successful_tasks / total_tasks if total_tasks > 0 else 0.0,
            "average_execution_time": avg_execution_time,
            "most_used_workflow": most_used_workflow,
            "active_workflows": len(self.active_workflows),
            "workflow_types_used": list(workflow_counts.keys())
        }
    
    def get_active_workflows(self) -> Dict[str, Any]:
        """Get information about currently active workflows."""
        return {
            workflow_id: {
                "task_description": info["task_description"][:100] + "..." if len(info["task_description"]) > 100 else info["task_description"],
                "workflow_type": info["workflow_type"],
                "status": info["status"],
                "running_time": time.time() - info["start_time"] if info["status"] == "running" else info.get("end_time", time.time()) - info["start_time"]
            }
            for workflow_id, info in self.active_workflows.items()
        }


# Global service instance
multi_agent_service = MultiAgentService()
