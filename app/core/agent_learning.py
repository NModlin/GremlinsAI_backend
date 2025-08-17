# app/core/agent_learning.py
"""
Agent Learning and Adaptation System

This module implements the learning and adaptation capabilities for the ProductionAgent.
It enables the agent to analyze its performance, extract insights, and continuously
improve its strategies and decision-making processes.

Features:
- Performance analysis and self-reflection
- Learning insight extraction and storage
- Strategy adaptation based on historical performance
- Long-term memory of successful patterns and failures
- Continuous improvement through experience
"""

import logging
import json
import uuid
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum

import weaviate
from weaviate.classes.config import Configure, Property, DataType
from weaviate.exceptions import WeaviateBaseError

from app.core.llm_manager import ProductionLLMManager

logger = logging.getLogger(__name__)


class LearningType(Enum):
    """Types of learning insights."""
    STRATEGY_IMPROVEMENT = "strategy_improvement"
    TOOL_OPTIMIZATION = "tool_optimization"
    PLANNING_ENHANCEMENT = "planning_enhancement"
    ERROR_PATTERN = "error_pattern"
    SUCCESS_PATTERN = "success_pattern"
    EFFICIENCY_GAIN = "efficiency_gain"


class PerformanceCategory(Enum):
    """Performance assessment categories."""
    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    POOR = "poor"
    FAILED = "failed"


@dataclass
class PerformanceMetrics:
    """Metrics for evaluating agent performance."""
    success_rate: float
    efficiency_score: float  # Steps taken vs optimal steps
    tool_usage_effectiveness: float
    planning_accuracy: float
    execution_time_ratio: float  # Actual vs estimated time
    error_recovery_rate: float
    overall_score: float


@dataclass
class LearningInsight:
    """Represents a learning insight extracted from agent performance."""
    insight_id: str
    learning_type: LearningType
    title: str
    description: str
    context: str
    improvement_suggestion: str
    confidence_score: float
    applicable_scenarios: List[str]
    performance_impact: str
    created_at: str
    
    def __post_init__(self):
        if not self.insight_id:
            self.insight_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()


@dataclass
class AgentLearning:
    """Complete learning record for an agent task."""
    learning_id: str
    task_id: str
    agent_type: str
    original_query: str
    performance_category: PerformanceCategory
    performance_metrics: PerformanceMetrics
    task_transcript: Dict[str, Any]
    reflection_analysis: str
    learning_insights: List[LearningInsight]
    strategy_updates: List[str]
    created_at: str
    metadata: Dict[str, Any]
    
    def __post_init__(self):
        if not self.learning_id:
            self.learning_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
        if not self.metadata:
            self.metadata = {}


