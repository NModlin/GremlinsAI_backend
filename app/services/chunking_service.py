"""
Intelligent Document Chunking Service

This module provides sophisticated document chunking capabilities with context preservation
and semantic coherence for advanced RAG systems. Implements multiple chunking strategies
including recursive character splitting, semantic boundary detection, and overlap management.
"""

import logging
import re
import hashlib
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid

from langchain.text_splitter import (
    RecursiveCharacterTextSplitter,
    CharacterTextSplitter,
    SentenceTransformersTokenTextSplitter,
    SpacyTextSplitter
)
from langchain.schema import Document as LangChainDocument

from app.database.models import Document, DocumentChunk

logger = logging.getLogger(__name__)


class ChunkingStrategy(Enum):
    """Available chunking strategies."""
    RECURSIVE_CHARACTER = "recursive_character"
    SENTENCE_BASED = "sentence_based"
    SEMANTIC_BOUNDARY = "semantic_boundary"
    TOKEN_BASED = "token_based"
    HYBRID = "hybrid"


@dataclass
class ChunkingConfig:
    """Configuration for document chunking."""
    
    # Basic chunking parameters
    chunk_size: int = 1000
    chunk_overlap: int = 200
    strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE_CHARACTER
    
    # Advanced parameters
    min_chunk_size: int = 100
    max_chunk_size: int = 2000
    preserve_sentences: bool = True
    preserve_paragraphs: bool = True
    
    # Semantic boundary detection
    separators: List[str] = field(default_factory=lambda: [
        "\n\n",  # Paragraphs
        "\n",    # Lines
        ". ",    # Sentences
        "! ",    # Exclamations
        "? ",    # Questions
        "; ",    # Semicolons
        ", ",    # Commas
        " ",     # Spaces
        ""       # Characters
    ])
    
    # Token-based settings
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    tokens_per_chunk: int = 256
    
    # Quality settings
    min_meaningful_content_ratio: float = 0.7
    remove_empty_chunks: bool = True
    normalize_whitespace: bool = True


@dataclass
class ChunkMetadata:
    """Metadata for a document chunk."""
    
    # Chunk identification
    chunk_id: str
    document_id: str
    chunk_index: int
    
    # Position information
    start_position: int
    end_position: int
    chunk_size: int
    
    # Content analysis
    word_count: int
    sentence_count: int
    paragraph_count: int
    
    # Quality metrics
    content_density: float
    semantic_coherence_score: float
    
    # Overlap information
    overlap_with_previous: int = 0
    overlap_with_next: int = 0
    
    # Additional metadata
    chunk_type: str = "content"
    language: Optional[str] = None
    topics: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "start_position": self.start_position,
            "end_position": self.end_position,
            "chunk_size": self.chunk_size,
            "word_count": self.word_count,
            "sentence_count": self.sentence_count,
            "paragraph_count": self.paragraph_count,
            "content_density": self.content_density,
            "semantic_coherence_score": self.semantic_coherence_score,
            "overlap_with_previous": self.overlap_with_previous,
            "overlap_with_next": self.overlap_with_next,
            "chunk_type": self.chunk_type,
            "language": self.language,
            "topics": self.topics
        }


@dataclass
class DocumentChunkResult:
    """Result of document chunking operation."""
    
    content: str
    metadata: ChunkMetadata
    
    def to_document_chunk(self) -> DocumentChunk:
        """Convert to DocumentChunk model."""
        return DocumentChunk(
            id=self.metadata.chunk_id,
            document_id=self.metadata.document_id,
            content=self.content,
            chunk_index=self.metadata.chunk_index,
            chunk_size=self.metadata.chunk_size,
            start_position=self.metadata.start_position,
            end_position=self.metadata.end_position,
            chunk_metadata=self.metadata.to_dict()
        )


