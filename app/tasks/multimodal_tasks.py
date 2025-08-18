"""
Multimodal processing tasks for Phase 3, Task 3.2: Multimodal Processing Pipeline

Handles asynchronous processing of audio, video, and image files with:
- Whisper transcription for audio (>95% accuracy)
- FFmpeg video processing with frame extraction
- CLIP embeddings for cross-modal search
- Weaviate integration for unified storage
"""

import asyncio
import logging
import time
import io
from typing import Dict, Any, List, Optional
from datetime import datetime
from celery import current_app as celery_app

from app.core.multimodal import MultiModalProcessor
from app.core.logging_config import get_logger, log_performance, log_security_event

logger = get_logger(__name__)


@celery_app.task(bind=True, name="multimodal_tasks.process_multimodal_content")
def process_multimodal_content_task(
    self,
    file_data_list: List[Dict[str, Any]],
    fusion_strategy: str = "concatenate",
    timeout: int = 300
) -> Dict[str, Any]:
    """
    Asynchronously process multiple multimodal files with unified pipeline.
    
    This task implements the complete multimodal processing pipeline:
    1. Process each file based on its media type
    2. Generate cross-modal embeddings using CLIP
    3. Store content and embeddings in Weaviate
    4. Perform multimodal fusion if multiple files
    
    Args:
        file_data_list: List of file data dictionaries
        fusion_strategy: Strategy for fusing multiple media types
        timeout: Maximum processing time in seconds
        
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
                'status': 'Starting multimodal processing',
                'stage': 'initialization',
                'progress': 0,
                'files_processed': 0,
                'total_files': len(file_data_list)
            }
        )
        
        logger.info(f"Starting multimodal processing task {task_id} with {len(file_data_list)} files")
        
        # Run the async processing function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                _process_multimodal_content_async(
                    self, file_data_list, fusion_strategy, timeout, start_time
                )
            )
            
            processing_time = time.time() - start_time
            
            # Log performance metrics
            log_performance(
                operation="multimodal_processing_pipeline",
                duration_ms=processing_time * 1000,
                success=True,
                files_processed=result.get("files_processed", 0),
                successful_files=result.get("successful_files", 0),
                task_id=task_id
            )
            
            # Final success state
            self.update_state(
                state='SUCCESS',
                meta={
                    'status': 'Multimodal processing completed',
                    'stage': 'completed',
                    'progress': 100,
                    'processing_time': processing_time,
                    'result': result
                }
            )
            
            logger.info(f"Multimodal processing task {task_id} completed in {processing_time:.2f}s")
            return result
            
        finally:
            loop.close()
            
    except Exception as e:
        processing_time = time.time() - start_time
        error_msg = str(e)
        
        logger.error(f"Multimodal processing task {task_id} failed: {error_msg}")
        
        # Log security event for processing failures
        log_security_event(
            event_type="multimodal_processing_failure",
            severity="medium",
            task_id=task_id,
            error=error_msg,
            processing_time=processing_time
        )
        
        # Update task state to failure
        self.update_state(
            state='FAILURE',
            meta={
                'status': 'Multimodal processing failed',
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


async def _process_multimodal_content_async(
    task_instance,
    file_data_list: List[Dict[str, Any]],
    fusion_strategy: str,
    timeout: int,
    start_time: float
) -> Dict[str, Any]:
    """
    Async helper function for multimodal content processing.
    
    Implements the complete multimodal processing pipeline with:
    - Individual file processing based on media type
    - Cross-modal embedding generation
    - Weaviate storage and indexing
    - Multimodal fusion for multiple files
    """
    try:
        # Initialize multimodal processor
        processor = MultiModalProcessor()
        
        # Stage 1: Process individual files
        task_instance.update_state(
            state='PROGRESS',
            meta={
                'status': 'Processing individual files',
                'stage': 'file_processing',
                'progress': 10,
                'files_processed': 0,
                'total_files': len(file_data_list)
            }
        )
        
        # Convert file data to file-like objects
        file_objects = []
        for file_data in file_data_list:
            # Create a file-like object from the content
            file_obj = io.BytesIO(file_data['content'])
            file_obj.filename = file_data['filename']
            file_obj.content_type = file_data['content_type']
            file_objects.append(file_obj)
        
        # Process all files
        processing_results = await processor.process_multimodal_content(file_objects)
        
        # Update progress
        files_processed = len(processing_results)
        successful_files = sum(1 for result in processing_results if result.success)
        failed_files = files_processed - successful_files
        
        task_instance.update_state(
            state='PROGRESS',
            meta={
                'status': 'Files processed, performing fusion',
                'stage': 'fusion',
                'progress': 70,
                'files_processed': files_processed,
                'total_files': len(file_data_list),
                'successful_files': successful_files,
                'failed_files': failed_files
            }
        )
        
        # Stage 2: Perform multimodal fusion if multiple successful files
        fusion_result = None
        if successful_files > 1:
            try:
                # Prepare fusion data
                fusion_data = []
                for result in processing_results:
                    if result.success:
                        fusion_data.append({
                            "media_type": result.media_type,
                            "filename": result.filename,
                            "content_data": result.content_data,
                            "embeddings": result.embeddings
                        })
                
                # Perform fusion based on strategy
                if fusion_strategy == "concatenate":
                    fusion_result = await _concatenate_fusion(fusion_data)
                elif fusion_strategy == "weighted":
                    fusion_result = await _weighted_fusion(fusion_data)
                elif fusion_strategy == "semantic":
                    fusion_result = await _semantic_fusion(fusion_data)
                else:
                    fusion_result = await _concatenate_fusion(fusion_data)
                    
            except Exception as e:
                logger.error(f"Fusion failed: {e}")
                fusion_result = {"error": f"Fusion failed: {str(e)}"}
        
        # Stage 3: Final processing and results
        task_instance.update_state(
            state='PROGRESS',
            meta={
                'status': 'Finalizing results',
                'stage': 'finalization',
                'progress': 90,
                'files_processed': files_processed,
                'total_files': len(file_data_list)
            }
        )
        
        processing_time = time.time() - start_time
        
        # Collect Weaviate IDs
        weaviate_ids = [result.weaviate_id for result in processing_results if result.weaviate_id]
        
        # Prepare final result
        result = {
            "success": True,
            "files_processed": files_processed,
            "successful_files": successful_files,
            "failed_files": failed_files,
            "processing_time": processing_time,
            "fusion_strategy": fusion_strategy,
            "fusion_result": fusion_result,
            "weaviate_ids": weaviate_ids,
            "individual_results": [
                {
                    "filename": result.filename,
                    "media_type": result.media_type,
                    "success": result.success,
                    "weaviate_id": result.weaviate_id,
                    "processing_time": result.processing_time,
                    "error_message": result.error_message
                }
                for result in processing_results
            ],
            "cross_modal_embeddings": len([r for r in processing_results if r.embeddings]) > 0,
            "processed_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Multimodal processing completed: {successful_files}/{files_processed} files successful")
        return result
        
    except Exception as e:
        logger.error(f"Multimodal processing failed: {e}")
        raise


async def _concatenate_fusion(fusion_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Simple concatenation fusion strategy."""
    combined_text = ""
    media_types = []
    
    for data in fusion_data:
        media_types.append(data["media_type"])
        
        # Extract text content based on media type
        if data["media_type"] == "audio":
            transcription = data["content_data"].get("transcription", {})
            combined_text += transcription.get("text", "") + " "
        elif data["media_type"] == "video":
            # Combine audio transcription and frame descriptions
            audio_transcription = data["content_data"].get("audio_transcription", {})
            combined_text += audio_transcription.get("text", "") + " "
            
            frames = data["content_data"].get("frames", {})
            for frame in frames.get("analyzed_frames", []):
                combined_text += frame.get("description", "") + " "
        elif data["media_type"] == "image":
            analysis = data["content_data"].get("analysis", {})
            combined_text += analysis.get("description", "") + " "
    
    return {
        "strategy": "concatenate",
        "combined_text": combined_text.strip(),
        "media_types": media_types,
        "fusion_quality": "basic"
    }


async def _weighted_fusion(fusion_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Weighted fusion strategy based on media type importance."""
    # Simple weighted approach - can be enhanced with ML models
    weights = {"video": 0.4, "audio": 0.35, "image": 0.25}
    
    weighted_content = {}
    for data in fusion_data:
        media_type = data["media_type"]
        weight = weights.get(media_type, 0.33)
        
        weighted_content[media_type] = {
            "weight": weight,
            "content": data["content_data"]
        }
    
    return {
        "strategy": "weighted",
        "weighted_content": weighted_content,
        "fusion_quality": "enhanced"
    }


async def _semantic_fusion(fusion_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Semantic fusion strategy using embeddings similarity."""
    # This would use actual semantic analysis in production
    # For now, return a placeholder implementation
    
    return {
        "strategy": "semantic",
        "semantic_analysis": "Advanced semantic fusion not yet implemented",
        "fusion_quality": "advanced",
        "note": "This would use CLIP embeddings for semantic similarity analysis"
    }
