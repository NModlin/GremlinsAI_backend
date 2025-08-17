# tests/integration/test_analytics_service.py
"""
Integration tests for advanced analytics service.

These tests verify that the AnalyticsService can:
- Process agent interaction data with <5 minute latency
- Generate tool usage analytics and insights
- Analyze query trends and user behavior patterns
- Calculate performance metrics and benchmarks
- Store aggregated metrics in Weaviate
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any, List

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.analytics_service import (
    AnalyticsService, AnalyticsMetric, MetricType, TimeWindow,
    ToolUsageMetric, QueryTrendMetric, PerformanceMetric
)


class TestAnalyticsService:
    """Test suite for advanced analytics service capabilities."""
    
    @pytest.fixture
    def mock_weaviate_client(self):
        """Create a mock Weaviate client for testing."""
        mock_client = MagicMock()
        
        # Mock collections
        mock_collections = MagicMock()
        mock_client.collections = mock_collections
        
        # Mock collection operations
        mock_collection = MagicMock()
        mock_collections.get.return_value = mock_collection
        
        # Mock data insertion
        mock_collection.data.insert.return_value = "test_metric_id_123"
        
        # Mock query operations
        mock_query_response = MagicMock()
        mock_query_response.objects = []
        mock_collection.query.fetch_objects.return_value = mock_query_response
        
        return mock_client
    
    @pytest.fixture
    def sample_agent_interactions(self):
        """Create sample agent interaction data for testing."""
        interactions = []
        
        # Generate diverse interaction data
        tools = ["web_search", "text_processor", "calculator", "file_reader", "code_executor"]
        agent_types = ["production_agent", "researcher", "analyst", "writer"]
        
        for i in range(20):
            interaction = {
                "interaction_id": f"interaction_{i}",
                "agent_type": agent_types[i % len(agent_types)],
                "query": f"Sample query {i} about business analysis and market research",
                "response": f"Detailed response {i} with comprehensive analysis",
                "tools_used": [tools[j % len(tools)] for j in range((i % 3) + 1)],
                "execution_time_ms": 1500 + (i * 200) % 4000,
                "tokens_used": 800 + (i * 100) % 1500,
                "conversation_id": f"conv_{i % 5}",
                "created_at": (datetime.utcnow() - timedelta(minutes=i * 5)).isoformat(),
                "metadata": {
                    "success": i % 8 != 0,  # 87.5% success rate
                    "reasoning_steps": (i % 4) + 1
                }
            }
            interactions.append(interaction)
        
        return interactions
    
    @pytest.fixture
    def analytics_service(self, mock_weaviate_client):
        """Create analytics service with mocked Weaviate client."""
        return AnalyticsService(weaviate_client=mock_weaviate_client)
    
    @pytest.mark.asyncio
    async def test_process_interaction_data_complete_pipeline(self, analytics_service, sample_agent_interactions):
        """Test complete analytics processing pipeline."""
        
        # Mock the interaction query to return sample data
        analytics_service._query_recent_interactions = AsyncMock(return_value=sample_agent_interactions)
        
        # Process interaction data
        result = await analytics_service.process_interaction_data(TimeWindow.LAST_HOUR)
        
        # Verify processing results
        assert result["processed"] == 20
        assert result["metrics_generated"] > 0
        assert result["processing_time_seconds"] < 300  # Should be under 5 minutes
        assert result["tool_metrics"] > 0
        assert result["query_metrics"] > 0
        assert result["performance_metrics"] > 0
        
        # Verify processing metrics were updated
        processing_metrics = analytics_service.processing_metrics
        assert processing_metrics["total_processed"] >= 20
        assert processing_metrics["processing_time_avg"] > 0
        assert processing_metrics["last_processing_time"] is not None
    
    @pytest.mark.asyncio
    async def test_tool_usage_metrics_generation(self, analytics_service, sample_agent_interactions):
        """Test tool usage analytics generation."""
        
        # Generate tool usage metrics
        tool_metrics = await analytics_service._generate_tool_usage_metrics(
            sample_agent_interactions, TimeWindow.LAST_DAY
        )
        
        # Verify metrics structure
        assert len(tool_metrics) > 0
        
        for metric in tool_metrics:
            assert isinstance(metric, AnalyticsMetric)
            assert metric.metric_type == MetricType.TOOL_USAGE
            assert metric.time_window == TimeWindow.LAST_DAY
            assert metric.value > 0  # Usage count
            
            # Verify metadata contains expected fields
            metadata = metric.metadata
            assert "tool_name" in metadata
            assert "success_rate" in metadata
            assert "avg_execution_time" in metadata
            assert "unique_users" in metadata
            assert 0.0 <= metadata["success_rate"] <= 1.0
            assert metadata["avg_execution_time"] >= 0.0
        
        # Verify tools are represented
        tool_names = [metric.metadata["tool_name"] for metric in tool_metrics]
        assert "web_search" in tool_names
        assert "text_processor" in tool_names
        assert "calculator" in tool_names
    
    @pytest.mark.asyncio
    async def test_query_trend_metrics_generation(self, analytics_service, sample_agent_interactions):
        """Test query trend analytics generation."""
        
        # Generate query trend metrics
        query_metrics = await analytics_service._generate_query_trend_metrics(
            sample_agent_interactions, TimeWindow.LAST_DAY
        )
        
        # Verify metrics structure
        assert len(query_metrics) > 0
        
        keyword_metrics = [m for m in query_metrics if "keyword" in m.metadata]
        category_metrics = [m for m in query_metrics if "category" in m.metadata]
        
        # Verify keyword metrics
        for metric in keyword_metrics:
            assert isinstance(metric, AnalyticsMetric)
            assert metric.metric_type == MetricType.QUERY_TRENDS
            assert metric.time_window == TimeWindow.LAST_DAY
            assert metric.value > 0  # Frequency
            
            metadata = metric.metadata
            assert "keyword" in metadata
            assert "trend_score" in metadata
            assert 0.0 <= metadata["trend_score"] <= 1.0
        
        # Verify category metrics
        for metric in category_metrics:
            assert "category" in metric.metadata
            assert "percentage" in metric.metadata
            assert 0.0 <= metric.metadata["percentage"] <= 1.0
        
        # Verify business keywords are captured
        keywords = [m.metadata["keyword"] for m in keyword_metrics if "keyword" in m.metadata]
        assert any(keyword in ["analysis", "business", "research", "market"] for keyword in keywords)
    
    @pytest.mark.asyncio
    async def test_performance_metrics_generation(self, analytics_service, sample_agent_interactions):
        """Test performance analytics generation."""
        
        # Generate performance metrics
        performance_metrics = await analytics_service._generate_performance_metrics(
            sample_agent_interactions, TimeWindow.LAST_DAY
        )
        
        # Verify metrics structure
        assert len(performance_metrics) > 0
        
        for metric in performance_metrics:
            assert isinstance(metric, AnalyticsMetric)
            assert metric.metric_type == MetricType.PERFORMANCE
            assert metric.time_window == TimeWindow.LAST_DAY
            assert metric.value >= 0.0  # Average response time
            
            # Verify metadata contains expected fields
            metadata = metric.metadata
            assert "agent_type" in metadata
            assert "avg_response_time" in metadata
            assert "success_rate" in metadata
            assert "total_interactions" in metadata
            assert "avg_reasoning_steps" in metadata
            assert "avg_token_usage" in metadata
            
            # Verify value ranges
            assert 0.0 <= metadata["success_rate"] <= 1.0
            assert metadata["avg_response_time"] >= 0.0
            assert metadata["total_interactions"] > 0
            assert metadata["avg_reasoning_steps"] >= 1.0
            assert metadata["avg_token_usage"] >= 0.0
        
        # Verify agent types are represented
        agent_types = [metric.metadata["agent_type"] for metric in performance_metrics]
        assert "production_agent" in agent_types
        assert "researcher" in agent_types
        assert "analyst" in agent_types
    
    @pytest.mark.asyncio
    async def test_analytics_metrics_storage(self, analytics_service, mock_weaviate_client):
        """Test analytics metrics storage in Weaviate."""
        
        # Create sample metrics
        sample_metrics = [
            AnalyticsMetric(
                metric_id="test_metric_1",
                metric_type=MetricType.TOOL_USAGE,
                time_window=TimeWindow.LAST_HOUR,
                timestamp=datetime.utcnow(),
                value=50.0,
                metadata={"tool_name": "web_search", "success_rate": 0.95},
                dimensions={"tool_name": "web_search", "time_window": "1h"}
            ),
            AnalyticsMetric(
                metric_id="test_metric_2",
                metric_type=MetricType.PERFORMANCE,
                time_window=TimeWindow.LAST_HOUR,
                timestamp=datetime.utcnow(),
                value=2.5,
                metadata={"agent_type": "production_agent", "success_rate": 0.92},
                dimensions={"agent_type": "production_agent", "time_window": "1h"}
            )
        ]
        
        # Store metrics
        stored_ids = await analytics_service._store_analytics_metrics(sample_metrics)
        
        # Verify storage was called
        mock_collection = mock_weaviate_client.collections.get.return_value
        assert mock_collection.data.insert.call_count == 2
        assert len(stored_ids) == 2
        
        # Verify data structure passed to Weaviate
        insert_calls = mock_collection.data.insert.call_args_list
        
        for i, call in enumerate(insert_calls):
            call_data = call[0][0]
            original_metric = sample_metrics[i]
            
            assert call_data["metricId"] == original_metric.metric_id
            assert call_data["metricType"] == original_metric.metric_type.value
            assert call_data["timeWindow"] == original_metric.time_window.value
            assert call_data["value"] == original_metric.value
            
            # Verify JSON serialization
            metadata = json.loads(call_data["metadata"])
            dimensions = json.loads(call_data["dimensions"])
            assert metadata == original_metric.metadata
            assert dimensions == original_metric.dimensions
    
    @pytest.mark.asyncio
    async def test_analytics_api_methods(self, analytics_service):
        """Test analytics API methods for dashboard."""
        
        # Test tool usage metrics API
        tool_metrics = await analytics_service.get_tool_usage_metrics(TimeWindow.LAST_DAY)
        assert isinstance(tool_metrics, list)
        assert len(tool_metrics) > 0
        
        for metric in tool_metrics:
            assert "tool_name" in metric
            assert "usage_count" in metric
            assert "success_rate" in metric
            assert "avg_execution_time" in metric
            assert "unique_users" in metric
        
        # Test query trend metrics API
        query_metrics = await analytics_service.get_query_trend_metrics(TimeWindow.LAST_DAY)
        assert isinstance(query_metrics, list)
        assert len(query_metrics) > 0
        
        for metric in query_metrics:
            assert "frequency" in metric
            # Should have either keyword or category
            assert "keyword" in metric or "category" in metric
        
        # Test performance metrics API
        performance_metrics = await analytics_service.get_performance_metrics(TimeWindow.LAST_DAY)
        assert isinstance(performance_metrics, list)
        assert len(performance_metrics) > 0
        
        for metric in performance_metrics:
            assert "agent_type" in metric
            assert "avg_response_time" in metric
            assert "success_rate" in metric
            assert "total_interactions" in metric
    
    @pytest.mark.asyncio
    async def test_processing_latency_requirement(self, analytics_service, sample_agent_interactions):
        """Test that processing meets <5 minute latency requirement."""
        
        # Mock the interaction query
        analytics_service._query_recent_interactions = AsyncMock(return_value=sample_agent_interactions)
        
        # Measure processing time
        start_time = asyncio.get_event_loop().time()
        result = await analytics_service.process_interaction_data(TimeWindow.LAST_HOUR)
        end_time = asyncio.get_event_loop().time()
        
        processing_time = end_time - start_time
        
        # Verify latency requirement
        assert processing_time < 300, f"Processing took {processing_time:.2f}s, exceeding 5-minute requirement"
        assert result["processing_time_seconds"] < 300
        
        # Verify processing was successful
        assert result["processed"] > 0
        assert result["metrics_generated"] > 0
    
    def test_processing_status_and_metrics(self, analytics_service):
        """Test processing status and metrics tracking."""
        
        # Get initial status
        status = analytics_service.get_processing_status()
        
        # Verify status structure
        assert "status" in status
        assert "processing_metrics" in status
        assert "cache_status" in status
        assert "latency_target" in status
        assert "last_processed" in status
        
        # Verify processing metrics
        processing_metrics = status["processing_metrics"]
        assert "total_processed" in processing_metrics
        assert "processing_time_avg" in processing_metrics
        assert "errors" in processing_metrics
        
        # Verify latency target
        assert status["latency_target"] == "< 5 minutes"
    
    @pytest.mark.asyncio
    async def test_time_window_filtering(self, analytics_service):
        """Test time window filtering for different analytics periods."""
        
        # Test different time windows
        time_windows = [TimeWindow.LAST_HOUR, TimeWindow.LAST_DAY, TimeWindow.LAST_WEEK, TimeWindow.LAST_MONTH]
        
        for time_window in time_windows:
            # Test time threshold calculation
            threshold = analytics_service._get_time_threshold(time_window)
            now = datetime.utcnow()
            
            # Verify threshold is in the past
            assert threshold < now
            
            # Verify appropriate time difference
            time_diff = now - threshold
            if time_window == TimeWindow.LAST_HOUR:
                assert timedelta(minutes=55) <= time_diff <= timedelta(minutes=65)
            elif time_window == TimeWindow.LAST_DAY:
                assert timedelta(hours=23) <= time_diff <= timedelta(hours=25)
            elif time_window == TimeWindow.LAST_WEEK:
                assert timedelta(days=6) <= time_diff <= timedelta(days=8)
            elif time_window == TimeWindow.LAST_MONTH:
                assert timedelta(days=29) <= time_diff <= timedelta(days=31)


if __name__ == "__main__":
    pytest.main([__file__])
