# tests/integration/test_multimodal_fusion.py
"""
Integration tests for multimodal fusion and reasoning capabilities.

These tests verify that the MultimodalFusionService can:
- Generate frame descriptions using VLM
- Combine multimodal data chronologically
- Reason over fused content using ProductionAgent
- Provide comprehensive multimodal understanding
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any, List

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.multimodal_fusion_service import (
    MultimodalFusionService, VisionLanguageModel, FusionStrategy,
    FrameDescription, TemporalSegment, ModalityType, FusedContent,
    MultimodalReasoningResult
)
from app.core.agent import AgentResult, ReasoningStep


class TestMultimodalFusion:
    """Test suite for multimodal fusion and reasoning capabilities."""
    
    @pytest.fixture
    def sample_multimodal_content(self):
        """Create sample multimodal content for testing."""
        return {
            "frames": [
                {
                    "timestamp": 0.0,
                    "data": "base64_frame_data_1",
                    "frame_index": 0
                },
                {
                    "timestamp": 5.0,
                    "data": "base64_frame_data_2",
                    "frame_index": 150
                },
                {
                    "timestamp": 10.0,
                    "data": "base64_frame_data_3",
                    "frame_index": 300
                }
            ],
            "audio_transcription": {
                "segments": [
                    {
                        "start": 0.0,
                        "end": 4.0,
                        "text": "Welcome everyone to today's quarterly business review meeting.",
                        "speaker": "CEO",
                        "confidence": 0.95
                    },
                    {
                        "start": 4.0,
                        "end": 8.0,
                        "text": "As you can see from the charts on screen, our revenue has grown by 25% this quarter.",
                        "speaker": "CEO",
                        "confidence": 0.92
                    },
                    {
                        "start": 8.0,
                        "end": 12.0,
                        "text": "The marketing team has done an excellent job driving customer acquisition.",
                        "speaker": "CEO",
                        "confidence": 0.88
                    }
                ],
                "duration": 12.0,
                "language": "en"
            },
            "metadata": {
                "duration": 12.0,
                "fps": 30,
                "resolution": [1920, 1080]
            }
        }
    
    @pytest.fixture
    def mock_agent_result(self):
        """Create a mock agent result for testing."""
        reasoning_steps = [
            ReasoningStep(
                step_number=1,
                thought="I need to analyze the multimodal content to understand the business meeting",
                action="analyze_content",
                action_input="Examining video frames and audio transcript",
                observation="The content shows a CEO presenting quarterly results at [0.0s] with charts visible at [5.0s] and discussing marketing success at [10.0s]"
            ),
            ReasoningStep(
                step_number=2,
                thought="I can now provide a comprehensive answer based on both visual and audio information",
                action="final_answer",
                action_input="Based on the multimodal analysis...",
                observation="Final answer provided"
            )
        ]
        
        return AgentResult(
            final_answer="Based on the multimodal analysis of the business meeting, the CEO presented strong quarterly results showing 25% revenue growth. The presentation included visual charts and graphs displayed on screen, while the CEO spoke about the marketing team's success in customer acquisition. The meeting demonstrates positive business performance with both quantitative data visualization and executive commentary.",
            reasoning_steps=reasoning_steps,
            total_steps=2,
            success=True
        )
    
    @pytest.mark.asyncio
    async def test_vlm_frame_description_generation(self):
        """Test VLM frame description generation."""
        vlm = VisionLanguageModel(model_type="mock")
        
        # Test frame description generation
        frame_desc = await vlm.describe_frame("mock_frame_data", timestamp=5.0)
        
        # Verify frame description structure
        assert isinstance(frame_desc, FrameDescription)
        assert frame_desc.timestamp == 5.0
        assert frame_desc.frame_index == 150  # 5.0 * 30 FPS
        assert len(frame_desc.description) > 0
        assert frame_desc.confidence > 0
        assert isinstance(frame_desc.objects_detected, list)
        assert isinstance(frame_desc.visual_elements, list)
        assert len(frame_desc.scene_context) > 0
    
    @pytest.mark.asyncio
    async def test_multimodal_fusion_and_reasoning(self, sample_multimodal_content, mock_agent_result):
        """Test complete multimodal fusion and reasoning pipeline."""
        
        with patch('app.services.multimodal_fusion_service.ProductionAgent') as mock_agent_class:
            # Setup mock agent
            mock_agent = AsyncMock()
            mock_agent_class.return_value = mock_agent
            mock_agent.reason_and_act.return_value = mock_agent_result
            
            # Create fusion service
            fusion_service = MultimodalFusionService()
            
            # Test query
            user_query = "What was discussed in this business meeting and what visual information was presented?"
            
            # Perform fusion and reasoning
            result = await fusion_service.fuse_and_reason(
                user_query=user_query,
                multimodal_content=sample_multimodal_content,
                fusion_strategy=FusionStrategy.CHRONOLOGICAL
            )
            
            # Verify result structure
            assert isinstance(result, MultimodalReasoningResult)
            assert result.query == user_query
            assert len(result.answer) > 0
            assert result.confidence_score > 0
            assert len(result.modalities_used) > 0
            assert ModalityType.AUDIO in result.modalities_used
            assert ModalityType.VIDEO in result.modalities_used
            
            # Verify reasoning steps
            assert len(result.reasoning_steps) > 0
            assert isinstance(result.reasoning_steps, list)
            
            # Verify evidence sources
            assert len(result.evidence_sources) > 0
            for evidence in result.evidence_sources:
                assert "step" in evidence
                assert "action" in evidence
                assert "evidence" in evidence
            
            # Verify temporal references
            assert len(result.temporal_references) > 0
            for ref in result.temporal_references:
                assert "timestamp" in ref
                assert "context" in ref
                assert "reasoning_step" in ref
            
            # Verify agent was called with enhanced query
            mock_agent.reason_and_act.assert_called_once()
            call_args = mock_agent.reason_and_act.call_args[0][0]
            assert user_query in call_args
            assert "MULTIMODAL CONTEXT" in call_args
            assert "CEO" in call_args  # Speaker information
            assert "[0.0s]" in call_args  # Timestamp information
            assert "[AUDIO]" in call_args  # Modality indicators
            assert "[VIDEO]" in call_args  # Modality indicators
    
    @pytest.mark.asyncio
    async def test_frame_description_generation(self, sample_multimodal_content):
        """Test frame description generation from video frames."""
        
        fusion_service = MultimodalFusionService()
        
        # Generate frame descriptions
        frame_descriptions = await fusion_service._generate_frame_descriptions(sample_multimodal_content)
        
        # Verify frame descriptions
        assert len(frame_descriptions) == 3  # Three frames in sample data
        
        for i, desc in enumerate(frame_descriptions):
            assert isinstance(desc, FrameDescription)
            assert desc.timestamp == i * 5.0  # 0.0, 5.0, 10.0
            assert len(desc.description) > 0
            assert desc.confidence > 0
            assert isinstance(desc.objects_detected, list)
            assert isinstance(desc.visual_elements, list)
    
    @pytest.mark.asyncio
    async def test_audio_segment_extraction(self, sample_multimodal_content):
        """Test audio transcript segment extraction."""
        
        fusion_service = MultimodalFusionService()
        
        # Extract audio segments
        audio_segments = fusion_service._extract_audio_segments(sample_multimodal_content)
        
        # Verify audio segments
        assert len(audio_segments) == 3  # Three segments in sample data
        
        for i, segment in enumerate(audio_segments):
            assert isinstance(segment, TemporalSegment)
            assert segment.modality_type == ModalityType.AUDIO
            assert segment.start_time == i * 4.0  # 0.0, 4.0, 8.0
            assert segment.end_time == (i + 1) * 4.0  # 4.0, 8.0, 12.0
            assert len(segment.content) > 0
            assert segment.confidence > 0
            assert segment.metadata["speaker"] == "CEO"
    
    @pytest.mark.asyncio
    async def test_chronological_fusion(self, sample_multimodal_content):
        """Test chronological fusion of multimodal data."""
        
        fusion_service = MultimodalFusionService()
        
        # Generate frame descriptions and extract audio segments
        frame_descriptions = await fusion_service._generate_frame_descriptions(sample_multimodal_content)
        audio_segments = fusion_service._extract_audio_segments(sample_multimodal_content)
        
        # Perform fusion
        fused_content = await fusion_service._fuse_multimodal_data(
            frame_descriptions, audio_segments, FusionStrategy.CHRONOLOGICAL
        )
        
        # Verify fused content structure
        assert isinstance(fused_content, FusedContent)
        assert fused_content.fusion_strategy == FusionStrategy.CHRONOLOGICAL
        assert fused_content.total_duration == 12.0
        assert ModalityType.AUDIO in fused_content.modalities_included
        assert ModalityType.VIDEO in fused_content.modalities_included
        
        # Verify fused text contains both modalities
        assert "[AUDIO]" in fused_content.fused_text
        assert "[VIDEO]" in fused_content.fused_text
        assert "CEO" in fused_content.fused_text  # Speaker information
        assert "quarterly" in fused_content.fused_text  # Audio content
        assert "conference" in fused_content.fused_text  # Video content (from mock descriptions)
        
        # Verify temporal segments are sorted chronologically
        timestamps = [seg.start_time for seg in fused_content.temporal_segments]
        assert timestamps == sorted(timestamps)
        
        # Verify metadata
        assert fused_content.fusion_metadata["total_segments"] == 6  # 3 audio + 3 video
        assert fused_content.fusion_metadata["audio_segments"] == 3
        assert fused_content.fusion_metadata["video_frames"] == 3
    
    @pytest.mark.asyncio
    async def test_fusion_with_missing_modalities(self):
        """Test fusion behavior with missing modalities."""
        
        fusion_service = MultimodalFusionService()
        
        # Test with only audio data
        audio_only_content = {
            "audio_transcription": {
                "text": "This is a simple audio transcription without video.",
                "duration": 10.0,
                "confidence": 0.9
            }
        }
        
        user_query = "What was said in this audio?"
        
        with patch('app.services.multimodal_fusion_service.ProductionAgent') as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent_class.return_value = mock_agent
            
            # Mock agent response
            mock_agent_result = AgentResult(
                final_answer="The audio contains a simple transcription message.",
                reasoning_steps=[],
                total_steps=1,
                success=True
            )
            mock_agent.reason_and_act.return_value = mock_agent_result
            
            # Perform fusion and reasoning
            result = await fusion_service.fuse_and_reason(
                user_query=user_query,
                multimodal_content=audio_only_content
            )
            
            # Verify result
            assert isinstance(result, MultimodalReasoningResult)
            assert result.confidence_score > 0
            assert ModalityType.AUDIO in result.modalities_used
            assert ModalityType.VIDEO not in result.modalities_used
    
    @pytest.mark.asyncio
    async def test_fusion_error_handling(self):
        """Test error handling in fusion process."""
        
        fusion_service = MultimodalFusionService()
        
        # Test with invalid/empty content
        invalid_content = {}
        user_query = "What is in this content?"
        
        with patch('app.services.multimodal_fusion_service.ProductionAgent') as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent_class.return_value = mock_agent
            
            # Mock agent to raise an exception
            mock_agent.reason_and_act.side_effect = Exception("Agent processing failed")
            
            # Perform fusion and reasoning
            result = await fusion_service.fuse_and_reason(
                user_query=user_query,
                multimodal_content=invalid_content
            )
            
            # Verify error handling
            assert isinstance(result, MultimodalReasoningResult)
            assert result.confidence_score <= 0.5  # Low confidence due to errors
            assert len(result.modalities_used) == 0
    
    def test_fusion_capabilities(self):
        """Test fusion capabilities reporting."""
        
        fusion_service = MultimodalFusionService()
        
        capabilities = fusion_service.get_fusion_capabilities()
        
        # Verify capabilities structure
        assert "supported_modalities" in capabilities
        assert "fusion_strategies" in capabilities
        assert "vlm_model" in capabilities
        assert "features" in capabilities
        
        # Verify supported modalities
        assert "audio" in capabilities["supported_modalities"]
        assert "video" in capabilities["supported_modalities"]
        assert "image" in capabilities["supported_modalities"]
        
        # Verify fusion strategies
        assert "chronological" in capabilities["fusion_strategies"]
        
        # Verify features
        features = capabilities["features"]
        assert "frame_description_generation" in features
        assert "chronological_fusion" in features
        assert "cross_modal_reasoning" in features


if __name__ == "__main__":
    pytest.main([__file__])
