"""
Unit tests for the intelligent document chunking service.

Tests verify semantic coherence, context preservation, overlap management,
and quality validation for various chunking strategies.
"""

import pytest
from unittest.mock import Mock, patch
import uuid

from app.services.chunking_service import (
    DocumentChunker,
    ChunkingConfig,
    ChunkingStrategy,
    ChunkMetadata,
    DocumentChunkResult,
    create_chunker
)
from app.database.models import Document


class TestChunkingConfig:
    """Test chunking configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = ChunkingConfig()
        
        assert config.chunk_size == 1000
        assert config.chunk_overlap == 200
        assert config.strategy == ChunkingStrategy.RECURSIVE_CHARACTER
        assert config.min_chunk_size == 100
        assert config.max_chunk_size == 2000
        assert config.preserve_sentences is True
        assert config.preserve_paragraphs is True
        assert len(config.separators) > 0
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = ChunkingConfig(
            chunk_size=500,
            chunk_overlap=100,
            strategy=ChunkingStrategy.SENTENCE_BASED,
            min_chunk_size=50,
            max_chunk_size=1000
        )
        
        assert config.chunk_size == 500
        assert config.chunk_overlap == 100
        assert config.strategy == ChunkingStrategy.SENTENCE_BASED
        assert config.min_chunk_size == 50
        assert config.max_chunk_size == 1000


class TestChunkMetadata:
    """Test chunk metadata functionality."""
    
    def test_metadata_creation(self):
        """Test chunk metadata creation."""
        metadata = ChunkMetadata(
            chunk_id="test-chunk-001",
            document_id="doc-123",
            chunk_index=0,
            start_position=0,
            end_position=100,
            chunk_size=100,
            word_count=20,
            sentence_count=3,
            paragraph_count=1,
            content_density=0.85,
            semantic_coherence_score=0.75
        )
        
        assert metadata.chunk_id == "test-chunk-001"
        assert metadata.document_id == "doc-123"
        assert metadata.chunk_index == 0
        assert metadata.chunk_size == 100
        assert metadata.content_density == 0.85
        assert metadata.semantic_coherence_score == 0.75
    
    def test_metadata_to_dict(self):
        """Test metadata serialization to dictionary."""
        metadata = ChunkMetadata(
            chunk_id="test-chunk-001",
            document_id="doc-123",
            chunk_index=0,
            start_position=0,
            end_position=100,
            chunk_size=100,
            word_count=20,
            sentence_count=3,
            paragraph_count=1,
            content_density=0.85,
            semantic_coherence_score=0.75
        )
        
        metadata_dict = metadata.to_dict()
        
        assert isinstance(metadata_dict, dict)
        assert metadata_dict["chunk_id"] == "test-chunk-001"
        assert metadata_dict["document_id"] == "doc-123"
        assert metadata_dict["chunk_size"] == 100
        assert metadata_dict["content_density"] == 0.85


class TestDocumentChunker:
    """Test document chunker functionality."""
    
    @pytest.fixture
    def sample_text(self):
        """Sample multi-paragraph text for testing."""
        return """
        This is the first paragraph of our test document. It contains multiple sentences that should be preserved together for semantic coherence. The content discusses various aspects of document processing and chunking strategies.

        The second paragraph introduces new concepts and ideas. It builds upon the foundation laid in the first paragraph while maintaining contextual relevance. This paragraph also contains technical details about implementation approaches.

        Our third paragraph delves deeper into the technical specifications. It provides concrete examples and use cases that demonstrate the practical applications of the concepts discussed earlier. The information here is crucial for understanding the complete picture.

        The final paragraph serves as a conclusion, summarizing the key points and providing actionable insights. It ties together all the previous discussions and offers a clear path forward for implementation and optimization.
        """.strip()
    
    @pytest.fixture
    def sample_document(self, sample_text):
        """Sample document model for testing."""
        return Document(
            id="test-doc-123",
            title="Test Document",
            content=sample_text,
            content_type="text/plain",
            file_path="/test/document.txt",
            doc_metadata={"author": "Test Author", "category": "Technical"},
            tags=["test", "chunking", "rag"]
        )
    
    def test_chunker_initialization(self):
        """Test chunker initialization with default config."""
        chunker = DocumentChunker()
        
        assert chunker.config.chunk_size == 1000
        assert chunker.config.chunk_overlap == 200
        assert chunker.config.strategy == ChunkingStrategy.RECURSIVE_CHARACTER
        assert len(chunker._text_splitters) > 0
    
    def test_chunker_with_custom_config(self):
        """Test chunker initialization with custom config."""
        config = ChunkingConfig(
            chunk_size=500,
            chunk_overlap=100,
            strategy=ChunkingStrategy.SENTENCE_BASED
        )
        chunker = DocumentChunker(config)
        
        assert chunker.config.chunk_size == 500
        assert chunker.config.chunk_overlap == 100
        assert chunker.config.strategy == ChunkingStrategy.SENTENCE_BASED
    
    def test_chunk_document_with_string(self, sample_text):
        """Test chunking with string input."""
        chunker = DocumentChunker(ChunkingConfig(chunk_size=300, chunk_overlap=50))
        
        chunks = chunker.chunk_document(sample_text)
        
        assert len(chunks) > 1  # Should create multiple chunks
        assert all(isinstance(chunk, DocumentChunkResult) for chunk in chunks)
        assert all(len(chunk.content) <= 400 for chunk in chunks)  # Reasonable size
        
        # Check chunk indices are sequential
        for i, chunk in enumerate(chunks):
            assert chunk.metadata.chunk_index == i
    
    def test_chunk_document_with_document_model(self, sample_document):
        """Test chunking with Document model input."""
        chunker = DocumentChunker(ChunkingConfig(chunk_size=400, chunk_overlap=80))
        
        chunks = chunker.chunk_document(sample_document)
        
        assert len(chunks) > 1
        assert all(chunk.metadata.document_id == sample_document.id for chunk in chunks)
        
        # Check metadata preservation
        first_chunk = chunks[0]
        assert first_chunk.metadata.document_id == "test-doc-123"
        assert isinstance(first_chunk.metadata.chunk_id, str)
        assert first_chunk.metadata.chunk_index == 0
    
    def test_chunk_overlap_calculation(self, sample_text):
        """Test that chunk overlap is calculated correctly."""
        chunker = DocumentChunker(ChunkingConfig(chunk_size=200, chunk_overlap=50))
        
        chunks = chunker.chunk_document(sample_text)
        
        if len(chunks) > 1:
            # Check that overlaps are calculated
            for i in range(1, len(chunks)):
                overlap = chunks[i].metadata.overlap_with_previous
                assert overlap >= 0
                # Overlap should be reasonable (not more than chunk size)
                assert overlap <= len(chunks[i].content)
    
    def test_semantic_coherence_preservation(self, sample_text):
        """Test that semantic coherence is preserved in chunks."""
        chunker = DocumentChunker(ChunkingConfig(
            chunk_size=300,
            chunk_overlap=50,
            preserve_sentences=True,
            preserve_paragraphs=True
        ))
        
        chunks = chunker.chunk_document(sample_text)
        
        # Check that chunks have reasonable coherence scores
        for chunk in chunks:
            assert chunk.metadata.semantic_coherence_score >= 0.0
            assert chunk.metadata.semantic_coherence_score <= 1.0
            
            # Chunks should generally have decent coherence
            assert chunk.metadata.semantic_coherence_score > 0.3
    
    def test_content_density_calculation(self, sample_text):
        """Test content density calculation."""
        chunker = DocumentChunker()
        
        chunks = chunker.chunk_document(sample_text)
        
        for chunk in chunks:
            assert chunk.metadata.content_density >= 0.0
            assert chunk.metadata.content_density <= 1.0
            
            # Normal text should have high content density
            assert chunk.metadata.content_density > 0.7
    
    def test_chunk_metadata_completeness(self, sample_document):
        """Test that chunk metadata is complete and accurate."""
        chunker = DocumentChunker(ChunkingConfig(chunk_size=300, chunk_overlap=50))
        
        chunks = chunker.chunk_document(sample_document)
        
        for chunk in chunks:
            metadata = chunk.metadata
            
            # Required fields
            assert metadata.chunk_id is not None
            assert metadata.document_id == sample_document.id
            assert metadata.chunk_index >= 0
            assert metadata.start_position >= 0
            assert metadata.end_position > metadata.start_position
            assert metadata.chunk_size == len(chunk.content)
            
            # Content analysis
            assert metadata.word_count > 0
            assert metadata.sentence_count >= 0
            assert metadata.paragraph_count >= 0
            
            # Quality metrics
            assert 0.0 <= metadata.content_density <= 1.0
            assert 0.0 <= metadata.semantic_coherence_score <= 1.0
    
    def test_different_chunking_strategies(self, sample_text):
        """Test different chunking strategies."""
        strategies = [
            ChunkingStrategy.RECURSIVE_CHARACTER,
            ChunkingStrategy.SENTENCE_BASED,
            ChunkingStrategy.HYBRID
        ]
        
        for strategy in strategies:
            config = ChunkingConfig(
                chunk_size=300,
                chunk_overlap=50,
                strategy=strategy
            )
            chunker = DocumentChunker(config)
            
            chunks = chunker.chunk_document(sample_text)
            
            assert len(chunks) > 0
            assert all(isinstance(chunk, DocumentChunkResult) for chunk in chunks)
            
            # Each strategy should produce reasonable results
            total_length = sum(len(chunk.content) for chunk in chunks)
            assert total_length > 0
    
    def test_empty_content_handling(self):
        """Test handling of empty or minimal content."""
        chunker = DocumentChunker()
        
        # Empty string
        chunks = chunker.chunk_document("")
        assert len(chunks) == 0
        
        # Very short content
        short_content = "Short text."
        chunks = chunker.chunk_document(short_content)
        assert len(chunks) <= 1
        if chunks:
            assert chunks[0].content.strip() == short_content
    
    def test_chunk_validation(self, sample_text):
        """Test chunk validation functionality."""
        chunker = DocumentChunker(ChunkingConfig(chunk_size=300, chunk_overlap=50))
        
        chunks = chunker.chunk_document(sample_text)
        validation_result = chunker.validate_chunks(chunks)
        
        assert "valid" in validation_result
        assert "metrics" in validation_result
        assert "quality_score" in validation_result
        
        metrics = validation_result["metrics"]
        assert "total_chunks" in metrics
        assert "avg_chunk_size" in metrics
        assert "avg_overlap" in metrics
        assert "avg_content_density" in metrics
        assert "avg_coherence_score" in metrics
        
        # Quality score should be reasonable
        quality_score = validation_result["quality_score"]
        assert 0.0 <= quality_score <= 1.0
    
    def test_chunking_statistics(self, sample_text):
        """Test chunking statistics generation."""
        chunker = DocumentChunker(ChunkingConfig(chunk_size=250, chunk_overlap=40))
        
        chunks = chunker.chunk_document(sample_text)
        stats = chunker.get_chunking_stats(chunks)
        
        assert "chunk_count" in stats
        assert "total_content_length" in stats
        assert "avg_chunk_size" in stats
        assert "min_chunk_size" in stats
        assert "max_chunk_size" in stats
        assert "total_overlap" in stats
        assert "avg_overlap" in stats
        assert "overlap_ratio" in stats
        assert "avg_content_density" in stats
        assert "avg_coherence_score" in stats
        assert "strategy_used" in stats
        assert "config" in stats
        
        # Verify statistics make sense
        assert stats["chunk_count"] == len(chunks)
        assert stats["total_content_length"] > 0
        assert stats["avg_chunk_size"] > 0
        assert stats["min_chunk_size"] <= stats["max_chunk_size"]


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_create_chunker_function(self):
        """Test create_chunker convenience function."""
        chunker = create_chunker(
            chunk_size=500,
            chunk_overlap=100,
            strategy=ChunkingStrategy.SENTENCE_BASED
        )
        
        assert isinstance(chunker, DocumentChunker)
        assert chunker.config.chunk_size == 500
        assert chunker.config.chunk_overlap == 100
        assert chunker.config.strategy == ChunkingStrategy.SENTENCE_BASED
    
    def test_create_chunker_with_defaults(self):
        """Test create_chunker with default parameters."""
        chunker = create_chunker()
        
        assert isinstance(chunker, DocumentChunker)
        assert chunker.config.chunk_size == 1000
        assert chunker.config.chunk_overlap == 200
        assert chunker.config.strategy == ChunkingStrategy.RECURSIVE_CHARACTER


class TestDocumentChunkResult:
    """Test DocumentChunkResult functionality."""
    
    def test_to_document_chunk_conversion(self):
        """Test conversion to DocumentChunk model."""
        metadata = ChunkMetadata(
            chunk_id="test-chunk-001",
            document_id="doc-123",
            chunk_index=0,
            start_position=0,
            end_position=100,
            chunk_size=100,
            word_count=20,
            sentence_count=3,
            paragraph_count=1,
            content_density=0.85,
            semantic_coherence_score=0.75
        )
        
        chunk_result = DocumentChunkResult(
            content="This is test content for the chunk.",
            metadata=metadata
        )
        
        document_chunk = chunk_result.to_document_chunk()
        
        assert document_chunk.id == "test-chunk-001"
        assert document_chunk.document_id == "doc-123"
        assert document_chunk.content == "This is test content for the chunk."
        assert document_chunk.chunk_index == 0
        assert document_chunk.chunk_size == 100
        assert document_chunk.start_position == 0
        assert document_chunk.end_position == 100
        assert document_chunk.chunk_metadata is not None
