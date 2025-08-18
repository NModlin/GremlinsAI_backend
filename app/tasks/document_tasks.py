"""
Document-related asynchronous tasks for Phase 5.
Handles long-running document processing, indexing, and RAG operations.
"""

import asyncio
import logging
import time
import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from celery import current_app as celery_app
from sentence_transformers import SentenceTransformer

from app.database.database import AsyncSessionLocal
from app.database.models import Document, DocumentChunk
from app.services.chunking_service import DocumentChunker, ChunkingStrategy, ChunkingConfig
from app.core.config import get_settings
from app.core.logging_config import get_logger, log_performance, log_security_event

logger = get_logger(__name__)
settings = get_settings()


@celery_app.task(bind=True, name="document_tasks.process_and_index_document")
def process_and_index_document_task(
    self,
    document_data: Dict[str, Any],
    chunking_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Asynchronously process and index a single document with intelligent chunking.

    This task implements the complete document processing pipeline:
    1. Create document record
    2. Extract metadata automatically
    3. Perform intelligent semantic chunking
    4. Generate vector embeddings for each chunk
    5. Index chunks and embeddings in Weaviate

    Args:
        document_data: Dictionary containing document information
        chunking_config: Optional chunking configuration

    Returns:
        Dict containing processing results and metadata
    """
    start_time = time.time()
    task_id = self.request.id

    try:
        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={
                'status': 'Starting document processing',
                'stage': 'initialization',
                'progress': 0
            }
        )

        logger.info(f"Starting document processing task {task_id}")

        # Run the async processing function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                _process_and_index_document(
                    self, document_data, chunking_config, start_time
                )
            )

            processing_time = time.time() - start_time

            # Log performance metrics
            log_performance(
                operation="document_processing_pipeline",
                duration_ms=processing_time * 1000,
                success=True,
                document_id=result.get("document_id"),
                chunks_created=result.get("chunks_created", 0),
                task_id=task_id
            )

            # Final success state
            self.update_state(
                state='SUCCESS',
                meta={
                    'status': 'Document processing completed',
                    'stage': 'completed',
                    'progress': 100,
                    'processing_time': processing_time,
                    'result': result
                }
            )

            logger.info(f"Document processing task {task_id} completed in {processing_time:.2f}s")
            return result

        finally:
            loop.close()

    except Exception as e:
        processing_time = time.time() - start_time
        error_msg = str(e)

        logger.error(f"Document processing task {task_id} failed: {error_msg}")

        # Log security event for processing failures
        log_security_event(
            event_type="document_processing_failure",
            severity="medium",
            task_id=task_id,
            error=error_msg,
            processing_time=processing_time
        )

        # Update task state to failure
        self.update_state(
            state='FAILURE',
            meta={
                'status': 'Document processing failed',
                'stage': 'error',
                'progress': 0,
                'error': error_msg,
                'processing_time': processing_time
            }
        )

        return {
            "success": False,
            "error": error_msg,
            "task_id": task_id,
            "processing_time": processing_time
        }


@celery_app.task(bind=True, name="document_tasks.process_document_batch")
def process_document_batch_task(self, document_data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Asynchronously process a batch of documents.
    
    Args:
        document_data_list: List of document data dictionaries
    
    Returns:
        Dict containing batch processing results
    """
    try:
        self.update_state(
            state='PROGRESS',
            meta={'status': f'Processing {len(document_data_list)} documents'}
        )
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                _process_document_batch(document_data_list)
            )
            
            self.update_state(state='SUCCESS', meta={'status': 'Batch processing completed'})
            return result
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Document batch processing failed: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'status': 'Batch processing failed', 'error': str(e)}
        )
        raise

