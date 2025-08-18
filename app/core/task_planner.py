# app/core/task_planner.py
"""
Advanced Task Planner for Goal Decomposition and Strategic Planning

This module implements an LLM-powered task planner that can decompose complex,
high-level objectives into structured, executable plans. The planner analyzes
goals, identifies required tools and resources, and creates step-by-step plans
that can be executed by the ProductionAgent.

Features:
- Goal analysis and intent extraction
- Multi-step plan generation with tool selection
- Plan validation and feasibility checking
- Dynamic plan adjustment based on execution results
- Hierarchical task decomposition
- Resource and dependency management
"""

import logging
import json
import re
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum

from app.core.llm_manager import ProductionLLMManager
from app.tools import get_tool_registry

logger = logging.getLogger(__name__)


def enum_serializer(obj):
    """Custom JSON serializer for Enum objects."""
    if isinstance(obj, Enum):
        return obj.value
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class PlanStepType(Enum):
    """Types of plan steps."""
    RESEARCH = "research"
    ANALYSIS = "analysis"
    CALCULATION = "calculation"
    COMMUNICATION = "communication"
    CREATION = "creation"
    VALIDATION = "validation"
    EXECUTION = "execution"
    DECISION = "decision"


class PlanStepStatus(Enum):
    """Status of plan steps."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PlanStep:
    """Represents a single step in an execution plan."""
    step_id: str
    step_number: int
    title: str
    description: str
    step_type: PlanStepType
    required_tools: List[str]
    expected_output: str
    dependencies: List[str]  # List of step_ids this step depends on
    estimated_duration: int  # Estimated duration in seconds
    status: PlanStepStatus = PlanStepStatus.PENDING
    actual_output: Optional[str] = None
    execution_time: Optional[float] = None
    error_message: Optional[str] = None
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()


@dataclass
class ExecutionPlan:
    """Represents a complete execution plan for a complex goal."""
    plan_id: str
    goal: str
    goal_type: str
    complexity_score: float
    total_steps: int
    estimated_duration: int
    steps: List[PlanStep]
    required_tools: List[str]
    success_criteria: List[str]
    fallback_strategies: List[str]
    created_at: str = None
    status: str = "created"
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()


class TaskPlanner:
    """
    Advanced task planner for decomposing complex goals into executable plans.
    
    The TaskPlanner uses LLM-powered analysis to:
    1. Analyze complex goals and extract intent
    2. Identify required tools and resources
    3. Generate structured, step-by-step execution plans
    4. Validate plan feasibility and dependencies
    5. Adjust plans based on execution feedback
    """
    
    def __init__(self):
        """Initialize the TaskPlanner with LLM and tool registry."""
        self.llm_manager = ProductionLLMManager()
        self.tool_registry = get_tool_registry()
        self.planning_prompt = self._create_planning_prompt()
        self.adjustment_prompt = self._create_adjustment_prompt()
        
        logger.info("TaskPlanner initialized with advanced planning capabilities")
    
    def _create_planning_prompt(self) -> str:
        """Create the planning prompt template."""
        available_tools = self.tool_registry.list_tools()
        tool_descriptions = []
        
        for tool_name in available_tools:
            tool_info = self.tool_registry.get_tool(tool_name)
            if tool_info:
                tool_descriptions.append(f"- {tool_name}: {tool_info.description}")
        
        tools_text = "\n".join(tool_descriptions)
        
        return f"""You are an advanced AI task planner. Your role is to analyze complex goals and decompose them into structured, executable plans.

AVAILABLE TOOLS:
{tools_text}

PLANNING INSTRUCTIONS:
1. Analyze the goal to understand its complexity and requirements
2. Break down the goal into logical, sequential steps
3. For each step, identify:
   - What needs to be accomplished
   - Which tools are required
   - Expected output or outcome
   - Dependencies on other steps
   - Estimated duration

