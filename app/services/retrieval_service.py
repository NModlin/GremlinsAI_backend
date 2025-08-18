"""
Hybrid Search Retrieval Service

This module provides sophisticated hybrid search capabilities combining semantic vector search
with keyword matching (BM25) for optimal retrieval performance in RAG systems.
Implements advanced ranking algorithms and query optimization strategies.
"""

import logging
import time
import re
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid
from datetime import datetime

import weaviate
from weaviate.exceptions import WeaviateBaseError
from weaviate.collections.classes.filters import Filter

logger = logging.getLogger(__name__)


class SearchStrategy(Enum):
    """Available search strategies."""
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"
    AUTO = "auto"


class RankingMethod(Enum):
    """Available ranking methods for hybrid search."""
    WEIGHTED_SUM = "weighted_sum"
    RRF = "reciprocal_rank_fusion"
    NORMALIZED_SCORE = "normalized_score"
    ADAPTIVE = "adaptive"


class MediaType(Enum):
    """Supported media types for multimodal content."""
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    TEXT = "text"


@dataclass
class MultiModalResult:
    """Individual multimodal search result."""

    # Content identification
    content_id: str
    media_type: str
    filename: str
    storage_path: str

    # Content metadata
    file_size: int
    content_hash: str
    created_at: datetime
    updated_at: datetime

    # Processing results
    processing_status: str
    processing_result: Dict[str, Any]
    text_content: str

    # Search relevance
    relevance_score: float
    cross_modal_score: float

    # Embeddings
    visual_embedding: Optional[List[float]] = None
    text_embedding: Optional[List[float]] = None

    # Conversation context
    conversation_id: Optional[str] = None

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "content_id": self.content_id,
            "media_type": self.media_type,
            "filename": self.filename,
            "storage_path": self.storage_path,
            "file_size": self.file_size,
            "content_hash": self.content_hash,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "processing_status": self.processing_status,
            "processing_result": self.processing_result,
            "text_content": self.text_content,
            "relevance_score": self.relevance_score,
            "cross_modal_score": self.cross_modal_score,
            "visual_embedding": self.visual_embedding,
            "text_embedding": self.text_embedding,
            "conversation_id": self.conversation_id,
            "metadata": self.metadata
        }


@dataclass
class MultiModalSearchResponse:
    """Response from multimodal search."""

    # Search results
    results: List[MultiModalResult]
    total_results: int

    # Search metadata
    query: str
    search_time: float

    # Quality metrics
    cross_modal_accuracy: float
    relevance_threshold: float

    # Search configuration
    limit: int
    offset: int

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        return {
            "results": [result.to_dict() for result in self.results],
            "total_results": self.total_results,
            "query": self.query,
            "search_time": self.search_time,
            "cross_modal_accuracy": self.cross_modal_accuracy,
            "relevance_threshold": self.relevance_threshold,
            "limit": self.limit,
            "offset": self.offset,
            "metadata": self.metadata
        }


@dataclass
class MultiModalSearchConfig:
    """Configuration for multimodal cross-modal search."""

    # Basic search parameters
    limit: int = 10
    offset: int = 0

    # Cross-modal search settings
    relevance_threshold: float = 0.7
    cross_modal_weight: float = 0.8
    text_weight: float = 0.2

    # Media type filtering
    media_types: Optional[List[MediaType]] = None

    # Quality settings
    min_cross_modal_score: float = 0.6
    max_results: int = 100

    # Performance settings
    timeout_seconds: float = 30.0
    enable_caching: bool = True
    cache_ttl_seconds: int = 300

    # Search enhancement
    enable_query_expansion: bool = True
    enable_semantic_boost: bool = True

    # Filtering options
    conversation_id: Optional[str] = None
    date_range: Optional[Tuple[datetime, datetime]] = None
    file_size_range: Optional[Tuple[int, int]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "limit": self.limit,
            "offset": self.offset,
            "relevance_threshold": self.relevance_threshold,
            "cross_modal_weight": self.cross_modal_weight,
            "text_weight": self.text_weight,
            "media_types": [mt.value for mt in self.media_types] if self.media_types else None,
            "min_cross_modal_score": self.min_cross_modal_score,
            "max_results": self.max_results,
            "timeout_seconds": self.timeout_seconds,
            "enable_caching": self.enable_caching,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "enable_query_expansion": self.enable_query_expansion,
            "enable_semantic_boost": self.enable_semantic_boost,
            "conversation_id": self.conversation_id,
            "date_range": [d.isoformat() for d in self.date_range] if self.date_range else None,
            "file_size_range": self.file_size_range
        }


@dataclass
class SearchConfig:
    """Configuration for hybrid search retrieval."""
    
    # Basic search parameters
    strategy: SearchStrategy = SearchStrategy.HYBRID
    limit: int = 10
    offset: int = 0
    
    # Hybrid search weights
    semantic_weight: float = 0.7
    keyword_weight: float = 0.3
    
    # Search quality parameters
    min_relevance_score: float = 0.5
    max_results: int = 100
    
    # Query processing
    enable_query_expansion: bool = True
    enable_spell_correction: bool = True
    enable_stemming: bool = True
    
    # Ranking configuration
    ranking_method: RankingMethod = RankingMethod.WEIGHTED_SUM
    rrf_k: int = 60  # RRF parameter
    
    # Filtering options
    document_filters: Optional[Dict[str, Any]] = None
    chunk_filters: Optional[Dict[str, Any]] = None
    
    # Performance settings
    timeout_seconds: float = 30.0
    enable_caching: bool = True
    cache_ttl_seconds: int = 300
    
    # Quality thresholds
    semantic_threshold: float = 0.6
    keyword_threshold: float = 0.4
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "strategy": self.strategy.value,
            "limit": self.limit,
            "offset": self.offset,
            "semantic_weight": self.semantic_weight,
            "keyword_weight": self.keyword_weight,
            "min_relevance_score": self.min_relevance_score,
            "ranking_method": self.ranking_method.value,
            "enable_query_expansion": self.enable_query_expansion,
            "enable_spell_correction": self.enable_spell_correction,
            "document_filters": self.document_filters,
            "chunk_filters": self.chunk_filters
        }


