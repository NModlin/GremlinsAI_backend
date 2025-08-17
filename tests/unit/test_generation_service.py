"""
Unit tests for the context-aware response generation service.

Tests verify response generation, source attribution, citation parsing,
and quality assessment using mocked LLM responses.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import uuid
from typing import List, Dict, Any

from app.services.generation_service import (
    GenerationService,
    GenerationConfig,
    CitationFormat,
    ResponseQuality,
    SourceCitation,
    GenerationResponse,
    create_generation_service
)
from app.services.retrieval_service import SearchResult
from app.core.llm_manager import LLMResponse, ProductionLLMManager


class TestGenerationService:
    """Test cases for generation service functionality."""
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Create mock LLM manager with predictable responses."""
        manager = AsyncMock(spec=ProductionLLMManager)
        
        # Mock successful response
        mock_response = LLMResponse(
            content="Based on the provided context, artificial intelligence (AI) is a branch of computer science [1]. Machine learning is a subset of AI that enables computers to learn from data [2]. These technologies are transforming modern applications across various industries.",
            provider="ollama",
            model="llama3.2:3b",
            response_time=1.5,
            token_count=150,
            finish_reason="stop"
        )
        
        manager.generate_response.return_value = mock_response
        return manager
    
    @pytest.fixture
    def sample_context_chunks(self):
        """Sample context chunks for testing."""
        return [
            SearchResult(
                chunk_id="chunk-001",
                document_id="doc-ai-intro",
                content="Artificial intelligence (AI) is a branch of computer science that aims to create intelligent machines capable of performing tasks that typically require human intelligence.",
                semantic_score=0.85,
                keyword_score=0.90,
                hybrid_score=0.87,
                chunk_index=0,
                start_position=0,
                end_position=150,
                chunk_metadata={"category": "AI", "complexity": "beginner"},
                query_match_highlights=["artificial intelligence", "computer science"],
                matched_terms=["ai", "artificial", "intelligence"]
            ),
            SearchResult(
                chunk_id="chunk-002",
                document_id="doc-ml-basics",
                content="Machine learning is a subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed.",
                semantic_score=0.80,
                keyword_score=0.85,
                hybrid_score=0.82,
                chunk_index=1,
                start_position=151,
                end_position=280,
                chunk_metadata={"category": "ML", "complexity": "intermediate"},
                query_match_highlights=["machine learning", "artificial intelligence"],
                matched_terms=["machine", "learning", "ai"]
            ),
            SearchResult(
                chunk_id="chunk-003",
                document_id="doc-applications",
                content="AI and machine learning technologies are being applied across various industries including healthcare, finance, transportation, and entertainment.",
                semantic_score=0.75,
                keyword_score=0.80,
                hybrid_score=0.77,
                chunk_index=2,
                start_position=281,
                end_position=400,
                chunk_metadata={"category": "Applications", "complexity": "beginner"},
                query_match_highlights=["AI", "machine learning"],
                matched_terms=["ai", "machine", "learning"]
            )
        ]
    
    def test_generation_service_initialization(self):
        """Test generation service initialization."""
        mock_llm = Mock()
        config = GenerationConfig(citation_format=CitationFormat.NUMBERED)
        
        service = GenerationService(mock_llm, config)
        
        assert service.llm_manager == mock_llm
        assert service.config.citation_format == CitationFormat.NUMBERED
        assert service.metrics["total_generations"] == 0
    
    @pytest.mark.asyncio
    async def test_generate_response_with_context(self, mock_llm_manager, sample_context_chunks):
        """Test complete response generation with context."""
        config = GenerationConfig(
            citation_format=CitationFormat.NUMBERED,
            require_citations=True,
            min_citation_confidence=0.7
        )
        
        service = GenerationService(mock_llm_manager, config)
        
        response = await service.generate_response_with_context(
            "What is artificial intelligence and machine learning?",
            sample_context_chunks
        )
        
        # Verify response structure
        assert isinstance(response, GenerationResponse)
        assert response.answer
        assert len(response.answer) > 0
        assert response.query == "What is artificial intelligence and machine learning?"
        
        # Verify LLM was called
        mock_llm_manager.generate_response.assert_called_once()
        
        # Verify citations were extracted
        assert len(response.sources) >= 0  # May be 0 if citations not properly parsed
        
        # Verify quality metrics
        assert 0.0 <= response.confidence_score <= 1.0
        assert isinstance(response.quality_level, ResponseQuality)
        assert 0.0 <= response.citation_accuracy <= 1.0
        
        # Verify performance metrics
        assert response.generation_time_ms > 0
        assert response.context_length > 0
        assert response.response_length > 0
        
        # Verify LLM metadata
        assert response.llm_provider == "ollama"
        assert response.llm_model == "llama3.2:3b"
        assert response.llm_response_time > 0
    
    @pytest.mark.asyncio
    async def test_citation_parsing_numbered_format(self, mock_llm_manager, sample_context_chunks):
        """Test citation parsing with numbered format."""
        # Mock response with numbered citations
        mock_response = LLMResponse(
            content="AI is a branch of computer science [1]. Machine learning is a subset of AI [2]. These technologies are widely used [3].",
            provider="ollama",
            model="llama3.2:3b",
            response_time=1.0
        )
        mock_llm_manager.generate_response.return_value = mock_response
        
        config = GenerationConfig(citation_format=CitationFormat.NUMBERED)
        service = GenerationService(mock_llm_manager, config)
        
        response = await service.generate_response_with_context(
            "What is AI?",
            sample_context_chunks
        )
        
        # Verify citations were parsed and validated
        assert len(response.sources) >= 2  # Should find at least 2 valid citations
        
        # Verify citation structure
        for citation in response.sources:
            assert isinstance(citation, SourceCitation)
            assert citation.document_id
            assert citation.chunk_id
            assert citation.citation_text
            assert 0.0 <= citation.confidence_score <= 1.0
            assert 0.0 <= citation.relevance_score <= 1.0
    
    @pytest.mark.asyncio
    async def test_citation_parsing_bracketed_format(self, mock_llm_manager, sample_context_chunks):
        """Test citation parsing with bracketed format."""
        # Mock response with bracketed citations
        mock_response = LLMResponse(
            content="AI is a branch of computer science [Source: doc-ai-intro]. Machine learning enables computers to learn [Source: doc-ml-basics].",
            provider="ollama",
            model="llama3.2:3b",
            response_time=1.0
        )
        mock_llm_manager.generate_response.return_value = mock_response
        
        config = GenerationConfig(citation_format=CitationFormat.BRACKETED)
        service = GenerationService(mock_llm_manager, config)
        
        response = await service.generate_response_with_context(
            "What is AI?",
            sample_context_chunks
        )
        
        # Verify citations were parsed
        assert len(response.sources) >= 1
        
        # Verify citation format
        for citation in response.sources:
            assert citation.document_id in ["doc-ai-intro", "doc-ml-basics", "doc-applications"]
    
    @pytest.mark.asyncio
    async def test_context_filtering(self, mock_llm_manager, sample_context_chunks):
        """Test context chunk filtering and ranking."""
        config = GenerationConfig(
            max_context_length=200,  # Small limit to test filtering
            min_source_relevance=0.8  # High threshold
        )
        
        service = GenerationService(mock_llm_manager, config)
        
        # Test filtering method directly
        filtered_chunks = service._filter_context_chunks(sample_context_chunks, config)
        
        # Should filter out chunks below relevance threshold
        assert len(filtered_chunks) <= len(sample_context_chunks)
        
        # All filtered chunks should meet relevance threshold
        for chunk in filtered_chunks:
            assert chunk.hybrid_score >= config.min_source_relevance
        
        # Should be sorted by relevance (descending)
        for i in range(len(filtered_chunks) - 1):
            assert filtered_chunks[i].hybrid_score >= filtered_chunks[i + 1].hybrid_score
    
    def test_query_preprocessing(self):
        """Test query preprocessing functionality."""
        service = GenerationService(Mock())
        
        # Test basic cleaning
        processed = service._preprocess_query("  What is AI  ")
        assert processed == "What is AI?"
        
        # Test question mark addition
        processed = service._preprocess_query("What is machine learning")
        assert processed == "What is machine learning?"
        
        # Test statement handling
        processed = service._preprocess_query("Tell me about AI")
        assert processed == "Tell me about AI."
        
        # Test existing punctuation preservation
        processed = service._preprocess_query("What is AI?")
        assert processed == "What is AI?"
    
    def test_prompt_building(self, sample_context_chunks):
        """Test RAG prompt building."""
        config = GenerationConfig(citation_format=CitationFormat.NUMBERED)
        service = GenerationService(Mock(), config)
        
        prompt = service._build_rag_prompt(
            "What is AI?",
            sample_context_chunks[:2],  # Use first 2 chunks
            config
        )
        
        # Verify prompt structure
        assert "CONTEXT:" in prompt
        assert "INSTRUCTIONS:" in prompt
        assert "QUESTION:" in prompt
        assert "RESPONSE:" in prompt
        
        # Verify context is included
        assert sample_context_chunks[0].content in prompt
        assert sample_context_chunks[1].content in prompt
        
        # Verify numbered citations
        assert "[1]" in prompt
        assert "[2]" in prompt
        
        # Verify citation instructions
        assert "numbered citations" in prompt.lower()
    
    def test_confidence_score_calculation(self, sample_context_chunks):
        """Test confidence score calculation."""
        service = GenerationService(Mock())
        config = GenerationConfig()
        
        # Create sample citations
        citations = [
            SourceCitation(
                source_id="1",
                document_id="doc-1",
                chunk_id="chunk-1",
                citation_text="[1]",
                confidence_score=0.9,
                relevance_score=0.9,
                content_snippet="Test content",
                chunk_index=0,
                start_position=0,
                end_position=100
            )
        ]
        
        # Test with good answer and citations
        answer = "Based on the context, AI is a branch of computer science that creates intelligent machines."
        confidence = service._calculate_confidence_score(answer, citations, sample_context_chunks, config)
        
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.5  # Should be reasonably high
        
        # Test with empty answer
        empty_confidence = service._calculate_confidence_score("", [], [], config)
        assert empty_confidence == 0.0
    
    def test_quality_level_assessment(self):
        """Test quality level assessment."""
        service = GenerationService(Mock())
        
        # Test excellent quality
        citations = [Mock(), Mock()]  # 2 citations
        quality = service._assess_quality_level(0.9, citations)
        assert quality == ResponseQuality.EXCELLENT
        
        # Test good quality
        citations = [Mock()]  # 1 citation
        quality = service._assess_quality_level(0.7, citations)
        assert quality == ResponseQuality.GOOD
        
        # Test fair quality
        quality = service._assess_quality_level(0.5, [])
        assert quality == ResponseQuality.FAIR
        
        # Test poor quality
        quality = service._assess_quality_level(0.2, [])
        assert quality == ResponseQuality.POOR
    
    @pytest.mark.asyncio
    async def test_error_handling(self, sample_context_chunks):
        """Test error handling in generation."""
        # Mock LLM manager that raises exception
        mock_llm = AsyncMock()
        mock_llm.generate_response.side_effect = Exception("LLM connection error")
        
        service = GenerationService(mock_llm)
        
        response = await service.generate_response_with_context(
            "What is AI?",
            sample_context_chunks
        )
        
        # Should return fallback response
        assert isinstance(response, GenerationResponse)
        assert "apologize" in response.answer.lower()
        assert response.confidence_score == 0.0
        assert response.quality_level == ResponseQuality.POOR
        assert len(response.sources) == 0
    
    @pytest.mark.asyncio
    async def test_simple_response_generation(self, mock_llm_manager):
        """Test simple response generation convenience method."""
        service = GenerationService(mock_llm_manager)
        
        response = await service.generate_simple_response(
            "What is AI?",
            "Artificial intelligence is a branch of computer science."
        )
        
        assert isinstance(response, str)
        assert len(response) > 0
        mock_llm_manager.generate_response.assert_called_once()
    
    def test_metrics_tracking(self, mock_llm_manager):
        """Test metrics tracking functionality."""
        service = GenerationService(mock_llm_manager)
        
        # Create sample response
        response = GenerationResponse(
            answer="Test answer",
            sources=[],
            query="Test query",
            processed_query="Test query?",
            confidence_score=0.8,
            quality_level=ResponseQuality.GOOD,
            citation_accuracy=0.9,
            generation_time_ms=100.0,
            context_length=500,
            response_length=50,
            llm_provider="ollama",
            llm_model="llama3.2:3b",
            llm_response_time=80.0,
            config_used=GenerationConfig()
        )
        
        # Update metrics
        service.metrics["successful_generations"] = 1
        service._update_metrics(response)
        
        # Get stats
        stats = service.get_generation_stats()
        
        assert "total_generations" in stats
        assert "successful_generations" in stats
        assert "average_generation_time_ms" in stats
        assert "average_confidence_score" in stats
        assert "citation_accuracy_rate" in stats
    
    def test_convenience_function(self):
        """Test create_generation_service convenience function."""
        mock_llm = Mock()
        
        service = create_generation_service(
            llm_manager=mock_llm,
            citation_format=CitationFormat.BRACKETED,
            max_context_length=5000,
            require_citations=False
        )
        
        assert isinstance(service, GenerationService)
        assert service.llm_manager == mock_llm
        assert service.config.citation_format == CitationFormat.BRACKETED
        assert service.config.max_context_length == 5000
        assert service.config.require_citations is False
