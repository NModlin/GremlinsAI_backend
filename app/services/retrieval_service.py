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
        
        logger.info(f"RetrievalService initialized with strategy: {self.config.strategy.value}")
    
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
        """Execute semantic vector search."""
        try:
            collection = self.client.collections.get("DocumentChunk")

            # Build where filter
            where_filter = self._build_where_filter(config, filters)

            # Execute semantic search
            response = collection.query.near_text(
                query=query,
                limit=config.limit,
                offset=config.offset,
                where=where_filter,
                return_metadata=["score", "distance"]
            )

            # Convert to standard format
            results = []
            for obj in response.objects:
                result = {
                    "chunk_id": obj.uuid,
                    "properties": obj.properties,
                    "metadata": obj.metadata,
                    "semantic_score": 1.0 - (obj.metadata.distance or 0.0),
                    "keyword_score": 0.0,
                    "search_type": "semantic"
                }
                results.append(result)

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

    def _build_where_filter(
        self,
        config: SearchConfig,
        additional_filters: Optional[Dict[str, Any]] = None
    ) -> Optional[Filter]:
        """Build Weaviate where filter from configuration and additional filters."""
        filters = []

        # Add document filters
        if config.document_filters:
            for field, value in config.document_filters.items():
                if isinstance(value, list):
                    filters.append(Filter.by_property(field).contains_any(value))
                else:
                    filters.append(Filter.by_property(field).equal(value))

        # Add chunk filters
        if config.chunk_filters:
            for field, value in config.chunk_filters.items():
                if isinstance(value, list):
                    filters.append(Filter.by_property(field).contains_any(value))
                else:
                    filters.append(Filter.by_property(field).equal(value))

        # Add additional filters
        if additional_filters:
            for field, value in additional_filters.items():
                if isinstance(value, list):
                    filters.append(Filter.by_property(field).contains_any(value))
                else:
                    filters.append(Filter.by_property(field).equal(value))

        # Combine filters with AND
        if len(filters) == 0:
            return None
        elif len(filters) == 1:
            return filters[0]
        else:
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