4. Create a comprehensive plan that is:
   - Logical and well-sequenced
   - Achievable with available tools
   - Detailed enough for execution
   - Includes validation and error handling

RESPONSE FORMAT:
You must respond with a valid JSON object containing the execution plan. Use this exact structure:

{{
  "goal_analysis": {{
    "goal": "The original goal",
    "goal_type": "research|analysis|creation|communication|calculation|mixed",
    "complexity_score": 0.1-1.0,
    "key_requirements": ["requirement1", "requirement2"]
  }},
  "execution_plan": {{
    "total_steps": number,
    "estimated_duration": seconds,
    "steps": [
      {{
        "step_id": "step_1",
        "step_number": 1,
        "title": "Step title",
        "description": "Detailed description of what to do",
        "step_type": "research|analysis|calculation|communication|creation|validation|execution|decision",
        "required_tools": ["tool1", "tool2"],
        "expected_output": "What this step should produce",
        "dependencies": [],
        "estimated_duration": seconds
      }}
    ],
    "success_criteria": ["criteria1", "criteria2"],
    "fallback_strategies": ["strategy1", "strategy2"]
  }}
}}

GOAL TO PLAN: {{goal}}

Generate a comprehensive execution plan for this goal:"""
    
    def _create_adjustment_prompt(self) -> str:
        """Create the plan adjustment prompt template."""
        return """You are adjusting an execution plan based on new information or step failures.

ORIGINAL PLAN:
{original_plan}

EXECUTION STATUS:
{execution_status}

ADJUSTMENT NEEDED:
{adjustment_reason}

Please provide an updated plan that addresses the issues while maintaining the original goal. 
Respond with the same JSON format as the original plan, but with necessary modifications.

