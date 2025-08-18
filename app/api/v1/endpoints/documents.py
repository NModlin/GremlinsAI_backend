# app/api/v1/endpoints/documents.py
import logging
import time
import json
import os
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.database.database import get_db
from app.services.document_service import DocumentService
from app.core.rag_system import production_rag_system
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

# Import sanitize_filename from security module for consistent sanitization
from app.core.security import sanitize_filename

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(None),
    chunking_config: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a document file for asynchronous processing.

    Returns 202 Accepted with a job ID for tracking processing status.
    The document will be intelligently chunked, embedded, and indexed in Weaviate.
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")

        # Sanitize filename to prevent path traversal attacks
        sanitized_filename = sanitize_filename(file.filename)

        # Parse metadata if provided
        parsed_metadata = {}
        if metadata:
            try:
                parsed_metadata = json.loads(metadata)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid metadata JSON")

        # Parse chunking configuration if provided
        parsed_chunking_config = None
        if chunking_config:
            try:
                parsed_chunking_config = json.loads(chunking_config)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid chunking configuration JSON")

        # Read file content
        content = await file.read()

        # Prepare document data for background processing
        document_data = {
            "title": sanitized_filename,
            "content": content.decode('utf-8', errors='ignore'),
            "content_type": file.content_type or "application/octet-stream",
            "file_size": len(content),
            "metadata": parsed_metadata,
            "tags": parsed_metadata.get("tags", []) if parsed_metadata else []
        }

        # Start background processing task
        from app.tasks.document_tasks import process_and_index_document_task

        task_result = process_and_index_document_task.delay(
            document_data=document_data,
            chunking_config=parsed_chunking_config
        )

        # Return 202 Accepted with job information
        return {
            "status": "accepted",
            "message": "Document upload accepted for processing",
            "job_id": task_result.id,
            "filename": sanitized_filename,
            "file_size": len(content),
            "content_type": file.content_type or "application/octet-stream",
            "status_url": f"/api/v1/documents/status/{task_result.id}",
            "estimated_processing_time": "30 seconds",
            "submitted_at": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload document: {str(e)}")

@router.post("/")
async def create_document(
    request: DocumentCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new document with asynchronous processing.

    Returns 202 Accepted with a job ID for tracking processing status.
    The document will be intelligently chunked, embedded, and indexed in Weaviate.
    """
    try:
        # Prepare document data for background processing
        document_data = {
            "title": request.title,
            "content": request.content,
            "content_type": request.content_type,
            "file_size": len(request.content),
            "metadata": request.doc_metadata or {},
            "tags": request.tags or []
        }

        # Prepare chunking configuration
        chunking_config = {
            "chunk_size": request.chunk_size,
            "chunk_overlap": request.chunk_overlap
        }

        # Check if custom chunking config is provided in metadata
        if request.doc_metadata and "chunking_config" in request.doc_metadata:
            custom_config = request.doc_metadata.pop("chunking_config")
            chunking_config.update(custom_config)

        # Start background processing task
        from app.tasks.document_tasks import process_and_index_document_task

        task_result = process_and_index_document_task.delay(
            document_data=document_data,
            chunking_config=chunking_config
        )

        # Return 202 Accepted with job information
        return {
            "status": "accepted",
            "message": "Document creation accepted for processing",
            "job_id": task_result.id,
            "title": request.title,
            "content_type": request.content_type,
            "content_length": len(request.content),
            "status_url": f"/api/v1/documents/status/{task_result.id}",
            "estimated_processing_time": "30 seconds",
            "submitted_at": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating document: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create document: {str(e)}")


@router.get("/status/{job_id}")
async def get_processing_status(job_id: str):
    """
    Get the processing status of a document processing job.

    Args:
        job_id: The Celery task ID returned from document upload/creation

    Returns:
        Current status and progress information
    """
    try:
        from app.core.celery_app import celery_app

        # Get task result
        task_result = celery_app.AsyncResult(job_id)

        if task_result.state == 'PENDING':
            # Task is waiting to be processed
            response = {
                "job_id": job_id,
                "status": "pending",
                "message": "Task is waiting to be processed",
                "progress": 0,
                "stage": "queued"
            }
        elif task_result.state == 'PROGRESS':
            # Task is currently being processed
            meta = task_result.info or {}
            response = {
                "job_id": job_id,
                "status": "processing",
                "message": meta.get("status", "Processing document"),
                "progress": meta.get("progress", 0),
                "stage": meta.get("stage", "unknown")
            }
        elif task_result.state == 'SUCCESS':
            # Task completed successfully
            result = task_result.result or {}
            response = {
                "job_id": job_id,
                "status": "completed",
                "message": "Document processing completed successfully",
                "progress": 100,
                "stage": "completed",
                "result": {
                    "document_id": result.get("document_id"),
                    "title": result.get("title"),
                    "chunks_created": result.get("chunks_created", 0),
                    "chunks_indexed": result.get("chunks_indexed", 0),
                    "processing_time": result.get("processing_time", 0),
                    "indexed_at": result.get("indexed_at")
                }
            }
        elif task_result.state == 'FAILURE':
            # Task failed
            meta = task_result.info or {}
            response = {
                "job_id": job_id,
                "status": "failed",
                "message": "Document processing failed",
                "progress": 0,
                "stage": "error",
                "error": meta.get("error", str(task_result.info)) if task_result.info else "Unknown error"
            }
        else:
            # Unknown state
            response = {
                "job_id": job_id,
                "status": "unknown",
                "message": f"Unknown task state: {task_result.state}",
                "progress": 0,
                "stage": "unknown"
            }

        return response

    except Exception as e:
        logger.error(f"Error getting processing status for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get processing status: {str(e)}")


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

@router.post("/search")
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
        
        # Return response in format expected by tests
        return {
            "query": request.query,
            "results": [result.model_dump() for result in search_results],
            "total_results": len(search_results),
            "query_time": execution_time,
            "search_query_id": search_query_id
        }
        
    except Exception as e:
        logger.error(f"Error in semantic search: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.post("/rag-query")
async def rag_query(
    request: RAGRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Perform Retrieval-Augmented Generation query using ProductionRAGSystem.

    This endpoint implements the complete five-step RAG pipeline:
    1. Generate query embedding
    2. Retrieve relevant chunks from Weaviate
    3. Construct context-aware prompt
    4. Generate response with LLM
    5. Add citations and confidence scoring
    """
    try:
        # Import the production RAG system
        from app.core.rag_system import production_rag_system

        # Perform RAG query using the ProductionRAGSystem
        rag_response = await production_rag_system.generate_response(
            query=request.query,
            context_limit=request.search_limit,
            certainty_threshold=request.score_threshold,
            conversation_id=request.conversation_id
        )

        # Convert sources to SearchResult format for API response
        search_results = []
        for source in rag_response.sources:
            search_results.append(SearchResult(
                id=source.get("document_id", ""),
                score=source.get("score", 0.0),
                content=source.get("content_preview", ""),
                document_id=source.get("document_id", ""),
                document_title=source.get("title", "Unknown"),
                document_type="text/plain",  # Default type
                chunk_index=source.get("chunk_index", 0),
                metadata=source.get("metadata", {})
            ))

        # Save to conversation history if requested
        conversation_id = None
        if request.save_conversation and request.conversation_id:
            conversation_id = request.conversation_id
            # TODO: Save RAG interaction to conversation history

        # Return response in format expected by API consumers
        return {
            "query": request.query,
            "answer": rag_response.answer,
            "sources": search_results,
            "context_used": rag_response.context_used,
            "confidence": rag_response.confidence,
            "query_time": rag_response.query_time_ms,
            "search_metadata": rag_response.search_metadata,
            "conversation_id": conversation_id,
            "timestamp": rag_response.timestamp
        }
        
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