async def _process_document_batch(document_data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Process a batch of documents asynchronously."""
    # Lazy imports to avoid circular dependencies
    from app.services.document_service import DocumentService

    async with AsyncSessionLocal() as db:
        results = []
        successful = 0
        failed = 0
        
        for doc_data in document_data_list:
            try:
                # Create document
                document = await DocumentService.create_document(
                    db=db,
                    title=doc_data.get("title", "Untitled"),
                    content=doc_data.get("content", ""),
                    content_type=doc_data.get("content_type", "text/plain"),
                    doc_metadata=doc_data.get("metadata", {}),
                    tags=doc_data.get("tags", []),
                    chunk_size=doc_data.get("chunk_size", 1000),
                    chunk_overlap=doc_data.get("chunk_overlap", 200)
                )
                
                results.append({
                    "title": doc_data.get("title"),
                    "document_id": document.id,
                    "status": "success",
                    "chunks_created": len(document.chunks)
                })
                successful += 1
                
            except Exception as e:
                results.append({
                    "title": doc_data.get("title"),
                    "document_id": None,
                    "status": "failed",
                    "error": str(e)
                })
                failed += 1
        
        return {
            "total_documents": len(document_data_list),
            "successful": successful,
            "failed": failed,
            "results": results,
            "status": "completed"
        }


async def _process_and_index_document(
    task_instance,
    document_data: Dict[str, Any],
    chunking_config: Optional[Dict[str, Any]],
    start_time: float
) -> Dict[str, Any]:
    """
    Async helper function for the complete document processing pipeline.

    Implements the intelligent document processing pipeline with:
    - Automatic metadata extraction
    - Semantic chunking with quality assessment
    - Vector embedding generation
    - Weaviate indexing with proper schema
    """
    async with AsyncSessionLocal() as db:
        try:
            # Stage 1: Create document record and extract metadata
            task_instance.update_state(
                state='PROGRESS',
                meta={
                    'status': 'Creating document record',
                    'stage': 'document_creation',
                    'progress': 10
                }
            )

            # Extract and enhance metadata
            extracted_metadata = _extract_document_metadata(document_data)

            # Create document record
            document = Document(
                id=str(uuid.uuid4()),
                title=document_data.get("title", "Untitled Document"),
                content=document_data.get("content", ""),
                content_type=document_data.get("content_type", "text/plain"),
                file_path=document_data.get("file_path"),
                file_size=document_data.get("file_size", len(document_data.get("content", ""))),
                doc_metadata=extracted_metadata,
                tags=document_data.get("tags", []),
                embedding_model="all-MiniLM-L6-v2",
                is_active=True
            )

            db.add(document)
            await db.flush()  # Get the document ID

            logger.info(f"Created document record: {document.id}")

            # Stage 2: Intelligent chunking
            task_instance.update_state(
                state='PROGRESS',
                meta={
                    'status': 'Performing intelligent chunking',
                    'stage': 'chunking',
                    'progress': 30
                }
            )

            # Configure chunking strategy based on document type and content
            chunk_config = _create_chunking_config(document_data, chunking_config)
            chunker = DocumentChunker(chunk_config)

            # Perform intelligent chunking
            chunk_results = chunker.chunk_document(document)

            # Validate chunk quality
            validation_result = chunker.validate_chunks(chunk_results)
            if not validation_result["valid"]:
                logger.warning(f"Chunk validation issues: {validation_result['issues']}")

            logger.info(f"Created {len(chunk_results)} chunks with quality score: {validation_result.get('quality_score', 0):.3f}")

            # Stage 3: Generate embeddings
            task_instance.update_state(
                state='PROGRESS',
                meta={
                    'status': 'Generating vector embeddings',
                    'stage': 'embedding_generation',
                    'progress': 50
                }
            )

            # Initialize embedding model
            embedder = SentenceTransformer('all-MiniLM-L6-v2')

            # Generate embeddings for all chunks
            chunk_texts = [chunk.content for chunk in chunk_results]
            embeddings = embedder.encode(chunk_texts, convert_to_tensor=False)

            logger.info(f"Generated embeddings for {len(chunk_texts)} chunks")

            # Stage 4: Index in Weaviate
            task_instance.update_state(
                state='PROGRESS',
                meta={
                    'status': 'Indexing in Weaviate',
                    'stage': 'weaviate_indexing',
                    'progress': 70
                }
            )

            indexed_chunks = await _index_chunks_in_weaviate(
                document, chunk_results, embeddings
            )

            # Stage 5: Create database records
            task_instance.update_state(
                state='PROGRESS',
                meta={
                    'status': 'Creating database records',
                    'stage': 'database_storage',
                    'progress': 90
                }
            )

            # Create DocumentChunk records
            chunk_records = []
            for i, (chunk_result, embedding) in enumerate(zip(chunk_results, embeddings)):
                chunk_record = DocumentChunk(
                    id=chunk_result.metadata.chunk_id,
                    document_id=document.id,
                    content=chunk_result.content,
                    chunk_index=chunk_result.metadata.chunk_index,
                    chunk_size=chunk_result.metadata.chunk_size,
                    start_position=chunk_result.metadata.start_position,
                    end_position=chunk_result.metadata.end_position,
                    chunk_metadata=chunk_result.metadata.to_dict(),
                    vector_id=indexed_chunks[i].get("weaviate_id") if i < len(indexed_chunks) else None,
                    embedding_model="all-MiniLM-L6-v2"
                )
                chunk_records.append(chunk_record)
                db.add(chunk_record)

            # Commit all changes
            await db.commit()
            await db.refresh(document)

            processing_time = time.time() - start_time

            # Prepare result
            result = {
                "success": True,
                "document_id": document.id,
                "title": document.title,
                "content_type": document.content_type,
                "file_size": document.file_size,
                "chunks_created": len(chunk_records),
                "chunks_indexed": len(indexed_chunks),
                "processing_time": processing_time,
                "metadata_extracted": extracted_metadata,
                "chunking_stats": chunker.get_chunking_stats(chunk_results),
                "validation_result": validation_result,
                "embedding_model": "all-MiniLM-L6-v2",
                "indexed_at": datetime.utcnow().isoformat()
            }

            logger.info(f"Document processing completed successfully: {document.id}")
            return result

        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            await db.rollback()
            raise


def _extract_document_metadata(document_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract and enhance document metadata automatically.

    Args:
        document_data: Raw document data

    Returns:
        Enhanced metadata dictionary
    """
    metadata = document_data.get("metadata", {}).copy()
    content = document_data.get("content", "")

    # Extract basic content statistics
    metadata.update({
        "content_length": len(content),
        "word_count": len(content.split()),
        "line_count": len(content.split('\n')),
        "paragraph_count": len([p for p in content.split('\n\n') if p.strip()]),
        "processed_at": datetime.utcnow().isoformat(),
        "processing_version": "2.4.0"
    })

    # Extract title from content if not provided
    if not document_data.get("title") or document_data.get("title") == "Untitled Document":
        lines = content.split('\n')
        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            if line and len(line) < 100:  # Reasonable title length
                metadata["extracted_title"] = line
                break

    # Detect content type characteristics
    if content:
        # Check for code patterns
        code_indicators = ['def ', 'function ', 'class ', 'import ', '#include', '<?php']
        if any(indicator in content for indicator in code_indicators):
            metadata["content_characteristics"] = metadata.get("content_characteristics", []) + ["code"]

        # Check for structured data
        if '{' in content and '}' in content:
            metadata["content_characteristics"] = metadata.get("content_characteristics", []) + ["structured"]

        # Check for academic/formal content
        academic_indicators = ['abstract', 'introduction', 'methodology', 'conclusion', 'references']
        if any(indicator.lower() in content.lower() for indicator in academic_indicators):
            metadata["content_characteristics"] = metadata.get("content_characteristics", []) + ["academic"]

    # Add file-based metadata if available
    file_path = document_data.get("file_path")
    if file_path:
        import os
        metadata.update({
            "file_extension": os.path.splitext(file_path)[1].lower(),
            "file_name": os.path.basename(file_path)
        })

    return metadata


def _create_chunking_config(
    document_data: Dict[str, Any],
    chunking_config: Optional[Dict[str, Any]]
) -> ChunkingConfig:
    """
    Create intelligent chunking configuration based on document characteristics.

    Args:
        document_data: Document data for analysis
        chunking_config: Optional override configuration

    Returns:
        Optimized ChunkingConfig instance
    """
    # Start with default configuration
    config_params = {
        "chunk_size": 1000,
        "chunk_overlap": 200,
        "strategy": ChunkingStrategy.RECURSIVE_CHARACTER,
        "preserve_sentences": True,
        "preserve_paragraphs": True
    }

    # Apply user overrides
    if chunking_config:
        config_params.update(chunking_config)

    # Intelligent strategy selection based on content
    content = document_data.get("content", "")
    content_type = document_data.get("content_type", "text/plain")
    metadata = document_data.get("metadata", {})

    # Adjust based on content type
    if content_type in ["application/json", "text/json"]:
        config_params.update({
            "strategy": ChunkingStrategy.SEMANTIC_BOUNDARY,
            "chunk_size": 800,
            "separators": ["\n\n", "\n", ",", " "]
        })
    elif content_type in ["text/markdown", "text/x-markdown"]:
        config_params.update({
            "strategy": ChunkingStrategy.HYBRID,
            "separators": ["\n## ", "\n# ", "\n\n", "\n", ". ", " "]
        })
    elif "code" in metadata.get("content_characteristics", []):
        config_params.update({
            "strategy": ChunkingStrategy.SEMANTIC_BOUNDARY,
            "chunk_size": 1200,
            "separators": ["\n\ndef ", "\nclass ", "\n\n", "\n", " "]
        })

    # Adjust based on content length
    content_length = len(content)
    if content_length < 2000:
        # Small documents - use larger chunks to maintain context
        config_params.update({
            "chunk_size": min(1500, content_length // 2),
            "chunk_overlap": 100
        })
    elif content_length > 50000:
        # Large documents - use smaller chunks for better granularity
        config_params.update({
            "chunk_size": 800,
            "chunk_overlap": 150
        })

    # Adjust based on content characteristics
    if "academic" in metadata.get("content_characteristics", []):
        config_params.update({
            "strategy": ChunkingStrategy.HYBRID,
            "chunk_size": 1200,
            "preserve_paragraphs": True
        })

    return ChunkingConfig(**config_params)


async def _index_chunks_in_weaviate(
    document: Document,
    chunk_results: List,
    embeddings: List
) -> List[Dict[str, Any]]:
    """
    Index document chunks in Weaviate with proper schema and metadata.

    Args:
        document: Document instance
        chunk_results: List of DocumentChunkResult objects
        embeddings: List of embedding vectors

    Returns:
        List of indexing results with Weaviate IDs
    """
    import requests

    indexed_chunks = []

    # Prepare Weaviate headers
    headers = {'Content-Type': 'application/json'}
    if settings.weaviate_api_key:
        headers['Authorization'] = f'Bearer {settings.weaviate_api_key}'

    try:
        for i, (chunk_result, embedding) in enumerate(zip(chunk_results, embeddings)):
            # Prepare chunk data for Weaviate
            chunk_data = {
                "class": "DocumentChunk",
                "properties": {
                    "content": chunk_result.content,
                    "document_id": document.id,
                    "document_title": document.title,
                    "chunk_index": chunk_result.metadata.chunk_index,
                    "chunk_size": chunk_result.metadata.chunk_size,
                    "start_position": chunk_result.metadata.start_position,
                    "end_position": chunk_result.metadata.end_position,
                    "content_type": document.content_type,
                    "word_count": chunk_result.metadata.word_count,
                    "sentence_count": chunk_result.metadata.sentence_count,
                    "content_density": chunk_result.metadata.content_density,
                    "semantic_coherence_score": chunk_result.metadata.semantic_coherence_score,
                    "metadata": json.dumps(chunk_result.metadata.to_dict()),
                    "created_at": datetime.utcnow().isoformat(),
                    "embedding_model": "all-MiniLM-L6-v2"
                },
                "vector": embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)
            }

            # Index in Weaviate
            response = requests.post(
                f"{settings.weaviate_url}/v1/objects",
                headers=headers,
                json=chunk_data,
                timeout=30
            )

            if response.status_code == 200:
                weaviate_result = response.json()
                indexed_chunks.append({
                    "chunk_index": i,
                    "weaviate_id": weaviate_result.get("id"),
                    "success": True
                })
                logger.debug(f"Indexed chunk {i} in Weaviate: {weaviate_result.get('id')}")
            else:
                logger.error(f"Failed to index chunk {i} in Weaviate: {response.status_code} - {response.text}")
                indexed_chunks.append({
                    "chunk_index": i,
                    "weaviate_id": None,
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                })

        logger.info(f"Successfully indexed {len([c for c in indexed_chunks if c['success']])} out of {len(chunk_results)} chunks in Weaviate")
        return indexed_chunks

    except Exception as e:
        logger.error(f"Failed to index chunks in Weaviate: {e}")
        # Return failed results for all chunks
        return [
            {
                "chunk_index": i,
                "weaviate_id": None,
                "success": False,
                "error": str(e)
            }
            for i in range(len(chunk_results))
        ]


@celery_app.task(bind=True, name="document_tasks.rebuild_vector_index")
def rebuild_vector_index_task(self, collection_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Asynchronously rebuild the vector index for documents.
    
    Args:
        collection_name: Optional specific collection to rebuild
    
    Returns:
        Dict containing rebuild results
    """
    try:
        self.update_state(state='PROGRESS', meta={'status': 'Rebuilding vector index'})
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                _rebuild_vector_index(collection_name)
            )
            
            self.update_state(state='SUCCESS', meta={'status': 'Vector index rebuilt'})
            return result
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Vector index rebuild failed: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'status': 'Index rebuild failed', 'error': str(e)}
        )
        raise

async def _rebuild_vector_index(collection_name: Optional[str]) -> Dict[str, Any]:
    """Rebuild vector index asynchronously."""
    
    async with AsyncSessionLocal() as db:
        try:
            from app.core.vector_store import vector_store
            
            # Get all documents
            documents = await DocumentService.list_documents(db, limit=1000)
            
            indexed_count = 0
            failed_count = 0
            
            for document in documents.items:
                try:
                    # Re-index document chunks
                    for chunk in document.chunks:
                        if chunk.vector_id:
                            # Remove old vector
                            vector_store.delete_document(chunk.vector_id)
                        
                        # Add new vector
                        vector_id = vector_store.add_document(
                            content=chunk.content,
                            metadata={
                                "document_id": str(document.id),
                                "chunk_id": str(chunk.id),
                                "title": document.title,
                                "tags": document.tags
                            }
                        )
                        
                        # Update chunk with new vector ID
                        chunk.vector_id = vector_id
                        await db.commit()
                    
                    indexed_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to index document {document.id}: {str(e)}")
                    failed_count += 1
            
            return {
                "total_documents": len(documents.items),
                "indexed_successfully": indexed_count,
                "failed": failed_count,
                "collection_name": collection_name or "default",
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"Vector index rebuild failed: {str(e)}")
            raise

@celery_app.task(bind=True, name="document_tasks.run_complex_rag_query")
def run_complex_rag_query_task(self, query: str, search_limit: int = 5,
                              use_multi_agent: bool = False,
                              conversation_id: Optional[str] = None,
                              save_conversation: bool = True) -> Dict[str, Any]:
    """
    Asynchronously execute a complex RAG query with optional multi-agent processing.
    
    Args:
        query: The query to process
        search_limit: Number of documents to retrieve
        use_multi_agent: Whether to use multi-agent processing
        conversation_id: Optional conversation ID
        save_conversation: Whether to save the conversation
    
    Returns:
        Dict containing RAG query results
    """
    try:
        self.update_state(state='PROGRESS', meta={'status': 'Processing RAG query'})
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                _execute_complex_rag_query(
                    query, search_limit, use_multi_agent, conversation_id, save_conversation
                )
            )
            
            self.update_state(state='SUCCESS', meta={'status': 'RAG query completed'})
            return result
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Complex RAG query failed: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'status': 'RAG query failed', 'error': str(e)}
        )
        raise

async def _execute_complex_rag_query(query: str, search_limit: int,
                                   use_multi_agent: bool, conversation_id: Optional[str],
                                   save_conversation: bool) -> Dict[str, Any]:
    """Execute complex RAG query asynchronously."""
    
    async with AsyncSessionLocal() as db:
        try:
            start_time = time.time()
            
            # Get conversation context if provided
            context = []
            if conversation_id:
                from app.services.chat_history import ChatHistoryService
                conversation = await ChatHistoryService.get_conversation(db, conversation_id)
                if conversation:
                    context = [
                        {"role": msg.role, "content": msg.content}
                        for msg in conversation.messages[-5:]  # Last 5 messages
                    ]
            
            # Execute RAG query
            from app.core.rag_system import production_rag_system

            rag_response = await production_rag_system.generate_response(
                query=query,
                context_limit=search_limit,
                certainty_threshold=0.7,
                conversation_id=conversation_id
            )

            # Convert to expected format for backward compatibility
            rag_result = {
                "query": query,
                "response": rag_response.answer,
                "sources": rag_response.sources,
                "confidence": rag_response.confidence,
                "context_used": rag_response.context_used,
                "query_time": rag_response.query_time_ms,
                "timestamp": rag_response.timestamp
            }
            
            execution_time = time.time() - start_time
            
            # Save conversation if requested
            if save_conversation:
                from app.services.chat_history import ChatHistoryService
                
                if not conversation_id:
                    conversation = await ChatHistoryService.create_conversation(
                        db=db,
                        title=f"RAG Query: {query[:50]}...",
                        initial_message=query
                    )
                    conversation_id = conversation.id
                
                # Add RAG response
                await ChatHistoryService.add_message(
                    db=db,
                    conversation_id=conversation_id,
                    role="assistant",
                    content=rag_result.get("response", ""),
                    metadata={
                        "rag_used": True,
                        "multi_agent_used": use_multi_agent,
                        "retrieved_documents": len(rag_result.get("retrieved_documents", [])),
                        "execution_time": execution_time,
                        "task_type": "complex_rag_query"
                    }
                )
            
            return {
                "query": query,
                "response": rag_result.get("response", ""),
                "retrieved_documents": rag_result.get("retrieved_documents", []),
                "context_used": rag_result.get("context_used", False),
                "multi_agent_used": use_multi_agent,
                "conversation_id": conversation_id,
                "execution_time": execution_time,
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"Complex RAG query execution failed: {str(e)}")
            raise

@celery_app.task(bind=True, name="document_tasks.analyze_document_collection")
def analyze_document_collection_task(self, analysis_type: str = "summary") -> Dict[str, Any]:
    """
    Asynchronously analyze the entire document collection.
    
    Args:
        analysis_type: Type of analysis to perform (summary, trends, etc.)
    
    Returns:
        Dict containing analysis results
    """
    try:
        self.update_state(state='PROGRESS', meta={'status': 'Analyzing document collection'})
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                _analyze_document_collection(analysis_type)
            )
            
            self.update_state(state='SUCCESS', meta={'status': 'Analysis completed'})
            return result
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Document collection analysis failed: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'status': 'Analysis failed', 'error': str(e)}
        )
        raise

async def _analyze_document_collection(analysis_type: str) -> Dict[str, Any]:
    """Analyze document collection asynchronously."""
    
    async with AsyncSessionLocal() as db:
        try:
            # Get all documents
            documents = await DocumentService.list_documents(db, limit=1000)
            
            if analysis_type == "summary":
                # Create collection summary
                total_docs = len(documents.items)
                total_chunks = sum(len(doc.chunks) for doc in documents.items)
                
                # Analyze tags
                all_tags = []
                for doc in documents.items:
                    all_tags.extend(doc.tags)
                
                tag_counts = {}
                for tag in all_tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
                
                # Most common tags
                common_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
                
                return {
                    "analysis_type": analysis_type,
                    "total_documents": total_docs,
                    "total_chunks": total_chunks,
                    "average_chunks_per_document": total_chunks / total_docs if total_docs > 0 else 0,
                    "common_tags": common_tags,
                    "unique_tags": len(tag_counts),
                    "status": "completed"
                }
            
            else:
                return {
                    "analysis_type": analysis_type,
                    "status": "unsupported_analysis_type",
                    "error": f"Analysis type '{analysis_type}' is not supported"
                }
                
        except Exception as e:
            logger.error(f"Document collection analysis failed: {str(e)}")
            raise