UPDATED PLAN:"""
    
    async def analyze_and_plan(self, goal: str) -> ExecutionPlan:
        """
        Analyze a complex goal and generate a structured execution plan.
        
        Args:
            goal: The high-level goal to decompose
            
        Returns:
            ExecutionPlan with structured steps and metadata
        """
        try:
            logger.info(f"Analyzing goal for planning: {goal[:100]}...")
            
            # Generate plan using LLM
            prompt = self.planning_prompt.format(goal=goal)
            
            response = await self.llm_manager.generate_response(
                prompt=prompt,
                max_tokens=2000,
                temperature=0.1  # Low temperature for consistent planning
            )
            
            # Parse the JSON response
            plan_data = self._parse_plan_response(response)
            
            # Create ExecutionPlan object
            execution_plan = self._create_execution_plan(goal, plan_data)
            
            # Validate the plan
            validation_result = self._validate_plan(execution_plan)
            if not validation_result["valid"]:
                logger.warning(f"Plan validation issues: {validation_result['issues']}")
                # Attempt to fix common issues
                execution_plan = self._fix_plan_issues(execution_plan, validation_result["issues"])
            
            logger.info(f"Generated execution plan with {execution_plan.total_steps} steps")
            return execution_plan
            
        except Exception as e:
            logger.error(f"Error in goal analysis and planning: {e}", exc_info=True)
            # Return a simple fallback plan
            return self._create_fallback_plan(goal)
    
    def _parse_plan_response(self, response: str) -> Dict[str, Any]:
        """Parse the LLM response into structured plan data."""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse plan JSON: {e}")
            logger.debug(f"Response content: {response}")
            raise ValueError(f"Invalid JSON in plan response: {e}")
    
    def _create_execution_plan(self, goal: str, plan_data: Dict[str, Any]) -> ExecutionPlan:
        """Create ExecutionPlan object from parsed plan data."""
        goal_analysis = plan_data.get("goal_analysis", {})
        execution_plan_data = plan_data.get("execution_plan", {})
        
        # Create plan steps
        steps = []
        for step_data in execution_plan_data.get("steps", []):
            step = PlanStep(
                step_id=step_data.get("step_id", f"step_{len(steps) + 1}"),
                step_number=step_data.get("step_number", len(steps) + 1),
                title=step_data.get("title", "Untitled Step"),
                description=step_data.get("description", ""),
                step_type=PlanStepType(step_data.get("step_type", "execution")),
                required_tools=step_data.get("required_tools", []),
                expected_output=step_data.get("expected_output", ""),
                dependencies=step_data.get("dependencies", []),
                estimated_duration=step_data.get("estimated_duration", 30)
            )
            steps.append(step)
        
        # Collect all required tools
        all_required_tools = set()
        for step in steps:
            all_required_tools.update(step.required_tools)
        
        # Create execution plan
        plan_id = f"plan_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        return ExecutionPlan(
            plan_id=plan_id,
            goal=goal,
            goal_type=goal_analysis.get("goal_type", "mixed"),
            complexity_score=goal_analysis.get("complexity_score", 0.5),
            total_steps=len(steps),
            estimated_duration=sum(step.estimated_duration for step in steps),
            steps=steps,
            required_tools=list(all_required_tools),
            success_criteria=execution_plan_data.get("success_criteria", []),
            fallback_strategies=execution_plan_data.get("fallback_strategies", [])
        )
    
    def _validate_plan(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """Validate the execution plan for feasibility and correctness."""
        issues = []
        
        # Check if required tools are available
        available_tools = set(self.tool_registry.list_tools())
        for tool in plan.required_tools:
            if tool not in available_tools:
                issues.append(f"Required tool '{tool}' is not available")
        
        # Check step dependencies
        step_ids = {step.step_id for step in plan.steps}
        for step in plan.steps:
            for dep in step.dependencies:
                if dep not in step_ids:
                    issues.append(f"Step '{step.step_id}' depends on non-existent step '{dep}'")
        
        # Check for circular dependencies
        if self._has_circular_dependencies(plan.steps):
            issues.append("Plan contains circular dependencies")
        
        # Check step sequence
        for i, step in enumerate(plan.steps):
            if step.step_number != i + 1:
                issues.append(f"Step numbering inconsistency at step {step.step_id}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
    
    def _has_circular_dependencies(self, steps: List[PlanStep]) -> bool:
        """Check for circular dependencies in the plan."""
        # Create dependency graph
        graph = {step.step_id: step.dependencies for step in steps}
        
        # Use DFS to detect cycles
        visited = set()
        rec_stack = set()
        
        def has_cycle(node):
            if node in rec_stack:
                return True
            if node in visited:
                return False
            
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if has_cycle(neighbor):
                    return True
            
            rec_stack.remove(node)
            return False
        
        for step_id in graph:
            if step_id not in visited:
                if has_cycle(step_id):
                    return True
        
        return False
    
    def _fix_plan_issues(self, plan: ExecutionPlan, issues: List[str]) -> ExecutionPlan:
        """Attempt to fix common plan issues."""
        # For now, just log the issues and return the original plan
        # In a more advanced implementation, we could automatically fix some issues
        logger.warning(f"Plan issues detected but not automatically fixed: {issues}")
        return plan
    
    def _create_fallback_plan(self, goal: str) -> ExecutionPlan:
        """Create a simple fallback plan when planning fails."""
        logger.info("Creating fallback plan for goal")
        
        fallback_step = PlanStep(
            step_id="fallback_step_1",
            step_number=1,
            title="Execute Goal Directly",
            description=f"Attempt to address the goal directly: {goal}",
            step_type=PlanStepType.EXECUTION,
            required_tools=["web_search"],
            expected_output="Best effort response to the goal",
            dependencies=[],
            estimated_duration=60
        )
        
        plan_id = f"fallback_plan_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        return ExecutionPlan(
            plan_id=plan_id,
            goal=goal,
            goal_type="mixed",
            complexity_score=0.3,
            total_steps=1,
            estimated_duration=60,
            steps=[fallback_step],
            required_tools=["web_search"],
            success_criteria=["Provide a reasonable response to the goal"],
            fallback_strategies=["Use basic ReAct pattern if planning fails"]
        )
    
    async def adjust_plan(self, plan: ExecutionPlan, execution_status: Dict[str, Any], 
                         adjustment_reason: str) -> ExecutionPlan:
        """
        Adjust an execution plan based on execution results or failures.
        
        Args:
            plan: The original execution plan
            execution_status: Current status of plan execution
            adjustment_reason: Reason for the adjustment
            
        Returns:
            Updated ExecutionPlan
        """
        try:
            logger.info(f"Adjusting plan {plan.plan_id}: {adjustment_reason}")
            
            # Create adjustment prompt
            prompt = self.adjustment_prompt.format(
                original_plan=json.dumps(asdict(plan), indent=2, default=enum_serializer),
                execution_status=json.dumps(execution_status, indent=2, default=enum_serializer),
                adjustment_reason=adjustment_reason
            )
            
            response = await self.llm_manager.generate_response(
                prompt=prompt,
                max_tokens=2000,
                temperature=0.1
            )
            
            # Parse and create updated plan
            plan_data = self._parse_plan_response(response)
            updated_plan = self._create_execution_plan(plan.goal, plan_data)
            
            # Preserve plan ID and update status
            updated_plan.plan_id = plan.plan_id
            updated_plan.status = "adjusted"
            
            logger.info(f"Plan adjusted: {plan.total_steps} -> {updated_plan.total_steps} steps")
            return updated_plan
            
        except Exception as e:
            logger.error(f"Error adjusting plan: {e}", exc_info=True)
            # Return original plan if adjustment fails
            return plan
    
    def get_next_executable_step(self, plan: ExecutionPlan) -> Optional[PlanStep]:
        """
        Get the next step that can be executed based on dependencies.
        
        Args:
            plan: The execution plan
            
        Returns:
            Next executable PlanStep or None if no steps are ready
        """
        completed_steps = {
            step.step_id for step in plan.steps 
            if step.status == PlanStepStatus.COMPLETED
        }
        
        for step in plan.steps:
            if step.status == PlanStepStatus.PENDING:
                # Check if all dependencies are completed
                if all(dep in completed_steps for dep in step.dependencies):
                    return step
        
        return None
    
    def update_step_status(self, plan: ExecutionPlan, step_id: str, 
                          status: PlanStepStatus, actual_output: Optional[str] = None,
                          execution_time: Optional[float] = None,
                          error_message: Optional[str] = None) -> None:
        """Update the status of a plan step."""
        for step in plan.steps:
            if step.step_id == step_id:
                step.status = status
                if actual_output is not None:
                    step.actual_output = actual_output
                if execution_time is not None:
                    step.execution_time = execution_time
                if error_message is not None:
                    step.error_message = error_message
                break
    
    def is_plan_complete(self, plan: ExecutionPlan) -> bool:
        """Check if all steps in the plan are completed."""
        return all(
            step.status in [PlanStepStatus.COMPLETED, PlanStepStatus.SKIPPED]
            for step in plan.steps
        )
    
    def get_plan_progress(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """Get progress information for the plan."""
        completed = sum(1 for step in plan.steps if step.status == PlanStepStatus.COMPLETED)
        failed = sum(1 for step in plan.steps if step.status == PlanStepStatus.FAILED)
        in_progress = sum(1 for step in plan.steps if step.status == PlanStepStatus.IN_PROGRESS)
        
        return {
            "total_steps": plan.total_steps,
            "completed_steps": completed,
            "failed_steps": failed,
            "in_progress_steps": in_progress,
            "completion_percentage": (completed / plan.total_steps) * 100 if plan.total_steps > 0 else 0,
            "is_complete": self.is_plan_complete(plan)
        }


# Global task planner instance
_task_planner = None

def get_task_planner() -> TaskPlanner:
    """Get the global TaskPlanner instance."""
    global _task_planner
    if _task_planner is None:
        _task_planner = TaskPlanner()
    return _task_planner