class DocumentChunker:
    """
    Intelligent document chunker with context preservation and semantic coherence.
    
    Provides multiple chunking strategies optimized for RAG systems:
    - Recursive character splitting with semantic boundaries
    - Sentence-based chunking for natural language
    - Token-based chunking for transformer models
    - Hybrid approaches combining multiple strategies
    """
    
    def __init__(self, config: Optional[ChunkingConfig] = None):
        """Initialize document chunker with configuration."""
        self.config = config or ChunkingConfig()
        self._text_splitters = {}
        self._initialize_splitters()
        
        logger.info(f"DocumentChunker initialized with strategy: {self.config.strategy.value}")
    
    def _initialize_splitters(self) -> None:
        """Initialize text splitters for different strategies."""
        try:
            # Recursive character splitter (primary strategy)
            self._text_splitters[ChunkingStrategy.RECURSIVE_CHARACTER] = RecursiveCharacterTextSplitter(
                chunk_size=self.config.chunk_size,
                chunk_overlap=self.config.chunk_overlap,
                separators=self.config.separators,
                keep_separator=True,
                is_separator_regex=False
            )
            
            # Character splitter for simple splitting
            self._text_splitters[ChunkingStrategy.SENTENCE_BASED] = CharacterTextSplitter(
                chunk_size=self.config.chunk_size,
                chunk_overlap=self.config.chunk_overlap,
                separator=". ",
                keep_separator=True
            )
            
            # Token-based splitter
            try:
                self._text_splitters[ChunkingStrategy.TOKEN_BASED] = SentenceTransformersTokenTextSplitter(
                    chunk_overlap=self.config.chunk_overlap,
                    model_name=self.config.model_name,
                    tokens_per_chunk=self.config.tokens_per_chunk
                )
            except Exception as e:
                logger.warning(f"Could not initialize token-based splitter: {e}")
            
            # Spacy splitter for advanced NLP
            try:
                self._text_splitters[ChunkingStrategy.SEMANTIC_BOUNDARY] = SpacyTextSplitter(
                    chunk_size=self.config.chunk_size,
                    chunk_overlap=self.config.chunk_overlap,
                    pipeline="en_core_web_sm"
                )
            except Exception as e:
                logger.warning(f"Could not initialize spaCy splitter: {e}")
            
            logger.info(f"Initialized {len(self._text_splitters)} text splitters")
            
        except Exception as e:
            logger.error(f"Failed to initialize text splitters: {e}")
            raise
    
    def chunk_document(
        self,
        document: Union[Document, str],
        strategy: Optional[ChunkingStrategy] = None
    ) -> List[DocumentChunkResult]:
        """
        Chunk a document into semantically coherent pieces.
        
        Args:
            document: Document model or text content to chunk
            strategy: Chunking strategy to use (overrides config)
            
        Returns:
            List of document chunk results with metadata
        """
        try:
            # Extract content and metadata
            if isinstance(document, Document):
                content = document.content
                document_id = document.id
                doc_metadata = {
                    "title": document.title,
                    "content_type": document.content_type,
                    "file_path": document.file_path,
                    "doc_metadata": document.doc_metadata or {},
                    "tags": document.tags or []
                }
            else:
                content = document
                document_id = str(uuid.uuid4())
                doc_metadata = {}
            
            # Use specified strategy or default
            chunk_strategy = strategy or self.config.strategy
            
            logger.info(f"Chunking document {document_id} with strategy: {chunk_strategy.value}")
            
            # Preprocess content
            processed_content = self._preprocess_content(content)
            
            # Perform chunking based on strategy
            if chunk_strategy == ChunkingStrategy.HYBRID:
                chunks = self._hybrid_chunking(processed_content, document_id, doc_metadata)
            else:
                chunks = self._standard_chunking(
                    processed_content, 
                    document_id, 
                    doc_metadata, 
                    chunk_strategy
                )
            
            # Post-process chunks
            processed_chunks = self._post_process_chunks(chunks)
            
            logger.info(f"Successfully chunked document into {len(processed_chunks)} chunks")
            return processed_chunks
            
        except Exception as e:
            logger.error(f"Failed to chunk document: {e}")
            raise

    def _preprocess_content(self, content: str) -> str:
        """Preprocess document content for optimal chunking."""
        if not content:
            return ""

        processed = content

        if self.config.normalize_whitespace:
            # Normalize whitespace while preserving paragraph breaks
            processed = re.sub(r'\n\s*\n', '\n\n', processed)  # Normalize paragraph breaks
            processed = re.sub(r'[ \t]+', ' ', processed)      # Normalize spaces and tabs
            processed = re.sub(r'\n[ \t]+', '\n', processed)   # Remove leading whitespace on lines

        return processed.strip()

    def _standard_chunking(
        self,
        content: str,
        document_id: str,
        doc_metadata: Dict[str, Any],
        strategy: ChunkingStrategy
    ) -> List[DocumentChunkResult]:
        """Perform standard chunking using specified strategy."""

        # Get appropriate text splitter
        splitter = self._text_splitters.get(strategy)
        if not splitter:
            logger.warning(f"Splitter for {strategy.value} not available, using recursive character")
            splitter = self._text_splitters[ChunkingStrategy.RECURSIVE_CHARACTER]

        # Create LangChain document
        langchain_doc = LangChainDocument(
            page_content=content,
            metadata=doc_metadata
        )

        # Split document
        split_docs = splitter.split_documents([langchain_doc])

        # Convert to DocumentChunkResult objects
        chunks = []
        for i, doc in enumerate(split_docs):
            chunk_content = doc.page_content

            # Calculate positions
            start_pos = content.find(chunk_content)
            if start_pos == -1:
                # Fallback for approximate positioning
                start_pos = i * (self.config.chunk_size - self.config.chunk_overlap)
            end_pos = start_pos + len(chunk_content)

            # Calculate overlap
            overlap_prev = 0
            overlap_next = 0
            if i > 0:
                prev_chunk = chunks[i-1]
                overlap_prev = self._calculate_overlap(prev_chunk.content, chunk_content)

            # Create metadata
            metadata = self._create_chunk_metadata(
                document_id=document_id,
                chunk_index=i,
                content=chunk_content,
                start_position=start_pos,
                end_position=end_pos,
                overlap_with_previous=overlap_prev,
                doc_metadata=doc_metadata
            )

            chunks.append(DocumentChunkResult(
                content=chunk_content,
                metadata=metadata
            ))

        # Update next overlaps
        for i in range(len(chunks) - 1):
            chunks[i].metadata.overlap_with_next = self._calculate_overlap(
                chunks[i].content,
                chunks[i + 1].content
            )

        return chunks

    def _hybrid_chunking(
        self,
        content: str,
        document_id: str,
        doc_metadata: Dict[str, Any]
    ) -> List[DocumentChunkResult]:
        """Perform hybrid chunking combining multiple strategies."""

        # Start with recursive character splitting
        primary_chunks = self._standard_chunking(
            content, document_id, doc_metadata, ChunkingStrategy.RECURSIVE_CHARACTER
        )

        # Refine chunks that are too large using sentence-based splitting
        refined_chunks = []
        for chunk in primary_chunks:
            if len(chunk.content) > self.config.max_chunk_size:
                # Split large chunks further
                sub_chunks = self._standard_chunking(
                    chunk.content, document_id, doc_metadata, ChunkingStrategy.SENTENCE_BASED
                )

                # Update indices and positions
                for j, sub_chunk in enumerate(sub_chunks):
                    sub_chunk.metadata.chunk_index = len(refined_chunks)
                    sub_chunk.metadata.start_position += chunk.metadata.start_position
                    sub_chunk.metadata.end_position += chunk.metadata.start_position
                    refined_chunks.append(sub_chunk)
            else:
                chunk.metadata.chunk_index = len(refined_chunks)
                refined_chunks.append(chunk)

        return refined_chunks

    def _post_process_chunks(self, chunks: List[DocumentChunkResult]) -> List[DocumentChunkResult]:
        """Post-process chunks for quality and consistency."""
        processed_chunks = []

        for chunk in chunks:
            # Skip empty or too small chunks
            if self.config.remove_empty_chunks:
                if (len(chunk.content.strip()) < self.config.min_chunk_size or
                    chunk.metadata.content_density < self.config.min_meaningful_content_ratio):
                    logger.debug(f"Skipping chunk {chunk.metadata.chunk_index} due to low quality")
                    continue

            # Update chunk index for final list
            chunk.metadata.chunk_index = len(processed_chunks)
            processed_chunks.append(chunk)

        return processed_chunks

    def _create_chunk_metadata(
        self,
        document_id: str,
        chunk_index: int,
        content: str,
        start_position: int,
        end_position: int,
        overlap_with_previous: int = 0,
        doc_metadata: Optional[Dict[str, Any]] = None
    ) -> ChunkMetadata:
        """Create comprehensive metadata for a chunk."""

        # Generate unique chunk ID
        chunk_id = self._generate_chunk_id(document_id, chunk_index, content)

        # Analyze content
        word_count = len(content.split())
        sentence_count = len(re.findall(r'[.!?]+', content))
        paragraph_count = len(content.split('\n\n'))

        # Calculate content density (ratio of meaningful content)
        content_density = self._calculate_content_density(content)

        # Calculate semantic coherence score
        coherence_score = self._calculate_semantic_coherence(content)

        return ChunkMetadata(
            chunk_id=chunk_id,
            document_id=document_id,
            chunk_index=chunk_index,
            start_position=start_position,
            end_position=end_position,
            chunk_size=len(content),
            word_count=word_count,
            sentence_count=sentence_count,
            paragraph_count=paragraph_count,
            content_density=content_density,
            semantic_coherence_score=coherence_score,
            overlap_with_previous=overlap_with_previous
        )

    def _generate_chunk_id(self, document_id: str, chunk_index: int, content: str) -> str:
        """Generate unique, deterministic chunk ID."""
        # Create hash from document ID, index, and content snippet
        content_hash = hashlib.md5(content[:100].encode()).hexdigest()[:8]
        return f"{document_id}-chunk-{chunk_index:04d}-{content_hash}"

    def _calculate_overlap(self, chunk1: str, chunk2: str) -> int:
        """Calculate character overlap between two chunks."""
        if not chunk1 or not chunk2:
            return 0

        # Find longest common substring at the end of chunk1 and start of chunk2
        max_overlap = min(len(chunk1), len(chunk2), self.config.chunk_overlap * 2)

        for i in range(max_overlap, 0, -1):
            if chunk1[-i:] == chunk2[:i]:
                return i

        return 0

    def _calculate_content_density(self, content: str) -> float:
        """Calculate the density of meaningful content in the chunk."""
        if not content:
            return 0.0

        # Count meaningful characters (letters, numbers, basic punctuation)
        meaningful_chars = len(re.findall(r'[a-zA-Z0-9.!?;:,]', content))
        total_chars = len(content)

        return meaningful_chars / total_chars if total_chars > 0 else 0.0

    def _calculate_semantic_coherence(self, content: str) -> float:
        """Calculate semantic coherence score for the chunk."""
        if not content:
            return 0.0

        # Simple heuristic-based coherence scoring
        score = 0.0

        # Check for complete sentences
        sentences = re.split(r'[.!?]+', content)
        complete_sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        if sentences:
            score += 0.3 * (len(complete_sentences) / len(sentences))

        # Check for paragraph structure
        paragraphs = content.split('\n\n')
        if len(paragraphs) > 1:
            score += 0.2

        # Check for balanced length (not too short or too long)
        ideal_length = self.config.chunk_size
        length_ratio = min(len(content), ideal_length) / ideal_length
        score += 0.3 * length_ratio

        # Check for proper capitalization and punctuation
        if re.search(r'^[A-Z]', content.strip()) and re.search(r'[.!?]$', content.strip()):
            score += 0.2

        return min(score, 1.0)

    def validate_chunks(self, chunks: List[DocumentChunkResult]) -> Dict[str, Any]:
        """
        Validate the quality of generated chunks.

        Returns:
            Dictionary with validation metrics and quality scores
        """
        if not chunks:
            return {
                "valid": False,
                "error": "No chunks provided",
                "metrics": {}
            }

        metrics = {
            "total_chunks": len(chunks),
            "avg_chunk_size": sum(len(c.content) for c in chunks) / len(chunks),
            "avg_overlap": sum(c.metadata.overlap_with_previous for c in chunks) / len(chunks),
            "avg_content_density": sum(c.metadata.content_density for c in chunks) / len(chunks),
            "avg_coherence_score": sum(c.metadata.semantic_coherence_score for c in chunks) / len(chunks),
            "size_distribution": self._analyze_size_distribution(chunks),
            "quality_distribution": self._analyze_quality_distribution(chunks)
        }

        # Validation criteria
        valid = True
        issues = []

        # Check chunk sizes
        oversized_chunks = [c for c in chunks if len(c.content) > self.config.max_chunk_size]
        undersized_chunks = [c for c in chunks if len(c.content) < self.config.min_chunk_size]

        if oversized_chunks:
            issues.append(f"{len(oversized_chunks)} chunks exceed maximum size")
            valid = False

        if undersized_chunks:
            issues.append(f"{len(undersized_chunks)} chunks below minimum size")

        # Check content quality
        low_quality_chunks = [
            c for c in chunks
            if c.metadata.content_density < self.config.min_meaningful_content_ratio
        ]

        if low_quality_chunks:
            issues.append(f"{len(low_quality_chunks)} chunks have low content density")

        # Check overlap consistency
        if metrics["avg_overlap"] < self.config.chunk_overlap * 0.5:
            issues.append("Average overlap is significantly lower than configured")

        return {
            "valid": valid,
            "issues": issues,
            "metrics": metrics,
            "quality_score": self._calculate_overall_quality_score(metrics)
        }

    def _analyze_size_distribution(self, chunks: List[DocumentChunkResult]) -> Dict[str, float]:
        """Analyze the distribution of chunk sizes."""
        sizes = [len(c.content) for c in chunks]

        if not sizes:
            return {}

        sizes.sort()
        n = len(sizes)

        return {
            "min": min(sizes),
            "max": max(sizes),
            "median": sizes[n // 2],
            "q1": sizes[n // 4],
            "q3": sizes[3 * n // 4],
            "std_dev": (sum((x - sum(sizes) / n) ** 2 for x in sizes) / n) ** 0.5
        }

    def _analyze_quality_distribution(self, chunks: List[DocumentChunkResult]) -> Dict[str, float]:
        """Analyze the distribution of chunk quality metrics."""
        densities = [c.metadata.content_density for c in chunks]
        coherence_scores = [c.metadata.semantic_coherence_score for c in chunks]

        return {
            "density_min": min(densities) if densities else 0,
            "density_max": max(densities) if densities else 0,
            "density_avg": sum(densities) / len(densities) if densities else 0,
            "coherence_min": min(coherence_scores) if coherence_scores else 0,
            "coherence_max": max(coherence_scores) if coherence_scores else 0,
            "coherence_avg": sum(coherence_scores) / len(coherence_scores) if coherence_scores else 0
        }

    def _calculate_overall_quality_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate overall quality score for the chunking result."""
        score = 0.0

        # Size consistency (30%)
        size_dist = metrics.get("size_distribution", {})
        if size_dist:
            # Prefer consistent sizes around the target
            avg_size = metrics.get("avg_chunk_size", 0)
            size_score = 1.0 - abs(avg_size - self.config.chunk_size) / self.config.chunk_size
            score += 0.3 * max(0, size_score)

        # Content quality (40%)
        quality_dist = metrics.get("quality_distribution", {})
        if quality_dist:
            density_score = quality_dist.get("density_avg", 0)
            coherence_score = quality_dist.get("coherence_avg", 0)
            score += 0.2 * density_score + 0.2 * coherence_score

        # Overlap consistency (20%)
        avg_overlap = metrics.get("avg_overlap", 0)
        target_overlap = self.config.chunk_overlap
        if target_overlap > 0:
            overlap_score = 1.0 - abs(avg_overlap - target_overlap) / target_overlap
            score += 0.2 * max(0, overlap_score)

        # Chunk count reasonableness (10%)
        total_chunks = metrics.get("total_chunks", 0)
        if total_chunks > 0:
            # Prefer reasonable number of chunks (not too many, not too few)
            chunk_score = min(1.0, 10 / total_chunks) if total_chunks > 10 else 1.0
            score += 0.1 * chunk_score

        return min(score, 1.0)

    def get_chunking_stats(self, chunks: List[DocumentChunkResult]) -> Dict[str, Any]:
        """Get comprehensive statistics about the chunking results."""
        if not chunks:
            return {"error": "No chunks provided"}

        total_content_length = sum(len(c.content) for c in chunks)
        total_overlap = sum(c.metadata.overlap_with_previous for c in chunks)

        return {
            "chunk_count": len(chunks),
            "total_content_length": total_content_length,
            "avg_chunk_size": total_content_length / len(chunks),
            "min_chunk_size": min(len(c.content) for c in chunks),
            "max_chunk_size": max(len(c.content) for c in chunks),
            "total_overlap": total_overlap,
            "avg_overlap": total_overlap / len(chunks),
            "overlap_ratio": total_overlap / total_content_length if total_content_length > 0 else 0,
            "avg_content_density": sum(c.metadata.content_density for c in chunks) / len(chunks),
            "avg_coherence_score": sum(c.metadata.semantic_coherence_score for c in chunks) / len(chunks),
            "strategy_used": self.config.strategy.value,
            "config": {
                "chunk_size": self.config.chunk_size,
                "chunk_overlap": self.config.chunk_overlap,
                "min_chunk_size": self.config.min_chunk_size,
                "max_chunk_size": self.config.max_chunk_size
            }
        }


def create_chunker(
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE_CHARACTER,
    **kwargs
) -> DocumentChunker:
    """
    Convenience function to create a DocumentChunker with common settings.

    Args:
        chunk_size: Target size for each chunk
        chunk_overlap: Overlap between consecutive chunks
        strategy: Chunking strategy to use
        **kwargs: Additional configuration options

    Returns:
        Configured DocumentChunker instance
    """
    config = ChunkingConfig(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        strategy=strategy,
        **kwargs
    )

    return DocumentChunker(config)