class AgentLearningService:
    """
    Service for managing agent learning and adaptation.
    
    This service handles:
    - Performance analysis and reflection
    - Learning insight extraction
    - Storage and retrieval of learning data
    - Strategy adaptation recommendations
    """
    
    def __init__(self, weaviate_client: Optional[weaviate.WeaviateClient] = None):
        """Initialize the learning service."""
        self.llm_manager = ProductionLLMManager()
        self.weaviate_client = weaviate_client
        self.reflection_prompt = self._create_reflection_prompt()
        
        # Initialize Weaviate schema if client provided
        if self.weaviate_client:
            self._ensure_learning_schema()
        
        logger.info("AgentLearningService initialized")
    
    def _create_reflection_prompt(self) -> str:
        """Create the self-reflection prompt template."""
        return """You are an AI agent analyzing your own performance on a completed task. Your goal is to identify areas for improvement and extract actionable insights for future tasks.

TASK PERFORMANCE DATA:
Original Query: {original_query}
Success: {success}
Total Steps: {total_steps}
Execution Time: {execution_time}
Plan Used: {plan_used}

EXECUTION TRANSCRIPT:
{transcript}

PERFORMANCE ANALYSIS INSTRUCTIONS:
1. Analyze the overall performance and identify strengths and weaknesses
2. Evaluate the effectiveness of tool choices and reasoning steps
3. Assess the quality of planning (if used) and execution strategy
4. Identify any inefficiencies, errors, or missed opportunities
5. Suggest specific improvements for similar tasks in the future

Please provide your analysis in the following JSON format:

{{
  "performance_assessment": {{
    "overall_rating": "excellent|good|average|poor|failed",
    "strengths": ["strength1", "strength2", ...],
    "weaknesses": ["weakness1", "weakness2", ...],
    "efficiency_score": 0.0-1.0,
    "tool_effectiveness": 0.0-1.0,
    "planning_quality": 0.0-1.0
  }},
  "learning_insights": [
    {{
      "type": "strategy_improvement|tool_optimization|planning_enhancement|error_pattern|success_pattern|efficiency_gain",
      "title": "Brief insight title",
      "description": "Detailed description of the insight",
      "improvement_suggestion": "Specific actionable improvement",
      "confidence": 0.0-1.0,
      "applicable_scenarios": ["scenario1", "scenario2"],
      "impact": "Expected performance impact"
    }}
  ],
  "strategy_recommendations": [
    "Specific strategy update or improvement recommendation"
  ],
  "reflection_summary": "Overall reflection on performance and key takeaways"
}}

REFLECTION ANALYSIS:"""
    
    def _ensure_learning_schema(self) -> None:
        """Ensure the AgentLearning schema exists in Weaviate."""
        try:
            # Check if AgentLearning class exists
            collections = self.weaviate_client.collections.list_all()
            if "AgentLearning" not in [col.name for col in collections]:
                self._create_learning_schema()
        except Exception as e:
            logger.error(f"Error checking/creating learning schema: {e}")
    
    def _create_learning_schema(self) -> None:
        """Create the AgentLearning schema in Weaviate."""
        try:
            logger.info("Creating AgentLearning schema in Weaviate...")
            
            self.weaviate_client.collections.create(
                name="AgentLearning",
                properties=[
                    Property(
                        name="learningId",
                        data_type=DataType.TEXT,
                        description="Unique learning record identifier"
                    ),
                    Property(
                        name="taskId",
                        data_type=DataType.TEXT,
                        description="Original task identifier"
                    ),
                    Property(
                        name="agentType",
                        data_type=DataType.TEXT,
                        description="Type of agent that performed the task"
                    ),
                    Property(
                        name="originalQuery",
                        data_type=DataType.TEXT,
                        description="Original user query or task"
                    ),
                    Property(
                        name="performanceCategory",
                        data_type=DataType.TEXT,
                        description="Performance assessment category"
                    ),
                    Property(
                        name="performanceMetrics",
                        data_type=DataType.OBJECT,
                        description="Detailed performance metrics"
                    ),
                    Property(
                        name="taskTranscript",
                        data_type=DataType.OBJECT,
                        description="Complete task execution transcript"
                    ),
                    Property(
                        name="reflectionAnalysis",
                        data_type=DataType.TEXT,
                        description="Self-reflection analysis text"
                    ),
                    Property(
                        name="learningInsights",
                        data_type=DataType.OBJECT_ARRAY,
                        description="Extracted learning insights"
                    ),
                    Property(
                        name="strategyUpdates",
                        data_type=DataType.TEXT_ARRAY,
                        description="Strategy update recommendations"
                    ),
                    Property(
                        name="createdAt",
                        data_type=DataType.DATE,
                        description="Learning record creation timestamp"
                    ),
                    Property(
                        name="metadata",
                        data_type=DataType.OBJECT,
                        description="Additional learning metadata"
                    ),
                    Property(
                        name="embedding",
                        data_type=DataType.NUMBER_ARRAY,
                        description="Learning content embedding for similarity search"
                    )
                ],
                vectorizer_config=Configure.Vectorizer.text2vec_transformers(
                    vectorize_collection_name=False
                )
            )
            
            logger.info("AgentLearning schema created successfully")
            
        except WeaviateBaseError as e:
            logger.error(f"Weaviate error creating learning schema: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating learning schema: {e}")
            raise
    
    async def analyze_performance(self, agent_result,
                                original_query: str, execution_time: float) -> AgentLearning:
        """
        Analyze agent performance and extract learning insights.
        
        Args:
            agent_result: The result from agent execution
            original_query: The original user query
            execution_time: Total execution time in seconds
            
        Returns:
            AgentLearning object with analysis and insights
        """
        try:
            logger.info(f"Analyzing agent performance for task: {original_query[:100]}...")
            
            # Create task transcript
            transcript = self._create_task_transcript(agent_result, execution_time)
            
            # Generate reflection analysis
            reflection_analysis = await self._generate_reflection(
                original_query, agent_result, transcript
            )
            
            # Parse reflection and extract insights
            performance_metrics, insights, strategy_updates = self._parse_reflection(reflection_analysis)
            
            # Determine performance category
            performance_category = self._categorize_performance(performance_metrics, agent_result.success)
            
            # Create learning record
            learning = AgentLearning(
                learning_id=str(uuid.uuid4()),
                task_id=str(uuid.uuid4()),  # Could be passed in if available
                agent_type="production_agent",
                original_query=original_query,
                performance_category=performance_category,
                performance_metrics=performance_metrics,
                task_transcript=transcript,
                reflection_analysis=reflection_analysis,
                learning_insights=insights,
                strategy_updates=strategy_updates,
                created_at=datetime.utcnow().isoformat(),
                metadata={
                    "execution_time": execution_time,
                    "plan_used": agent_result.plan_used,
                    "total_steps": agent_result.total_steps,
                    "success": agent_result.success
                }
            )
            
            logger.info(f"Performance analysis completed: {performance_category.value}")
            return learning
            
        except Exception as e:
            logger.error(f"Error analyzing performance: {e}", exc_info=True)
            raise
    
    def _create_task_transcript(self, agent_result, execution_time: float) -> Dict[str, Any]:
        """Create a comprehensive task transcript."""
        transcript = {
            "execution_summary": {
                "success": agent_result.success,
                "total_steps": agent_result.total_steps,
                "execution_time": execution_time,
                "plan_used": agent_result.plan_used,
                "error_message": agent_result.error_message
            },
            "reasoning_steps": [],
            "execution_plan": None,
            "final_answer": agent_result.final_answer
        }
        
        # Add reasoning steps
        for step in agent_result.reasoning_steps:
            transcript["reasoning_steps"].append({
                "step_number": step.step_number,
                "thought": step.thought,
                "action": step.action,
                "action_input": step.action_input,
                "observation": step.observation,
                "timestamp": step.timestamp
            })
        
        # Add execution plan if used
        if agent_result.execution_plan:
            plan = agent_result.execution_plan
            transcript["execution_plan"] = {
                "plan_id": plan.plan_id,
                "goal": plan.goal,
                "goal_type": plan.goal_type,
                "complexity_score": plan.complexity_score,
                "total_steps": plan.total_steps,
                "estimated_duration": plan.estimated_duration,
                "steps": [
                    {
                        "step_id": step.step_id,
                        "title": step.title,
                        "description": step.description,
                        "step_type": step.step_type.value,
                        "required_tools": step.required_tools,
                        "expected_output": step.expected_output,
                        "dependencies": step.dependencies,
                        "status": step.status.value,
                        "actual_output": step.actual_output,
                        "execution_time": step.execution_time,
                        "error_message": step.error_message
                    }
                    for step in plan.steps
                ],
                "success_criteria": plan.success_criteria,
                "fallback_strategies": plan.fallback_strategies
            }
        
        return transcript

    async def _generate_reflection(self, original_query: str, agent_result,
                                 transcript: Dict[str, Any]) -> str:
        """Generate self-reflection analysis using LLM."""
        try:
            # Format transcript for prompt
            transcript_text = json.dumps(transcript, indent=2)

            # Create reflection prompt
            prompt = self.reflection_prompt.format(
                original_query=original_query,
                success=agent_result.success,
                total_steps=agent_result.total_steps,
                execution_time=transcript["execution_summary"]["execution_time"],
                plan_used=agent_result.plan_used,
                transcript=transcript_text
            )

            # Generate reflection
            response = await self.llm_manager.generate_response(
                prompt=prompt,
                max_tokens=2000,
                temperature=0.1  # Low temperature for consistent analysis
            )

            return response

        except Exception as e:
            logger.error(f"Error generating reflection: {e}")
            return f"Error generating reflection: {str(e)}"

    def _parse_reflection(self, reflection_text: str) -> Tuple[PerformanceMetrics, List[LearningInsight], List[str]]:
        """Parse reflection analysis and extract structured data."""
        try:
            # Extract JSON from reflection
            import re
            json_match = re.search(r'\{.*\}', reflection_text, re.DOTALL)
            if json_match:
                reflection_data = json.loads(json_match.group())
            else:
                # Fallback if no JSON found
                return self._create_default_metrics(), [], []

            # Extract performance metrics
            perf_data = reflection_data.get("performance_assessment", {})
            performance_metrics = PerformanceMetrics(
                success_rate=1.0 if perf_data.get("overall_rating") in ["excellent", "good"] else 0.5,
                efficiency_score=perf_data.get("efficiency_score", 0.5),
                tool_usage_effectiveness=perf_data.get("tool_effectiveness", 0.5),
                planning_accuracy=perf_data.get("planning_quality", 0.5),
                execution_time_ratio=0.8,  # Default value
                error_recovery_rate=0.7,   # Default value
                overall_score=(
                    perf_data.get("efficiency_score", 0.5) +
                    perf_data.get("tool_effectiveness", 0.5) +
                    perf_data.get("planning_quality", 0.5)
                ) / 3
            )

            # Extract learning insights
            insights = []
            for insight_data in reflection_data.get("learning_insights", []):
                insight = LearningInsight(
                    insight_id=str(uuid.uuid4()),
                    learning_type=LearningType(insight_data.get("type", "strategy_improvement")),
                    title=insight_data.get("title", "Untitled Insight"),
                    description=insight_data.get("description", ""),
                    context=original_query if 'original_query' in locals() else "",
                    improvement_suggestion=insight_data.get("improvement_suggestion", ""),
                    confidence_score=insight_data.get("confidence", 0.5),
                    applicable_scenarios=insight_data.get("applicable_scenarios", []),
                    performance_impact=insight_data.get("impact", "Unknown impact"),
                    created_at=datetime.utcnow().isoformat()
                )
                insights.append(insight)

            # Extract strategy updates
            strategy_updates = reflection_data.get("strategy_recommendations", [])

            return performance_metrics, insights, strategy_updates

        except Exception as e:
            logger.error(f"Error parsing reflection: {e}")
            return self._create_default_metrics(), [], []

    def _create_default_metrics(self) -> PerformanceMetrics:
        """Create default performance metrics when parsing fails."""
        return PerformanceMetrics(
            success_rate=0.5,
            efficiency_score=0.5,
            tool_usage_effectiveness=0.5,
            planning_accuracy=0.5,
            execution_time_ratio=0.8,
            error_recovery_rate=0.7,
            overall_score=0.5
        )

    def _categorize_performance(self, metrics: PerformanceMetrics, success: bool) -> PerformanceCategory:
        """Categorize overall performance based on metrics."""
        if not success:
            return PerformanceCategory.FAILED

        overall_score = metrics.overall_score

        if overall_score >= 0.9:
            return PerformanceCategory.EXCELLENT
        elif overall_score >= 0.7:
            return PerformanceCategory.GOOD
        elif overall_score >= 0.5:
            return PerformanceCategory.AVERAGE
        else:
            return PerformanceCategory.POOR

    async def store_learning(self, learning: AgentLearning) -> bool:
        """Store learning record in Weaviate."""
        if not self.weaviate_client:
            logger.warning("No Weaviate client available for storing learning")
            return False

        try:
            # Prepare data for Weaviate
            learning_data = {
                "learningId": learning.learning_id,
                "taskId": learning.task_id,
                "agentType": learning.agent_type,
                "originalQuery": learning.original_query,
                "performanceCategory": learning.performance_category.value,
                "performanceMetrics": asdict(learning.performance_metrics),
                "taskTranscript": learning.task_transcript,
                "reflectionAnalysis": learning.reflection_analysis,
                "learningInsights": [asdict(insight) for insight in learning.learning_insights],
                "strategyUpdates": learning.strategy_updates,
                "createdAt": learning.created_at,
                "metadata": learning.metadata
            }

            # Store in Weaviate
            collection = self.weaviate_client.collections.get("AgentLearning")
            result = collection.data.insert(learning_data)

            logger.info(f"Learning record stored with ID: {result}")
            return True

        except Exception as e:
            logger.error(f"Error storing learning record: {e}")
            return False

    async def retrieve_similar_learnings(self, query: str, limit: int = 5) -> List[AgentLearning]:
        """Retrieve similar learning records for context."""
        if not self.weaviate_client:
            return []

        try:
            collection = self.weaviate_client.collections.get("AgentLearning")

            # Search for similar learnings
            response = collection.query.near_text(
                query=query,
                limit=limit,
                return_metadata=["score"]
            )

            learnings = []
            for obj in response.objects:
                # Convert Weaviate object back to AgentLearning
                props = obj.properties

                # Reconstruct learning insights
                insights = []
                for insight_data in props.get("learningInsights", []):
                    insight = LearningInsight(
                        insight_id=insight_data.get("insight_id", ""),
                        learning_type=LearningType(insight_data.get("learning_type", "strategy_improvement")),
                        title=insight_data.get("title", ""),
                        description=insight_data.get("description", ""),
                        context=insight_data.get("context", ""),
                        improvement_suggestion=insight_data.get("improvement_suggestion", ""),
                        confidence_score=insight_data.get("confidence_score", 0.5),
                        applicable_scenarios=insight_data.get("applicable_scenarios", []),
                        performance_impact=insight_data.get("performance_impact", ""),
                        created_at=insight_data.get("created_at", "")
                    )
                    insights.append(insight)

                # Reconstruct performance metrics
                metrics_data = props.get("performanceMetrics", {})
                performance_metrics = PerformanceMetrics(
                    success_rate=metrics_data.get("success_rate", 0.5),
                    efficiency_score=metrics_data.get("efficiency_score", 0.5),
                    tool_usage_effectiveness=metrics_data.get("tool_usage_effectiveness", 0.5),
                    planning_accuracy=metrics_data.get("planning_accuracy", 0.5),
                    execution_time_ratio=metrics_data.get("execution_time_ratio", 0.8),
                    error_recovery_rate=metrics_data.get("error_recovery_rate", 0.7),
                    overall_score=metrics_data.get("overall_score", 0.5)
                )

                learning = AgentLearning(
                    learning_id=props.get("learningId", ""),
                    task_id=props.get("taskId", ""),
                    agent_type=props.get("agentType", ""),
                    original_query=props.get("originalQuery", ""),
                    performance_category=PerformanceCategory(props.get("performanceCategory", "average")),
                    performance_metrics=performance_metrics,
                    task_transcript=props.get("taskTranscript", {}),
                    reflection_analysis=props.get("reflectionAnalysis", ""),
                    learning_insights=insights,
                    strategy_updates=props.get("strategyUpdates", []),
                    created_at=props.get("createdAt", ""),
                    metadata=props.get("metadata", {})
                )

                learnings.append(learning)

            return learnings

        except Exception as e:
            logger.error(f"Error retrieving similar learnings: {e}")
            return []

    def get_learning_summary(self, learnings: List[AgentLearning]) -> Dict[str, Any]:
        """Generate a summary of learning insights."""
        if not learnings:
            return {"total_learnings": 0, "insights": [], "recommendations": []}

        # Aggregate insights by type
        insight_types = {}
        all_recommendations = []

        for learning in learnings:
            for insight in learning.learning_insights:
                insight_type = insight.learning_type.value
                if insight_type not in insight_types:
                    insight_types[insight_type] = []
                insight_types[insight_type].append(insight)

            all_recommendations.extend(learning.strategy_updates)

        # Calculate performance trends
        performance_scores = [l.performance_metrics.overall_score for l in learnings]
        avg_performance = sum(performance_scores) / len(performance_scores) if performance_scores else 0

        return {
            "total_learnings": len(learnings),
            "average_performance": avg_performance,
            "insight_types": {k: len(v) for k, v in insight_types.items()},
            "top_insights": [
                {
                    "title": insight.title,
                    "type": insight.learning_type.value,
                    "confidence": insight.confidence_score,
                    "suggestion": insight.improvement_suggestion
                }
                for learning in learnings[-3:]  # Last 3 learnings
                for insight in learning.learning_insights[:2]  # Top 2 insights each
            ],
            "strategy_recommendations": list(set(all_recommendations))  # Unique recommendations
        }


# Global learning service instance
_learning_service = None

def get_learning_service(weaviate_client: Optional[weaviate.WeaviateClient] = None) -> AgentLearningService:
    """Get the global AgentLearningService instance."""
    global _learning_service
    if _learning_service is None:
        _learning_service = AgentLearningService(weaviate_client)
    return _learning_service
