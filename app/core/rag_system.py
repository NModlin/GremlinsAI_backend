# app/core/rag_system.py
"""
Production-Ready RAG System Implementation
Phase 2, Task 2.3: RAG System Implementation

This module implements the ProductionRAGSystem as specified in prometheus.md,
providing a complete five-step RAG pipeline with Weaviate integration,
citations, confidence scoring, and sub-2-second response times.
"""

import logging
import time
import asyncio
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

import requests
import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import get_settings
from app.core.llm_manager import ProductionLLMManager
from app.core.logging_config import get_logger, log_performance, log_security_event
from app.core.tracing_service import tracing_service
from app.core.metrics_service import metrics_service

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class RAGResponse:
    """Structured RAG response with citations and confidence scoring."""
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float
    query_time_ms: float
    context_used: bool
    search_metadata: Dict[str, Any]
    timestamp: str


@dataclass
class DocumentSource:
    """Document source with citation information."""
    document_id: str
    title: str
    content: str
    score: float
    chunk_index: int
    metadata: Dict[str, Any]

class ProductionRAGSystem:
    """
    Production-ready RAG system implementing the five-step pipeline from prometheus.md:
    1. Generate query embedding
    2. Retrieve relevant chunks from Weaviate
    3. Construct context-aware prompt
    4. Generate response with LLM
    5. Add citations and confidence scoring
    """

    def __init__(self):
        """Initialize the production RAG system."""
        self.settings = get_settings()
        self.embedder = None
        self.llm_manager = None
        self.weaviate_headers = {}

        # Setup Weaviate authentication
        if self.settings.weaviate_api_key:
            self.weaviate_headers['Authorization'] = f'Bearer {self.settings.weaviate_api_key}'

        logger.info("ProductionRAGSystem initialized")

    async def _initialize_models(self):
        """Lazy initialization of models to avoid startup delays."""
        if self.embedder is None:
            logger.info("Loading SentenceTransformer model...")
            self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("SentenceTransformer model loaded")

        if self.llm_manager is None:
            logger.info("Initializing ProductionLLMManager...")
            self.llm_manager = ProductionLLMManager()
            logger.info("ProductionLLMManager initialized")

    async def generate_response(
        self,
        query: str,
        context_limit: int = 5,
        certainty_threshold: float = 0.7,
        conversation_id: Optional[str] = None
    ) -> RAGResponse:
        """
        Generate a RAG response following the five-step pipeline.

        Args:
            query: User query string
            context_limit: Maximum number of document chunks to retrieve
            certainty_threshold: Minimum certainty score for Weaviate results
            conversation_id: Optional conversation ID for context

        Returns:
            RAGResponse with answer, sources, and confidence score
        """
        start_time = time.time()

        try:
            with tracing_service.trace_rag_query("generate_response", context_limit) as span:
                span.set_attribute("rag.query_length", len(query))
                span.set_attribute("rag.context_limit", context_limit)
                span.set_attribute("rag.certainty_threshold", certainty_threshold)
                # Initialize models if needed
                await self._initialize_models()

                logger.info(f"Starting RAG pipeline for query: {query[:100]}...")

                # Step 1: Generate query embedding
                with tracing_service.trace_operation("rag.generate_embedding") as embed_span:
                    query_vector = await self._generate_query_embedding(query)
                    embed_span.set_attribute("embedding.vector_length", len(query_vector))

                # Step 2: Retrieve relevant chunks from Weaviate
                with tracing_service.trace_weaviate_query("search", "DocumentChunk") as weaviate_span:
                    retrieved_chunks = await self._retrieve_from_weaviate(
                        query_vector, context_limit, certainty_threshold
                    )
                    weaviate_span.set_attribute("weaviate.chunks_retrieved", len(retrieved_chunks))

                # Step 3: Construct context-aware prompt
                context = self._build_context(retrieved_chunks)
                prompt = self._build_rag_prompt(query, context)

                # Step 4: Generate response with LLM
                with tracing_service.trace_llm_request("local", "default") as llm_span:
                    llm_response = await self._generate_llm_response(prompt)
                    llm_span.set_attribute("llm.prompt_length", len(prompt))
                    llm_span.set_attribute("llm.response_length", len(llm_response))

                # Step 5: Add citations and confidence scoring
                sources = self._extract_sources(retrieved_chunks)
                confidence = self._calculate_confidence(retrieved_chunks, llm_response)

                query_time_ms = (time.time() - start_time) * 1000

                # Record metrics
                metrics_service.record_rag_query(
                    query_type="generate_response",
                    status="success",
                    duration=query_time_ms / 1000,
                    similarity_score=confidence
                )

                # Add tracing attributes
                span.set_attribute("rag.sources_count", len(sources))
                span.set_attribute("rag.confidence_score", confidence)
                span.set_attribute("rag.response_time_ms", query_time_ms)

                # Log performance
                log_performance(
                    operation="rag_generate_response",
                    duration_ms=query_time_ms,
                    success=True,
                    context_chunks=len(retrieved_chunks),
                    confidence=confidence,
                    conversation_id=conversation_id
                )

                response = RAGResponse(
                    answer=llm_response,
                    sources=sources,
                    confidence=confidence,
                    query_time_ms=query_time_ms,
                    context_used=len(retrieved_chunks) > 0,
                    search_metadata={
                        "total_chunks": len(retrieved_chunks),
                        "certainty_threshold": certainty_threshold,
                        "context_limit": context_limit,
                        "embedding_model": "all-MiniLM-L6-v2"
                    },
                    timestamp=datetime.utcnow().isoformat()
                )

                logger.info(f"RAG response generated successfully in {query_time_ms:.2f}ms")
                return response

        except Exception as e:
            query_time_ms = (time.time() - start_time) * 1000
            logger.error(f"RAG generation failed: {e}")

            # Record error metrics
            metrics_service.record_rag_query(
                query_type="generate_response",
                status="error",
                duration=query_time_ms / 1000
            )

            # Log security event for RAG failures
            log_security_event(
                event_type="rag_generation_failure",
                severity="medium",
                query=query[:100],
                error=str(e),
                conversation_id=conversation_id
            )

            # Return error response
            return RAGResponse(
                answer="I encountered an error while processing your request. Please try again.",
                sources=[],
                confidence=0.0,
                query_time_ms=query_time_ms,
                context_used=False,
                search_metadata={"error": str(e)},
                timestamp=datetime.utcnow().isoformat()
            )

    async def _generate_query_embedding(self, query: str) -> List[float]:
        """Step 1: Generate vector embedding for the query."""
        try:
            # Generate embedding using SentenceTransformer
            embedding = self.embedder.encode(query, convert_to_tensor=False)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            raise

    async def _retrieve_from_weaviate(
        self,
        query_vector: List[float],
        limit: int,
        certainty_threshold: float
    ) -> List[DocumentSource]:
        """Step 2: Retrieve relevant chunks from Weaviate using near_vector search."""
        try:
            # Construct GraphQL query for Weaviate
            graphql_query = {
                "query": f"""
                {{
                    Get {{
                        DocumentChunk(
                            limit: {limit}
                            nearVector: {{
                                vector: {json.dumps(query_vector)}
                                certainty: {certainty_threshold}
                            }}
                        ) {{
                            content
                            document_title
                            chunk_index
                            metadata
                            _additional {{
                                certainty
                                id
                            }}
                        }}
                    }}
                }}
                """
            }

            # Execute query against Weaviate
            response = requests.post(
                f"{self.settings.weaviate_url}/v1/graphql",
                headers={**self.weaviate_headers, 'Content-Type': 'application/json'},
                json=graphql_query,
                timeout=10
            )

            if response.status_code != 200:
                logger.error(f"Weaviate query failed: {response.status_code} - {response.text}")
                return []

            data = response.json()
            chunks = data.get('data', {}).get('Get', {}).get('DocumentChunk', [])

            # Convert to DocumentSource objects
            document_sources = []
            for chunk in chunks:
                additional = chunk.get('_additional', {})
                document_sources.append(DocumentSource(
                    document_id=additional.get('id', ''),
                    title=chunk.get('document_title', 'Unknown Document'),
                    content=chunk.get('content', ''),
                    score=additional.get('certainty', 0.0),
                    chunk_index=chunk.get('chunk_index', 0),
                    metadata=chunk.get('metadata', {})
                ))

            logger.info(f"Retrieved {len(document_sources)} chunks from Weaviate")
            return document_sources

        except Exception as e:
            logger.error(f"Failed to retrieve from Weaviate: {e}")
            return []

    def _build_context(self, retrieved_chunks: List[DocumentSource]) -> str:
        """Step 3: Build context string from retrieved document chunks."""
        if not retrieved_chunks:
            return ""

        context_parts = []
        for i, chunk in enumerate(retrieved_chunks):
            context_part = f"[Document {i+1}: {chunk.title}]\n{chunk.content}\n"
            context_parts.append(context_part)

        return "\n---\n".join(context_parts)

    def _build_rag_prompt(self, query: str, context: str) -> str:
        """Step 3: Construct context-aware prompt for LLM."""
        if not context:
            return f"""Please answer the following question: {query}

Note: No specific context documents are available, so please provide a general response based on your knowledge."""

        return f"""Please answer the following question based on the provided context documents.

Context Documents:
{context}

Question: {query}

Instructions:
1. Use only the information provided in the context documents
2. If the context doesn't contain enough information to answer the question, say so clearly
3. Cite specific documents when referencing information (e.g., "According to Document 1...")
4. Provide a clear, comprehensive answer
5. Be accurate and don't make up information not present in the context

Answer:"""

    async def _generate_llm_response(self, prompt: str) -> str:
        """Step 4: Generate response using ProductionLLMManager."""
        try:
            # Use the ProductionLLMManager to generate response
            response = await self.llm_manager.generate_response(
                prompt=prompt,
                max_tokens=512,
                temperature=0.1,  # Low temperature for factual responses
                system_message="You are a helpful assistant that provides accurate, well-cited responses based on provided context."
            )

            return response.get("content", "I couldn't generate a response.")

        except Exception as e:
            logger.error(f"LLM response generation failed: {e}")
            return "I encountered an error while generating the response. Please try again."

    def _extract_sources(self, retrieved_chunks: List[DocumentSource]) -> List[Dict[str, Any]]:
        """Step 5: Extract source information for citations."""
        sources = []
        for chunk in retrieved_chunks:
            sources.append({
                "document_id": chunk.document_id,
                "title": chunk.title,
                "score": chunk.score,
                "chunk_index": chunk.chunk_index,
                "content_preview": chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
                "metadata": chunk.metadata
            })
        return sources

    def _calculate_confidence(self, retrieved_chunks: List[DocumentSource], llm_response: str) -> float:
        """Step 5: Calculate confidence score based on retrieval quality and response."""
        if not retrieved_chunks:
            return 0.0

        # Base confidence on average retrieval scores
        avg_score = sum(chunk.score for chunk in retrieved_chunks) / len(retrieved_chunks)

        # Adjust confidence based on response quality indicators
        response_quality_score = 1.0

        # Lower confidence if response indicates uncertainty
        uncertainty_phrases = [
            "i don't know", "not sure", "unclear", "insufficient information",
            "cannot determine", "not enough context", "unable to answer"
        ]

        response_lower = llm_response.lower()
        for phrase in uncertainty_phrases:
            if phrase in response_lower:
                response_quality_score *= 0.7
                break

        # Higher confidence if response includes citations
        if "document" in response_lower and ("according to" in response_lower or "based on" in response_lower):
            response_quality_score *= 1.1

        # Final confidence calculation
        confidence = min(avg_score * response_quality_score, 1.0)
        return round(confidence, 3)


# Global RAG system instance
production_rag_system = ProductionRAGSystem()