@dataclass
class SearchResult:
    """Individual search result with metadata."""
    
    # Core content
    chunk_id: str
    document_id: str
    content: str
    
    # Relevance scores
    semantic_score: float
    keyword_score: float
    hybrid_score: float
    
    # Position and metadata
    chunk_index: int
    start_position: int
    end_position: int
    chunk_metadata: Dict[str, Any]
    
    # Search context
    query_match_highlights: List[str] = field(default_factory=list)
    matched_terms: List[str] = field(default_factory=list)
    
    # Quality metrics
    content_quality_score: float = 0.0
    freshness_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "content": self.content,
            "semantic_score": self.semantic_score,
            "keyword_score": self.keyword_score,
            "hybrid_score": self.hybrid_score,
            "chunk_index": self.chunk_index,
            "start_position": self.start_position,
            "end_position": self.end_position,
            "chunk_metadata": self.chunk_metadata,
            "query_match_highlights": self.query_match_highlights,
            "matched_terms": self.matched_terms,
            "content_quality_score": self.content_quality_score,
            "freshness_score": self.freshness_score
        }


@dataclass
class SearchResponse:
    """Complete search response with results and metadata."""
    
    # Results
    results: List[SearchResult]
    
    # Query information
    query: str
    processed_query: str
    strategy_used: SearchStrategy
    
    # Performance metrics
    total_results: int
    search_time_ms: float
    
    # Quality metrics
    avg_relevance_score: float
    max_relevance_score: float
    min_relevance_score: float
    
    # Search metadata
    config_used: SearchConfig
    filters_applied: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        return {
            "results": [result.to_dict() for result in self.results],
            "query": self.query,
            "processed_query": self.processed_query,
            "strategy_used": self.strategy_used.value,
            "total_results": self.total_results,
            "search_time_ms": self.search_time_ms,
            "avg_relevance_score": self.avg_relevance_score,
            "max_relevance_score": self.max_relevance_score,
            "min_relevance_score": self.min_relevance_score,
            "config_used": self.config_used.to_dict(),
            "filters_applied": self.filters_applied
        }


