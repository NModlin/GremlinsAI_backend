# app/api/v1/endpoints/documents.py
import logging
import time
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.database.database import get_db
from app.services.document_service import DocumentService
from app.core.rag_system import rag_system
from app.api.v1.schemas.documents import (
    DocumentCreate,
    DocumentResponse,
    DocumentListResponse,
    SemanticSearchRequest,
    SemanticSearchResponse,
    RAGRequest,
    RAGResponse,
    DocumentUploadResponse,
    SystemStatusResponse,
    QuerySuggestionsRequest,
    QuerySuggestionsResponse,
    SearchAnalyticsResponse,
    SearchResult
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/", response_model=DocumentResponse)
async def create_document(
    request: DocumentCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new document with automatic chunking and vector storage."""
    try:
        document = await DocumentService.create_document(
            db=db,
            title=request.title,
            content=request.content,
            content_type=request.content_type,
            doc_metadata=request.doc_metadata,
            tags=request.tags,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap
        )
        
        if not document:
            raise HTTPException(status_code=500, detail="Failed to create document")
        
        return DocumentResponse(
            id=document.id,
            title=document.title,
            content=document.content,
            content_type=document.content_type,
            file_path=document.file_path,
            file_size=document.file_size,
            vector_id=document.vector_id,
            embedding_model=document.embedding_model,
            doc_metadata=document.doc_metadata,
            tags=document.tags,
            created_at=document.created_at,
            updated_at=document.updated_at,
            is_active=document.is_active
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating document: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create document: {str(e)}")

@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    limit: int = 50,
    offset: int = 0,
    tags: Optional[str] = None,
    content_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List documents with optional filtering."""
    try:
        # Parse tags if provided
        tag_list = tags.split(",") if tags else None
        
        documents, total = await DocumentService.list_documents(
            db=db,
            limit=limit,
            offset=offset,
            tags=tag_list,
            content_type=content_type
        )
        
        document_responses = [
            DocumentResponse(
                id=doc.id,
                title=doc.title,
                content=doc.content,
                content_type=doc.content_type,
                file_path=doc.file_path,
                file_size=doc.file_size,
                vector_id=doc.vector_id,
                embedding_model=doc.embedding_model,
                doc_metadata=doc.doc_metadata,
                tags=doc.tags,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
                is_active=doc.is_active
            )
            for doc in documents
        ]
        
        return DocumentListResponse(
            documents=document_responses,
            total=total,
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific document by ID."""
    try:
        document = await DocumentService.get_document(db=db, document_id=document_id)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return DocumentResponse(
            id=document.id,
            title=document.title,
            content=document.content,
            content_type=document.content_type,
            file_path=document.file_path,
            file_size=document.file_size,
            vector_id=document.vector_id,
            embedding_model=document.embedding_model,
            doc_metadata=document.doc_metadata,
            tags=document.tags,
            created_at=document.created_at,
            updated_at=document.updated_at,
            is_active=document.is_active
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get document: {str(e)}")

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    soft_delete: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """Delete a document."""
    try:
        success = await DocumentService.delete_document(
            db=db,
            document_id=document_id,
            soft_delete=soft_delete
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {"message": f"Document {document_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

@router.post("/search", response_model=SemanticSearchResponse)
async def semantic_search(
    request: SemanticSearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """Perform semantic search across documents."""
    try:
        start_time = time.time()
        
        results, search_query_id = await DocumentService.semantic_search(
            db=db,
            query=request.query,
            limit=request.limit,
            score_threshold=request.score_threshold,
            filter_conditions=request.filter_conditions,
            search_type=request.search_type.value,
            conversation_id=request.conversation_id
        )
        
        execution_time = (time.time() - start_time) * 1000
        
        search_results = [
            SearchResult(
                id=result["id"],
                score=result["score"],
                content=result["content"],
                document_id=result["document_id"],
                document_title=result["document_title"],
                document_type=result["document_type"],
                chunk_index=result.get("chunk_index"),
                metadata=result["metadata"]
            )
            for result in results
        ]
        
        return SemanticSearchResponse(
            query=request.query,
            results=search_results,
            total_found=len(search_results),
            search_query_id=search_query_id,
            execution_time_ms=execution_time
        )
        
    except Exception as e:
        logger.error(f"Error in semantic search: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.post("/rag", response_model=RAGResponse)
async def rag_query(
    request: RAGRequest,
    db: AsyncSession = Depends(get_db)
):
    """Perform Retrieval-Augmented Generation query."""
    try:
        rag_response = await rag_system.retrieve_and_generate(
            db=db,
            query=request.query,
            conversation_id=request.conversation_id,
            search_limit=request.search_limit,
            score_threshold=request.score_threshold,
            filter_conditions=request.filter_conditions,
            use_multi_agent=request.use_multi_agent,
            search_type=request.search_type.value
        )
        
        # Convert retrieved documents to SearchResult format
        search_results = [
            SearchResult(
                id=doc["id"],
                score=doc["score"],
                content=doc["content"],
                document_id=doc["document_id"],
                document_title=doc["document_title"],
                document_type=doc["document_type"],
                chunk_index=doc.get("chunk_index"),
                metadata=doc["metadata"]
            )
            for doc in rag_response.get("retrieved_documents", [])
        ]
        
        # Save to conversation if requested
        conversation_id = None
        if request.save_conversation and request.conversation_id:
            conversation_id = request.conversation_id
            # TODO: Save RAG interaction to conversation history
        
        return RAGResponse(
            query=rag_response["query"],
            response=rag_response["response"],
            retrieved_documents=search_results,
            context_used=rag_response["context_used"],
            search_metadata=rag_response.get("search_metadata", {}),
            agent_metadata=rag_response.get("agent_metadata", {}),
            conversation_id=conversation_id,
            timestamp=rag_response["timestamp"]
        )
        
    except Exception as e:
        logger.error(f"Error in RAG query: {e}")
        raise HTTPException(status_code=500, detail=f"RAG query failed: {str(e)}")

@router.get("/system/status", response_model=SystemStatusResponse)
async def get_system_status(db: AsyncSession = Depends(get_db)):
    """Get the status of the RAG system."""
    try:
        status = await rag_system.get_system_status(db)
        return SystemStatusResponse(**status)
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get system status: {str(e)}")

@router.post("/suggestions", response_model=QuerySuggestionsResponse)
async def get_query_suggestions(
    request: QuerySuggestionsRequest,
    db: AsyncSession = Depends(get_db)
):
    """Get query suggestions based on document content."""
    try:
        suggestions = await rag_system.suggest_related_queries(
            db=db,
            query=request.query,
            limit=request.limit
        )
        
        return QuerySuggestionsResponse(
            original_query=request.query,
            suggestions=suggestions,
            total_suggestions=len(suggestions)
        )
        
    except Exception as e:
        logger.error(f"Error getting query suggestions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {str(e)}")

@router.get("/analytics/search", response_model=SearchAnalyticsResponse)
async def get_search_analytics(
    days_back: int = 7,
    db: AsyncSession = Depends(get_db)
):
    """Get search analytics and insights."""
    try:
        analytics = await DocumentService.get_search_analytics(db, days_back=days_back)
        return SearchAnalyticsResponse(**analytics)
        
    except Exception as e:
        logger.error(f"Error getting search analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")
