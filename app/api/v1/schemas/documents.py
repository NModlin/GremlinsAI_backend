# app/api/v1/schemas/documents.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class SearchType(str, Enum):
    """Available search types for semantic search."""
    CHUNKS = "chunks"
    DOCUMENTS = "documents"
    BOTH = "both"

class DocumentCreate(BaseModel):
    """Schema for creating a new document."""
    title: str = Field(..., min_length=1, max_length=500, description="Document title")
    content: str = Field(..., min_length=1, description="Document content")
    content_type: str = Field(default="text/plain", description="MIME type of the content")
    doc_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")
    chunk_size: int = Field(default=1000, ge=100, le=5000, description="Size of text chunks")
    chunk_overlap: int = Field(default=200, ge=0, le=1000, description="Overlap between chunks")

class DocumentResponse(BaseModel):
    """Schema for document responses."""
    id: str = Field(..., description="Document ID")
    title: str = Field(..., description="Document title")
    content: str = Field(..., description="Document content")
    content_type: str = Field(..., description="MIME type")
    file_path: Optional[str] = Field(None, description="Original file path")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    vector_id: Optional[str] = Field(None, description="Vector store ID")
    embedding_model: Optional[str] = Field(None, description="Embedding model used")
    doc_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    tags: Optional[List[str]] = Field(None, description="Document tags")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    is_active: bool = Field(..., description="Whether document is active")

class DocumentListResponse(BaseModel):
    """Schema for document list responses."""
    documents: List[DocumentResponse] = Field(..., description="List of documents")
    total: int = Field(..., description="Total number of documents")
    limit: int = Field(..., description="Limit used for pagination")
    offset: int = Field(..., description="Offset used for pagination")

class SemanticSearchRequest(BaseModel):
    """Schema for semantic search requests."""
    query: str = Field(..., min_length=1, description="Search query")
    limit: int = Field(default=5, ge=1, le=50, description="Maximum number of results")
    score_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum similarity score")
    search_type: SearchType = Field(default=SearchType.CHUNKS, description="Type of search to perform")
    filter_conditions: Optional[Dict[str, Any]] = Field(None, description="Additional filter conditions")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")

class SearchResult(BaseModel):
    """Schema for individual search results."""
    id: str = Field(..., description="Result ID")
    score: float = Field(..., description="Similarity score")
    content: str = Field(..., description="Content snippet")
    document_id: str = Field(..., description="Source document ID")
    document_title: str = Field(..., description="Source document title")
    document_type: str = Field(..., description="Document content type")
    chunk_index: Optional[int] = Field(None, description="Chunk index if applicable")
    metadata: Dict[str, Any] = Field(..., description="Additional metadata")

class SemanticSearchResponse(BaseModel):
    """Schema for semantic search responses."""
    query: str = Field(..., description="Original search query")
    results: List[SearchResult] = Field(..., description="Search results")
    total_found: int = Field(..., description="Total number of results found")
    search_query_id: Optional[str] = Field(None, description="ID of the search query record")
    execution_time_ms: Optional[float] = Field(None, description="Search execution time")

class RAGRequest(BaseModel):
    """Schema for RAG (Retrieval-Augmented Generation) requests."""
    query: str = Field(..., min_length=1, description="User query")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")
    search_limit: Optional[int] = Field(5, ge=1, le=20, description="Number of documents to retrieve")
    score_threshold: Optional[float] = Field(0.7, ge=0.0, le=1.0, description="Minimum similarity score")
    filter_conditions: Optional[Dict[str, Any]] = Field(None, description="Search filter conditions")
    use_multi_agent: bool = Field(False, description="Whether to use multi-agent system")
    search_type: SearchType = Field(default=SearchType.CHUNKS, description="Type of search to perform")
    save_conversation: bool = Field(True, description="Whether to save to conversation history")

class RAGResponse(BaseModel):
    """Schema for RAG responses."""
    query: str = Field(..., description="Original user query")
    response: str = Field(..., description="Generated response")
    retrieved_documents: List[SearchResult] = Field(..., description="Documents used for context")
    context_used: bool = Field(..., description="Whether retrieved context was used")
    search_metadata: Dict[str, Any] = Field(..., description="Search operation metadata")
    agent_metadata: Dict[str, Any] = Field(..., description="Agent processing metadata")
    conversation_id: Optional[str] = Field(None, description="Conversation ID if saved")
    timestamp: str = Field(..., description="Response timestamp")

class DocumentUploadResponse(BaseModel):
    """Schema for document upload responses."""
    document_id: str = Field(..., description="ID of the created document")
    title: str = Field(..., description="Document title")
    file_size: int = Field(..., description="File size in bytes")
    chunks_created: int = Field(..., description="Number of chunks created")
    vector_ids: List[str] = Field(..., description="Vector store IDs")
    processing_time_ms: float = Field(..., description="Processing time")

class SystemStatusResponse(BaseModel):
    """Schema for RAG system status responses."""
    status: str = Field(..., description="System status")
    total_documents: int = Field(..., description="Total number of documents")
    vector_store: Dict[str, Any] = Field(..., description="Vector store information")
    search_analytics: Dict[str, Any] = Field(..., description="Search analytics")
    configuration: Dict[str, Any] = Field(..., description="System configuration")

class QuerySuggestionsRequest(BaseModel):
    """Schema for query suggestion requests."""
    query: str = Field(..., min_length=1, description="Base query for suggestions")
    limit: int = Field(default=5, ge=1, le=10, description="Number of suggestions to return")

class QuerySuggestionsResponse(BaseModel):
    """Schema for query suggestion responses."""
    original_query: str = Field(..., description="Original query")
    suggestions: List[str] = Field(..., description="Suggested related queries")
    total_suggestions: int = Field(..., description="Total number of suggestions generated")

class DocumentChunkResponse(BaseModel):
    """Schema for document chunk responses."""
    id: str = Field(..., description="Chunk ID")
    document_id: str = Field(..., description="Parent document ID")
    content: str = Field(..., description="Chunk content")
    chunk_index: int = Field(..., description="Chunk index in document")
    chunk_size: int = Field(..., description="Chunk size in characters")
    vector_id: Optional[str] = Field(None, description="Vector store ID")
    start_position: Optional[int] = Field(None, description="Start position in document")
    end_position: Optional[int] = Field(None, description="End position in document")
    chunk_metadata: Optional[Dict[str, Any]] = Field(None, description="Chunk metadata")
    created_at: datetime = Field(..., description="Creation timestamp")

class SearchAnalyticsResponse(BaseModel):
    """Schema for search analytics responses."""
    total_searches: int = Field(..., description="Total number of searches")
    avg_execution_time_ms: float = Field(..., description="Average execution time")
    avg_results_per_search: float = Field(..., description="Average results per search")
    popular_queries: List[List] = Field(..., description="Most popular queries")
    vector_store_info: Dict[str, Any] = Field(..., description="Vector store information")

# Error schemas
class DocumentError(BaseModel):
    """Schema for document-related errors."""
    error_type: str = Field(..., description="Type of error")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")

class ValidationError(BaseModel):
    """Schema for validation errors."""
    field: str = Field(..., description="Field that failed validation")
    message: str = Field(..., description="Validation error message")
    value: Any = Field(..., description="Invalid value")