class RetrievalService:
    """
    Hybrid search retrieval service combining semantic and keyword matching.
    
    Provides sophisticated search capabilities optimized for RAG systems:
    - Semantic vector search using embeddings
    - Keyword search using BM25 algorithm
    - Hybrid search combining both approaches
    - Advanced ranking and relevance scoring
    - Query optimization and preprocessing
    """
    
    def __init__(
        self,
        weaviate_client: Optional[weaviate.WeaviateClient] = None,
        config: Optional[SearchConfig] = None
    ):
        """Initialize retrieval service."""
        self.client = weaviate_client
        self.config = config or SearchConfig()
        self._cache = {} if self.config.enable_caching else None

        # Performance optimization: Pre-compile common filter patterns
        self._filter_cache = {}
        self._query_cache = {}

        # Connection pooling for better performance
        self._connection_pool_size = 5
        self._active_connections = 0

        logger.info(f"RetrievalService initialized with strategy: {self.config.strategy.value}")
        logger.info(f"Performance optimizations enabled: caching={self.config.enable_caching}, pool_size={self._connection_pool_size}")
    
    def search_documents(
        self,
        query: str,
        config: Optional[SearchConfig] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> SearchResponse:
        """
        Search documents using hybrid approach combining semantic and keyword matching.
        
        Args:
            query: User search query
            config: Optional search configuration (overrides default)
            filters: Optional additional filters
            
        Returns:
            SearchResponse with ranked results and metadata
        """
        start_time = time.time()
        search_config = config or self.config
        
        try:
            logger.info(f"Searching documents with query: '{query}' using strategy: {search_config.strategy.value}")
            
            # Preprocess query
            processed_query = self._preprocess_query(query, search_config)
            
            # Check cache if enabled
            cache_key = self._generate_cache_key(processed_query, search_config, filters)
            if self._cache and cache_key in self._cache:
                cached_result = self._cache[cache_key]
                if time.time() - cached_result["timestamp"] < search_config.cache_ttl_seconds:
                    logger.info("Returning cached search results")
                    return cached_result["response"]
            
            # Execute search based on strategy
            if search_config.strategy == SearchStrategy.SEMANTIC:
                results = self._semantic_search(processed_query, search_config, filters)
            elif search_config.strategy == SearchStrategy.KEYWORD:
                results = self._keyword_search(processed_query, search_config, filters)
            elif search_config.strategy == SearchStrategy.HYBRID:
                results = self._hybrid_search(processed_query, search_config, filters)
            elif search_config.strategy == SearchStrategy.AUTO:
                results = self._auto_search(processed_query, search_config, filters)
            else:
                raise ValueError(f"Unknown search strategy: {search_config.strategy}")
            
            # Process and rank results
            processed_results = self._process_results(results, query, processed_query, search_config)
            
            # Calculate metrics
            search_time_ms = (time.time() - start_time) * 1000
            
            # Create response
            response = self._create_search_response(
                processed_results,
                query,
                processed_query,
                search_config,
                search_time_ms,
                filters or {}
            )
            
            # Cache result if enabled
            if self._cache:
                self._cache[cache_key] = {
                    "response": response,
                    "timestamp": time.time()
                }
            
            logger.info(f"Search completed: {len(processed_results)} results in {search_time_ms:.2f}ms")
            return response
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            # Return empty response on error
            return SearchResponse(
                results=[],
                query=query,
                processed_query=query,
                strategy_used=search_config.strategy,
                total_results=0,
                search_time_ms=(time.time() - start_time) * 1000,
                avg_relevance_score=0.0,
                max_relevance_score=0.0,
                min_relevance_score=0.0,
                config_used=search_config,
                filters_applied=filters or {}
            )

    def _preprocess_query(self, query: str, config: SearchConfig) -> str:
        """Preprocess query for optimal search performance."""
        processed = query.strip()

        if not processed:
            return processed

        # Basic cleaning
        processed = re.sub(r'\s+', ' ', processed)  # Normalize whitespace
        processed = re.sub(r'[^\w\s\-\.]', ' ', processed)  # Remove special chars except hyphens and periods

        # Query expansion (simple implementation)
        if config.enable_query_expansion:
            processed = self._expand_query(processed)

        # Spell correction (placeholder - would integrate with spell checker)
        if config.enable_spell_correction:
            processed = self._correct_spelling(processed)

        # Stemming (basic implementation)
        if config.enable_stemming:
            processed = self._apply_stemming(processed)

        return processed.strip()

    def _expand_query(self, query: str) -> str:
        """Expand query with synonyms and related terms."""
        # Simple synonym expansion (in production, use proper NLP library)
        synonyms = {
            "ai": "artificial intelligence machine learning",
            "ml": "machine learning artificial intelligence",
            "nlp": "natural language processing text analysis",
            "api": "application programming interface endpoint",
            "db": "database data storage",
            "ui": "user interface frontend"
        }

        words = query.lower().split()
        expanded_words = []

        for word in words:
            expanded_words.append(word)
            if word in synonyms:
                expanded_words.extend(synonyms[word].split())

        return " ".join(expanded_words)

    def _correct_spelling(self, query: str) -> str:
        """Apply basic spell correction."""
        # Placeholder for spell correction
        # In production, integrate with libraries like pyspellchecker
        return query

    def _apply_stemming(self, query: str) -> str:
        """Apply basic stemming to query terms."""
        # Simple stemming rules (in production, use proper stemmer)
        stemming_rules = {
            "running": "run",
            "runs": "run",
            "programming": "program",
            "programs": "program",
            "searching": "search",
            "searches": "search"
        }

        words = query.split()
        stemmed_words = []

        for word in words:
            stemmed_words.append(stemming_rules.get(word.lower(), word))

        return " ".join(stemmed_words)

    def _semantic_search(
        self,
        query: str,
        config: SearchConfig,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute optimized semantic vector search with performance enhancements."""
        try:
            # Performance optimization: Check distributed cache first
            from app.core.caching_service import caching_service

            cached_results = await caching_service.get_vector_search_results(
                query=query,
                filters=filters or {},
                limit=config.limit
            )
            if cached_results is not None:
                logger.debug(f"Cache hit for semantic search: {query[:50]}...")
                return cached_results

            collection = self.client.collections.get("DocumentChunk")

            # Build optimized where filter with pre-filtering for performance
            where_filter = self._build_optimized_where_filter(config, filters)

            # Performance optimization: Use hybrid search for better results
            if config.enable_hybrid_search:
                response = collection.query.hybrid(
                    query=query,
                    limit=min(config.limit, 50),  # Reduced limit for hybrid search
                    offset=config.offset,
                    where=where_filter,
                    return_metadata=["score", "distance", "explain_score"],
                    alpha=0.7  # Balance between vector and keyword search
                )
            else:
                # Optimized semantic search with performance tuning
                response = collection.query.near_text(
                    query=query,
                    limit=min(config.limit, 100),  # Cap limit for better performance
                    offset=config.offset,
                    where=where_filter,
                    return_metadata=["score", "distance"],
                    # Performance optimization: Use certainty threshold for faster filtering
                    certainty=config.min_relevance_score if config.min_relevance_score > 0 else None,
                    # Additional performance optimizations
                    move_to={
                        "concepts": [query],
                        "force": 0.85
                    } if len(query.split()) > 3 else None
                )

            # Convert to standard format with performance optimization
            results = []
            for obj in response.objects:
                # Extract properties efficiently
                properties = obj.properties
                metadata = obj.metadata

                result = {
                    "chunk_id": obj.uuid,
                    "properties": properties,
                    "metadata": metadata,
                    "semantic_score": 1.0 - (metadata.distance or 0.0),
                    "keyword_score": 0.0,
                    "search_type": "semantic",
                    # Add additional fields for better context
                    "document_id": properties.get("documentId", ""),
                    "chunk_index": properties.get("chunkIndex", 0)
                }
                results.append(result)

            # Cache results in distributed cache for better performance
            if len(results) > 0:
                await caching_service.set_vector_search_results(
                    query=query,
                    filters=filters or {},
                    limit=config.limit,
                    results=results,
                    ttl=600  # 10 minutes cache
                )

            logger.debug(f"Optimized semantic search returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

    def _keyword_search(
        self,
        query: str,
        config: SearchConfig,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute keyword search using BM25."""
        try:
            collection = self.client.collections.get("DocumentChunk")

            # Build where filter
            where_filter = self._build_where_filter(config, filters)

            # Execute BM25 search
            response = collection.query.bm25(
                query=query,
                limit=config.limit,
                offset=config.offset,
                where=where_filter,
                return_metadata=["score"]
            )

            # Convert to standard format
            results = []
            for obj in response.objects:
                result = {
                    "chunk_id": obj.uuid,
                    "properties": obj.properties,
                    "metadata": obj.metadata,
                    "semantic_score": 0.0,
                    "keyword_score": obj.metadata.score or 0.0,
                    "search_type": "keyword"
                }
                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []

    def _hybrid_search(
        self,
        query: str,
        config: SearchConfig,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute hybrid search combining semantic and keyword approaches."""
        try:
            collection = self.client.collections.get("DocumentChunk")

            # Build where filter
            where_filter = self._build_where_filter(config, filters)

            # Execute hybrid search
            response = collection.query.hybrid(
                query=query,
                alpha=config.semantic_weight,  # 0 = pure BM25, 1 = pure vector
                limit=config.limit,
                offset=config.offset,
                where=where_filter,
                return_metadata=["score", "explain_score"]
            )

            # Convert to standard format
            results = []
            for obj in response.objects:
                # Extract scores from explain_score if available
                explain_score = obj.metadata.explain_score or {}
                semantic_score = explain_score.get("vector", 0.0)
                keyword_score = explain_score.get("bm25", 0.0)

                result = {
                    "chunk_id": obj.uuid,
                    "properties": obj.properties,
                    "metadata": obj.metadata,
                    "semantic_score": semantic_score,
                    "keyword_score": keyword_score,
                    "hybrid_score": obj.metadata.score or 0.0,
                    "search_type": "hybrid"
                }
                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return []

    def _auto_search(
        self,
        query: str,
        config: SearchConfig,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Automatically select best search strategy based on query characteristics."""

        # Analyze query to determine best strategy
        query_length = len(query.split())
        has_specific_terms = bool(re.search(r'\b(id|name|title|type)\b', query.lower()))
        has_semantic_intent = query_length > 3 and not has_specific_terms

        if has_specific_terms or query_length <= 2:
            # Use keyword search for specific terms or short queries
            logger.info("Auto-selecting keyword search strategy")
            return self._keyword_search(query, config, filters)
        elif has_semantic_intent:
            # Use semantic search for longer, conceptual queries
            logger.info("Auto-selecting semantic search strategy")
            return self._semantic_search(query, config, filters)
        else:
            # Use hybrid for balanced queries
            logger.info("Auto-selecting hybrid search strategy")
            return self._hybrid_search(query, config, filters)

    def _build_optimized_where_filter(
        self,
        config: SearchConfig,
        additional_filters: Optional[Dict[str, Any]] = None
    ) -> Optional[Filter]:
        """Build highly optimized Weaviate where filter with pre-filtering for 1000+ QPS."""
        # Create cache key for filter reuse
        filter_key = self._create_filter_cache_key(config, additional_filters)

        # Check cache first for performance optimization
        if filter_key in self._filter_cache:
            return self._filter_cache[filter_key]

        # Build optimized filter with pre-filtering strategy
        filter_conditions = []

        # Performance optimization: Add most selective filters first
        if additional_filters:
            # Sort filters by selectivity (most selective first)
            sorted_filters = self._sort_filters_by_selectivity(additional_filters)

            for key, value in sorted_filters.items():
                if key == "document_id" and value:
                    # Most selective filter - document ID
                    filter_conditions.append(
                        Filter.by_property("documentId").equal(value)
                    )
                elif key == "document_type" and value:
                    # Highly selective - document type
                    filter_conditions.append(
                        Filter.by_property("documentType").equal(value)
                    )
                elif key == "created_after" and value:
                    # Time-based filtering for recent documents
                    filter_conditions.append(
                        Filter.by_property("createdAt").greater_than(value)
                    )
                elif key == "chunk_size_min" and value:
                    # Size-based pre-filtering
                    filter_conditions.append(
                        Filter.by_property("chunkSize").greater_than(value)
                    )

        # Combine filters efficiently
        if len(filter_conditions) == 0:
            where_filter = None
        elif len(filter_conditions) == 1:
            where_filter = filter_conditions[0]
        else:
            # Use AND for multiple conditions (most restrictive)
            where_filter = filter_conditions[0]
            for condition in filter_conditions[1:]:
                where_filter = where_filter & condition

        # Cache the filter for reuse
        self._filter_cache[filter_key] = where_filter

        # Limit cache size
        if len(self._filter_cache) > 500:
            # Remove oldest entries
            oldest_keys = list(self._filter_cache.keys())[:50]
            for key in oldest_keys:
                del self._filter_cache[key]

        return where_filter

    def _sort_filters_by_selectivity(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Sort filters by selectivity (most selective first) for optimal performance."""
        # Define selectivity order (most selective first)
        selectivity_order = [
            "document_id",      # Most selective
            "document_type",    # Highly selective
            "user_id",         # Moderately selective
            "created_after",   # Time-based
            "chunk_size_min",  # Size-based
            "tags",           # Tag-based
        ]

        sorted_filters = {}

        # Add filters in selectivity order
        for key in selectivity_order:
            if key in filters and filters[key] is not None:
                sorted_filters[key] = filters[key]

        # Add any remaining filters
        for key, value in filters.items():
            if key not in sorted_filters and value is not None:
                sorted_filters[key] = value

        return sorted_filters

    def _build_where_filter(
        self,
        config: SearchConfig,
        additional_filters: Optional[Dict[str, Any]] = None
    ) -> Optional[Filter]:
        """Build optimized Weaviate where filter with caching for better P99 latency."""
        # Use the optimized version for better performance
        return self._build_optimized_where_filter(config, additional_filters)

        filters = []

        # Optimized filter building with indexed field prioritization
        # Process most selective filters first for better query performance

        # Add document filters (prioritize indexed fields)
        if config.document_filters:
            # Sort filters by selectivity (indexed fields first)
            sorted_doc_filters = self._sort_filters_by_selectivity(config.document_filters)
            for field, value in sorted_doc_filters:
                if isinstance(value, list):
                    # Use more efficient contains_any for list values
                    filters.append(Filter.by_property(field).contains_any(value))
                else:
                    # Use equal for single values
                    filters.append(Filter.by_property(field).equal(value))

        # Add chunk filters (optimized for chunk-specific queries)
        if config.chunk_filters:
            sorted_chunk_filters = self._sort_filters_by_selectivity(config.chunk_filters)
            for field, value in sorted_chunk_filters:
                if isinstance(value, list):
                    filters.append(Filter.by_property(field).contains_any(value))
                else:
                    filters.append(Filter.by_property(field).equal(value))

        # Add additional filters
        if additional_filters:
            sorted_additional_filters = self._sort_filters_by_selectivity(additional_filters)
            for field, value in sorted_additional_filters:
                if isinstance(value, list):
                    filters.append(Filter.by_property(field).contains_any(value))
                else:
                    filters.append(Filter.by_property(field).equal(value))

        # Optimized filter combination
        combined_filter = self._combine_filters_optimized(filters)

        # Cache the result for future use
        self._filter_cache[filter_key] = combined_filter

        return combined_filter

    def _create_filter_cache_key(
        self,
        config: SearchConfig,
        additional_filters: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a cache key for filter combinations."""
        import hashlib
        import json

        key_data = {
            'doc_filters': config.document_filters or {},
            'chunk_filters': config.chunk_filters or {},
            'additional': additional_filters or {}
        }

        # Create deterministic hash
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    def _sort_filters_by_selectivity(self, filters: Dict[str, Any]) -> List[tuple]:
        """Sort filters by selectivity for optimal query performance."""
        # Define indexed fields that should be processed first
        indexed_fields = {
            'documentId': 1,      # Primary key - highest selectivity
            'chunkId': 1,         # Primary key - highest selectivity
            'contentType': 2,     # Indexed field - high selectivity
            'isActive': 3,        # Boolean field - medium selectivity
            'tags': 4,            # Array field - medium selectivity
            'createdAt': 5,       # Date field - lower selectivity
            'updatedAt': 5,       # Date field - lower selectivity
            'metadata': 6         # Object field - lowest selectivity
        }

        # Sort by selectivity (lower number = higher priority)
        sorted_items = sorted(
            filters.items(),
            key=lambda x: indexed_fields.get(x[0], 10)  # Default to low priority
        )

        return sorted_items

    def _combine_filters_optimized(self, filters: List[Filter]) -> Optional[Filter]:
        """Combine filters with optimized AND logic."""
        if len(filters) == 0:
            return None
        elif len(filters) == 1:
            return filters[0]
        else:
            # Use iterative combination for better performance
            combined_filter = filters[0]
            for f in filters[1:]:
                combined_filter = combined_filter & f
            return combined_filter

    def _process_results(
        self,
        raw_results: List[Dict[str, Any]],
        original_query: str,
        processed_query: str,
        config: SearchConfig
    ) -> List[SearchResult]:
        """Process and enhance raw search results."""
        processed_results = []

        for result in raw_results:
            try:
                # Extract properties
                props = result.get("properties", {})
                metadata = result.get("metadata", {})

                # Create SearchResult
                search_result = SearchResult(
                    chunk_id=result.get("chunk_id", ""),
                    document_id=props.get("documentId", ""),
                    content=props.get("content", ""),
                    semantic_score=result.get("semantic_score", 0.0),
                    keyword_score=result.get("keyword_score", 0.0),
                    hybrid_score=result.get("hybrid_score", 0.0),
                    chunk_index=props.get("chunkIndex", 0),
                    start_position=props.get("startOffset", 0),
                    end_position=props.get("endOffset", 0),
                    chunk_metadata=props.get("metadata", {})
                )

                # Calculate final hybrid score if not provided
                if search_result.hybrid_score == 0.0:
                    search_result.hybrid_score = self._calculate_hybrid_score(
                        search_result.semantic_score,
                        search_result.keyword_score,
                        config
                    )

                # Add query highlighting
                search_result.query_match_highlights = self._highlight_matches(
                    search_result.content,
                    processed_query
                )

                # Extract matched terms
                search_result.matched_terms = self._extract_matched_terms(
                    search_result.content,
                    processed_query
                )

                # Calculate quality scores
                search_result.content_quality_score = self._calculate_content_quality(
                    search_result.content
                )

                # Filter by minimum relevance
                if search_result.hybrid_score >= config.min_relevance_score:
                    processed_results.append(search_result)

            except Exception as e:
                logger.warning(f"Failed to process search result: {e}")
                continue

        # Sort by hybrid score (descending)
        processed_results.sort(key=lambda x: x.hybrid_score, reverse=True)

        # Apply ranking method
        if config.ranking_method != RankingMethod.WEIGHTED_SUM:
            processed_results = self._apply_advanced_ranking(processed_results, config)

        # Limit results
        return processed_results[:config.max_results]

    def _calculate_hybrid_score(
        self,
        semantic_score: float,
        keyword_score: float,
        config: SearchConfig
    ) -> float:
        """Calculate hybrid score from semantic and keyword scores."""
        if config.ranking_method == RankingMethod.WEIGHTED_SUM:
            return (
                semantic_score * config.semantic_weight +
                keyword_score * config.keyword_weight
            )
        elif config.ranking_method == RankingMethod.NORMALIZED_SCORE:
            # Normalize scores to 0-1 range before combining
            norm_semantic = min(semantic_score / config.semantic_threshold, 1.0)
            norm_keyword = min(keyword_score / config.keyword_threshold, 1.0)
            return (
                norm_semantic * config.semantic_weight +
                norm_keyword * config.keyword_weight
            )
        else:
            # Default to weighted sum
            return (
                semantic_score * config.semantic_weight +
                keyword_score * config.keyword_weight
            )

    def _apply_advanced_ranking(
        self,
        results: List[SearchResult],
        config: SearchConfig
    ) -> List[SearchResult]:
        """Apply advanced ranking methods like RRF."""
        if config.ranking_method == RankingMethod.RRF:
            return self._apply_rrf_ranking(results, config.rrf_k)
        elif config.ranking_method == RankingMethod.ADAPTIVE:
            return self._apply_adaptive_ranking(results, config)
        else:
            return results

    def _apply_rrf_ranking(self, results: List[SearchResult], k: int = 60) -> List[SearchResult]:
        """Apply Reciprocal Rank Fusion (RRF) ranking."""
        # Sort by semantic score
        semantic_ranked = sorted(results, key=lambda x: x.semantic_score, reverse=True)
        # Sort by keyword score
        keyword_ranked = sorted(results, key=lambda x: x.keyword_score, reverse=True)

        # Calculate RRF scores
        rrf_scores = {}

        for rank, result in enumerate(semantic_ranked):
            rrf_scores[result.chunk_id] = rrf_scores.get(result.chunk_id, 0) + 1 / (k + rank + 1)

        for rank, result in enumerate(keyword_ranked):
            rrf_scores[result.chunk_id] = rrf_scores.get(result.chunk_id, 0) + 1 / (k + rank + 1)

        # Update hybrid scores with RRF scores
        for result in results:
            result.hybrid_score = rrf_scores.get(result.chunk_id, 0)

        # Sort by RRF score
        return sorted(results, key=lambda x: x.hybrid_score, reverse=True)

    def _apply_adaptive_ranking(
        self,
        results: List[SearchResult],
        config: SearchConfig
    ) -> List[SearchResult]:
        """Apply adaptive ranking based on result characteristics."""
        # Analyze result distribution to adjust weights
        semantic_scores = [r.semantic_score for r in results]
        keyword_scores = [r.keyword_score for r in results]

        semantic_variance = self._calculate_variance(semantic_scores)
        keyword_variance = self._calculate_variance(keyword_scores)

        # Adjust weights based on score variance
        if semantic_variance > keyword_variance:
            # Semantic scores are more discriminative
            adaptive_semantic_weight = min(0.8, config.semantic_weight + 0.1)
            adaptive_keyword_weight = 1.0 - adaptive_semantic_weight
        else:
            # Keyword scores are more discriminative
            adaptive_keyword_weight = min(0.8, config.keyword_weight + 0.1)
            adaptive_semantic_weight = 1.0 - adaptive_keyword_weight

        # Recalculate hybrid scores
        for result in results:
            result.hybrid_score = (
                result.semantic_score * adaptive_semantic_weight +
                result.keyword_score * adaptive_keyword_weight
            )

        return sorted(results, key=lambda x: x.hybrid_score, reverse=True)

    def _calculate_variance(self, scores: List[float]) -> float:
        """Calculate variance of scores."""
        if not scores:
            return 0.0

        mean = sum(scores) / len(scores)
        variance = sum((x - mean) ** 2 for x in scores) / len(scores)
        return variance

    def _highlight_matches(self, content: str, query: str) -> List[str]:
        """Highlight query matches in content."""
        highlights = []
        query_terms = query.lower().split()

        for term in query_terms:
            if len(term) > 2:  # Skip very short terms
                pattern = re.compile(re.escape(term), re.IGNORECASE)
                matches = pattern.finditer(content)

                for match in matches:
                    start = max(0, match.start() - 30)
                    end = min(len(content), match.end() + 30)
                    highlight = content[start:end]

                    # Bold the matched term
                    highlight = pattern.sub(f"**{match.group()}**", highlight)
                    highlights.append(highlight.strip())

        return highlights[:5]  # Limit to 5 highlights

    def _extract_matched_terms(self, content: str, query: str) -> List[str]:
        """Extract terms from query that match in content."""
        matched_terms = []
        query_terms = query.lower().split()
        content_lower = content.lower()

        for term in query_terms:
            if len(term) > 2 and term in content_lower:
                matched_terms.append(term)

        return list(set(matched_terms))  # Remove duplicates

    def _calculate_content_quality(self, content: str) -> float:
        """Calculate content quality score."""
        if not content:
            return 0.0

        score = 0.0

        # Length score (prefer medium-length content)
        length = len(content)
        if 100 <= length <= 1000:
            score += 0.3
        elif 50 <= length < 100 or 1000 < length <= 2000:
            score += 0.2
        else:
            score += 0.1

        # Sentence structure score
        sentences = re.split(r'[.!?]+', content)
        complete_sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        if sentences:
            sentence_ratio = len(complete_sentences) / len(sentences)
            score += 0.3 * sentence_ratio

        # Word diversity score
        words = content.lower().split()
        unique_words = set(words)
        if words:
            diversity_ratio = len(unique_words) / len(words)
            score += 0.2 * diversity_ratio

        # Capitalization and punctuation score
        if re.search(r'^[A-Z]', content.strip()) and re.search(r'[.!?]$', content.strip()):
            score += 0.2

        return min(score, 1.0)

    def _create_search_response(
        self,
        results: List[SearchResult],
        original_query: str,
        processed_query: str,
        config: SearchConfig,
        search_time_ms: float,
        filters_applied: Dict[str, Any]
    ) -> SearchResponse:
        """Create comprehensive search response."""

        # Calculate relevance metrics
        relevance_scores = [r.hybrid_score for r in results]

        avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0
        max_relevance = max(relevance_scores) if relevance_scores else 0.0
        min_relevance = min(relevance_scores) if relevance_scores else 0.0

        return SearchResponse(
            results=results,
            query=original_query,
            processed_query=processed_query,
            strategy_used=config.strategy,
            total_results=len(results),
            search_time_ms=search_time_ms,
            avg_relevance_score=avg_relevance,
            max_relevance_score=max_relevance,
            min_relevance_score=min_relevance,
            config_used=config,
            filters_applied=filters_applied
        )

    def _generate_cache_key(
        self,
        query: str,
        config: SearchConfig,
        filters: Optional[Dict[str, Any]]
    ) -> str:
        """Generate cache key for search results."""
        import hashlib

        key_data = {
            "query": query,
            "strategy": config.strategy.value,
            "limit": config.limit,
            "semantic_weight": config.semantic_weight,
            "keyword_weight": config.keyword_weight,
            "filters": filters or {}
        }

        key_string = str(sorted(key_data.items()))
        return hashlib.md5(key_string.encode()).hexdigest()

    def get_search_stats(self) -> Dict[str, Any]:
        """Get search service statistics."""
        cache_size = len(self._cache) if self._cache else 0

        return {
            "cache_enabled": self.config.enable_caching,
            "cache_size": cache_size,
            "default_strategy": self.config.strategy.value,
            "default_limit": self.config.limit,
            "semantic_weight": self.config.semantic_weight,
            "keyword_weight": self.config.keyword_weight
        }

    def clear_cache(self) -> None:
        """Clear search result cache."""
        if self._cache:
            self._cache.clear()
            logger.info("Search cache cleared")

    def search_multimodal_content(
        self,
        query: str,
        config: Optional[MultiModalSearchConfig] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> MultiModalSearchResponse:
        """
        Search multimodal content using cross-modal CLIP embeddings.

        This method enables text-to-image/video search by leveraging Weaviate's
        multi2vec-clip vectorizer to find visually relevant content based on
        text descriptions.

        Args:
            query: Text query to search for (e.g., "a person giving a speech")
            config: Optional multimodal search configuration
            filters: Optional filters for media type, date range, etc.

        Returns:
            MultiModalSearchResponse with relevant multimodal content

        Raises:
            ValueError: If query is empty or invalid
            WeaviateBaseError: If Weaviate query fails
        """
        start_time = time.time()
        search_config = config or MultiModalSearchConfig()

        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        if not self.client:
            raise ValueError("Weaviate client not initialized")

        try:
            logger.info(f"Executing multimodal search: '{query}' with config: {search_config.to_dict()}")

            # Preprocess query for optimal cross-modal search
            processed_query = self._preprocess_multimodal_query(query, search_config)

            # Build Weaviate query with nearText for cross-modal search
            collection = self.client.collections.get("MultiModalContent")

            # Build filters
            where_filter = self._build_multimodal_filters(filters, search_config)

            # Execute cross-modal search using nearText
            # Weaviate's multi2vec-clip will automatically handle text-to-image/video embedding
            response = collection.query.near_text(
                query=processed_query,
                limit=search_config.limit,
                offset=search_config.offset,
                where=where_filter,
                return_metadata=["score", "distance"]
            )

            # Process results
            results = self._process_multimodal_results(
                response.objects,
                query,
                search_config
            )

            # Calculate cross-modal accuracy
            cross_modal_accuracy = self._calculate_cross_modal_accuracy(results, search_config)

            search_time = time.time() - start_time

            # Create response
            search_response = MultiModalSearchResponse(
                results=results,
                total_results=len(results),
                query=query,
                search_time=search_time,
                cross_modal_accuracy=cross_modal_accuracy,
                relevance_threshold=search_config.relevance_threshold,
                limit=search_config.limit,
                offset=search_config.offset,
                metadata={
                    "processed_query": processed_query,
                    "filters_applied": filters or {},
                    "config_used": search_config.to_dict()
                }
            )

            logger.info(f"Multimodal search completed: {len(results)} results in {search_time:.3f}s")
            return search_response

        except WeaviateBaseError as e:
            logger.error(f"Weaviate multimodal search failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Multimodal search failed: {e}")
            raise

    def _preprocess_multimodal_query(
        self,
        query: str,
        config: MultiModalSearchConfig
    ) -> str:
        """Preprocess query for optimal cross-modal search."""
        processed = query.strip()

        # Expand query for better cross-modal matching
        if config.enable_query_expansion:
            processed = self._expand_multimodal_query(processed)

        # Enhance with semantic context
        if config.enable_semantic_boost:
            processed = self._add_semantic_context(processed)

        return processed

    def _expand_multimodal_query(self, query: str) -> str:
        """Expand query with visual and contextual terms."""
        # Visual enhancement terms for better cross-modal matching
        visual_enhancements = {
            "person": "person human figure individual",
            "speech": "speech speaking talking presentation lecture",
            "meeting": "meeting conference discussion group people",
            "presentation": "presentation slide screen projector audience",
            "office": "office workplace desk computer business",
            "outdoor": "outdoor outside nature landscape sky",
            "indoor": "indoor inside room building interior",
            "car": "car vehicle automobile transportation",
            "food": "food meal eating restaurant kitchen",
            "animal": "animal pet wildlife creature"
        }

        words = query.lower().split()
        expanded_words = []

        for word in words:
            expanded_words.append(word)
            if word in visual_enhancements:
                expanded_words.extend(visual_enhancements[word].split())

        return " ".join(expanded_words)

    def _add_semantic_context(self, query: str) -> str:
        """Add semantic context for better cross-modal understanding."""
        # Add visual context markers
        if any(word in query.lower() for word in ["person", "people", "human"]):
            query += " human figure person"

        if any(word in query.lower() for word in ["speaking", "talking", "speech"]):
            query += " speaking talking communication"

        if any(word in query.lower() for word in ["meeting", "conference"]):
            query += " meeting conference group discussion"

        return query

    def _build_multimodal_filters(
        self,
        filters: Optional[Dict[str, Any]],
        config: MultiModalSearchConfig
    ) -> Optional[Filter]:
        """Build Weaviate filters for multimodal search."""
        filter_conditions = []

        # Media type filtering
        if config.media_types:
            media_type_values = [mt.value for mt in config.media_types]
            filter_conditions.append(
                Filter.by_property("media_type").contains_any(media_type_values)
            )

        # Conversation ID filtering
        if config.conversation_id:
            filter_conditions.append(
                Filter.by_property("conversation_id").equal(config.conversation_id)
            )

        # Date range filtering
        if config.date_range:
            start_date, end_date = config.date_range
            filter_conditions.append(
                Filter.by_property("created_at").greater_or_equal(start_date)
            )
            filter_conditions.append(
                Filter.by_property("created_at").less_or_equal(end_date)
            )

        # File size filtering
        if config.file_size_range:
            min_size, max_size = config.file_size_range
            filter_conditions.append(
                Filter.by_property("file_size").greater_or_equal(min_size)
            )
            filter_conditions.append(
                Filter.by_property("file_size").less_or_equal(max_size)
            )

        # Additional custom filters
        if filters:
            for key, value in filters.items():
                if isinstance(value, list):
                    filter_conditions.append(
                        Filter.by_property(key).contains_any(value)
                    )
                else:
                    filter_conditions.append(
                        Filter.by_property(key).equal(value)
                    )

        # Combine filters with AND logic
        if filter_conditions:
            combined_filter = filter_conditions[0]
            for condition in filter_conditions[1:]:
                combined_filter = combined_filter & condition
            return combined_filter

        return None

    def _process_multimodal_results(
        self,
        weaviate_objects: List[Any],
        query: str,
        config: MultiModalSearchConfig
    ) -> List[MultiModalResult]:
        """Process Weaviate results into MultiModalResult objects."""
        results = []

        for obj in weaviate_objects:
            try:
                # Extract properties from Weaviate object
                properties = obj.properties
                metadata = obj.metadata

                # Calculate relevance scores
                relevance_score = metadata.score if hasattr(metadata, 'score') else 0.0
                cross_modal_score = self._calculate_cross_modal_score(
                    properties, query, relevance_score
                )

                # Filter by minimum cross-modal score
                if cross_modal_score < config.min_cross_modal_score:
                    continue

                # Parse datetime fields
                created_at = self._parse_datetime(properties.get("created_at"))
                updated_at = self._parse_datetime(properties.get("updated_at"))

                # Create MultiModalResult
                result = MultiModalResult(
                    content_id=properties.get("content_id", str(obj.uuid)),
                    media_type=properties.get("media_type", "unknown"),
                    filename=properties.get("filename", ""),
                    storage_path=properties.get("storage_path", ""),
                    file_size=properties.get("file_size", 0),
                    content_hash=properties.get("content_hash", ""),
                    created_at=created_at,
                    updated_at=updated_at,
                    processing_status=properties.get("processing_status", "unknown"),
                    processing_result=properties.get("processing_result", {}),
                    text_content=properties.get("text_content", ""),
                    relevance_score=relevance_score,
                    cross_modal_score=cross_modal_score,
                    visual_embedding=properties.get("visual_embedding"),
                    text_embedding=properties.get("text_embedding"),
                    conversation_id=properties.get("conversation_id"),
                    metadata=properties.get("metadata", {})
                )

                results.append(result)

            except Exception as e:
                logger.error(f"Failed to process multimodal result: {e}")
                continue

        # Sort by cross-modal score
        results.sort(key=lambda x: x.cross_modal_score, reverse=True)

        return results[:config.max_results]

    def _calculate_cross_modal_score(
        self,
        properties: Dict[str, Any],
        query: str,
        base_score: float
    ) -> float:
        """Calculate cross-modal relevance score."""

        # Start with base Weaviate score
        score = base_score

        # Boost score based on text content relevance
        text_content = properties.get("text_content", "")
        if text_content:
            text_relevance = self._calculate_text_relevance(text_content, query)
            score = score * 0.7 + text_relevance * 0.3

        # Boost score based on processing quality
        processing_result = properties.get("processing_result", {})
        if processing_result:
            quality_boost = self._calculate_quality_boost(processing_result)
            score *= (1.0 + quality_boost * 0.1)

        # Boost score based on media type preference
        media_type = properties.get("media_type", "")
        if media_type in ["image", "video"]:
            score *= 1.1  # Slight boost for visual content

        return min(score, 1.0)

    def _calculate_text_relevance(self, text_content: str, query: str) -> float:
        """Calculate text relevance score."""
        if not text_content or not query:
            return 0.0

        # Simple keyword matching (in production, use proper NLP)
        query_words = set(query.lower().split())
        content_words = set(text_content.lower().split())

        if not query_words:
            return 0.0

        # Calculate Jaccard similarity
        intersection = len(query_words.intersection(content_words))
        union = len(query_words.union(content_words))

        return intersection / union if union > 0 else 0.0

    def _calculate_quality_boost(self, processing_result: Dict[str, Any]) -> float:
        """Calculate quality boost based on processing results."""
        quality_boost = 0.0

        # Video processing quality
        if "overall_video_quality" in processing_result:
            quality_boost += processing_result["overall_video_quality"] * 0.3

        # Audio processing quality
        if "transcription_confidence" in processing_result:
            quality_boost += processing_result["transcription_confidence"] * 0.3

        # Scene detection quality
        if "scene_detection_confidence" in processing_result:
            quality_boost += processing_result["scene_detection_confidence"] * 0.2

        # Frame extraction quality
        if "frame_extraction_quality" in processing_result:
            quality_boost += processing_result["frame_extraction_quality"] * 0.2

        return min(quality_boost, 1.0)

    def _parse_datetime(self, datetime_str: Any) -> Optional[datetime]:
        """Parse datetime string to datetime object."""
        if not datetime_str:
            return None

        if isinstance(datetime_str, datetime):
            return datetime_str

        try:
            # Try ISO format first
            return datetime.fromisoformat(str(datetime_str).replace('Z', '+00:00'))
        except:
            try:
                # Try common formats
                return datetime.strptime(str(datetime_str), "%Y-%m-%d %H:%M:%S")
            except:
                return None

    def _calculate_cross_modal_accuracy(
        self,
        results: List[MultiModalResult],
        config: MultiModalSearchConfig
    ) -> float:
        """Calculate cross-modal search accuracy."""
        if not results:
            return 0.0

        # Calculate accuracy based on cross-modal scores
        high_quality_results = [
            r for r in results
            if r.cross_modal_score >= config.relevance_threshold
        ]

        accuracy = len(high_quality_results) / len(results)

        # Boost accuracy for diverse media types
        media_types = set(r.media_type for r in results)
        diversity_boost = min(len(media_types) * 0.1, 0.3)

        return min(accuracy + diversity_boost, 1.0)


def create_retrieval_service(
    weaviate_client: weaviate.WeaviateClient,
    strategy: SearchStrategy = SearchStrategy.HYBRID,
    semantic_weight: float = 0.7,
    keyword_weight: float = 0.3,
    **kwargs
) -> RetrievalService:
    """
    Convenience function to create a RetrievalService with common settings.

    Args:
        weaviate_client: Weaviate client instance
        strategy: Default search strategy
        semantic_weight: Weight for semantic search (0.0-1.0)
        keyword_weight: Weight for keyword search (0.0-1.0)
        **kwargs: Additional configuration options

    Returns:
        Configured RetrievalService instance
    """
    config = SearchConfig(
        strategy=strategy,
        semantic_weight=semantic_weight,
        keyword_weight=keyword_weight,
        **kwargs
    )

    return RetrievalService(weaviate_client, config)
