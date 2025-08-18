"""
Multi-Modal API endpoints for Phase 7.

Provides REST API endpoints for processing audio, video, and image content
with comprehensive multi-modal analysis and fusion capabilities.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.multimodal import multimodal_processor
from app.database.models import MultiModalContent
from app.services.multimodal_service import MultiModalService
from app.api.v1.schemas.multimodal import (
    MultiModalProcessRequest,
    MultiModalProcessResponse,
    MediaAnalysisResponse,
    MultiModalFusionRequest,
    MultiModalFusionResponse
)
from app.core.exceptions import (
    MultiModalProcessingException,
    ValidationException,
    ValidationErrorDetail,
    ExternalServiceException
)
from app.core.error_handlers import (
    create_multimodal_processing_error,
    create_service_degradation_response
)
from app.api.v1.schemas.errors import ERROR_RESPONSES

logger = logging.getLogger(__name__)

router = APIRouter()

# Dependency to get multimodal service
def get_multimodal_service() -> MultiModalService:
    return MultiModalService()


@router.post("/upload")
async def upload_multimodal_content(
    files: List[UploadFile] = File(...),
    fusion_strategy: str = Form("concatenate"),
    timeout: int = Form(300)
):
    """
    Upload and process multiple multimodal files with background processing.

    This endpoint implements the unified multimodal processing pipeline with:
    - Audio transcription using Whisper (>95% accuracy)
    - Video processing with FFmpeg and frame extraction
    - Image processing with CLIP embeddings
    - Cross-modal embeddings for unified search
    - Weaviate integration for content indexing

    Returns 202 Accepted with a job ID for tracking processing status.
    """
    try:
        # Validate files
        if not files:
            raise HTTPException(status_code=422, detail="At least one file is required")

        # Validate file types
        supported_types = {
            'audio': ['audio/wav', 'audio/mp3', 'audio/m4a', 'audio/flac', 'audio/ogg'],
            'video': ['video/mp4', 'video/avi', 'video/mov', 'video/mkv'],
            'image': ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/bmp']
        }

        all_supported = []
        for category in supported_types.values():
            all_supported.extend(category)

        for file in files:
            if file.content_type not in all_supported:
                raise HTTPException(
                    status_code=422,
                    detail=f"Unsupported file type: {file.content_type}. Supported types: {all_supported}"
                )

        # Start background processing task
        from app.tasks.multimodal_tasks import process_multimodal_content_task

        # Prepare file data for background processing
        file_data_list = []
        for file in files:
            content = await file.read()
            file_data_list.append({
                "filename": file.filename,
                "content_type": file.content_type,
                "content": content,
                "size": len(content)
            })

        # Start the background task
        task_result = process_multimodal_content_task.delay(
            file_data_list=file_data_list,
            fusion_strategy=fusion_strategy,
            timeout=timeout
        )

        # Return 202 Accepted with job information
        return {
            "status": "accepted",
            "message": "Multimodal content upload accepted for processing",
            "job_id": task_result.id,
            "files_count": len(files),
            "fusion_strategy": fusion_strategy,
            "status_url": f"/api/v1/multimodal/status/{task_result.id}",
            "estimated_processing_time": f"{len(files) * 30} seconds",
            "submitted_at": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Multimodal upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/status/{job_id}")
async def get_multimodal_processing_status(job_id: str):
    """
    Get the processing status of a multimodal processing job.

    Args:
        job_id: The Celery task ID returned from multimodal upload

    Returns:
        Current status and progress information
    """
    try:
        from app.core.celery_app import celery_app

        # Get task result
        task_result = celery_app.AsyncResult(job_id)

        if task_result.state == 'PENDING':
            response = {
                "job_id": job_id,
                "status": "pending",
                "message": "Task is waiting to be processed",
                "progress": 0,
                "stage": "queued"
            }
        elif task_result.state == 'PROGRESS':
            meta = task_result.info or {}
            response = {
                "job_id": job_id,
                "status": "processing",
                "message": meta.get("status", "Processing multimodal content"),
                "progress": meta.get("progress", 0),
                "stage": meta.get("stage", "unknown"),
                "files_processed": meta.get("files_processed", 0),
                "total_files": meta.get("total_files", 0)
            }
        elif task_result.state == 'SUCCESS':
            result = task_result.result or {}
            response = {
                "job_id": job_id,
                "status": "completed",
                "message": "Multimodal processing completed successfully",
                "progress": 100,
                "stage": "completed",
                "result": {
                    "files_processed": result.get("files_processed", 0),
                    "successful_files": result.get("successful_files", 0),
                    "failed_files": result.get("failed_files", 0),
                    "fusion_result": result.get("fusion_result"),
                    "cross_modal_embeddings": result.get("cross_modal_embeddings"),
                    "weaviate_ids": result.get("weaviate_ids", []),
                    "processing_time": result.get("processing_time", 0)
                }
            }
        elif task_result.state == 'FAILURE':
            meta = task_result.info or {}
            response = {
                "job_id": job_id,
                "status": "failed",
                "message": "Multimodal processing failed",
                "progress": 0,
                "stage": "error",
                "error": meta.get("error", str(task_result.info)) if task_result.info else "Unknown error"
            }
        else:
            response = {
                "job_id": job_id,
                "status": "unknown",
                "message": f"Unknown task state: {task_result.state}",
                "progress": 0,
                "stage": "unknown"
            }

        return response

    except Exception as e:
        logger.error(f"Error getting multimodal processing status for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get processing status: {str(e)}")


@router.post("/search")
async def search_multimodal_content(
    query: str = Form(...),
    media_types: Optional[List[str]] = Form(None),
    limit: int = Form(10)
):
    """
    Perform cross-modal search using text query to find relevant media content.

    This endpoint demonstrates the cross-modal search capabilities where
    text queries can find relevant images, videos, or audio content.
    """
    try:
        # Initialize multimodal processor
        from app.core.multimodal import MultiModalProcessor
        processor = MultiModalProcessor()

        # Perform cross-modal search
        results = await processor.search_cross_modal(
            query=query,
            media_types=media_types,
            limit=limit
        )

        return {
            "query": query,
            "media_types_searched": media_types or ["audio", "video", "image"],
            "results_count": len(results),
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Cross-modal search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# Simplified routes for backward compatibility
@router.post(
    "/audio",
    response_model=MediaAnalysisResponse,
    responses=ERROR_RESPONSES
)
async def process_audio_simple(
    file: UploadFile = File(...),
    transcribe: bool = Form(True),
    analyze: bool = Form(False),
    conversation_id: Optional[str] = Form(None),
    multimodal_service: MultiModalService = Depends(get_multimodal_service)
):
    """
    Process audio file with speech-to-text and analysis capabilities (simplified endpoint).
    """
    return await process_audio(file, transcribe, analyze, conversation_id, multimodal_service)


@router.post(
    "/image",
    response_model=MediaAnalysisResponse,
    responses=ERROR_RESPONSES
)
async def process_image_simple(
    file: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None),
    detect_objects: bool = Form(False),
    extract_text: bool = Form(False),
    enhance: bool = Form(False),
    analyze: bool = Form(True),
    conversation_id: Optional[str] = Form(None),
    options: Optional[str] = Form(None),
    multimodal_service: MultiModalService = Depends(get_multimodal_service)
):
    """
    Process image file with computer vision and analysis capabilities (simplified endpoint).
    """
    # Determine which file parameter was provided
    upload_file = file if file else image
    if not upload_file:
        raise HTTPException(status_code=422, detail="Either 'file' or 'image' parameter is required")

    # Parse options if provided
    if options:
        try:
            import json
            opts = json.loads(options)
            detect_objects = opts.get("detect_objects", detect_objects)
            extract_text = opts.get("extract_text", extract_text)
            enhance = opts.get("enhance", enhance)
            analyze = opts.get("analyze", analyze)
        except (json.JSONDecodeError, AttributeError):
            pass  # Use default values if parsing fails

    return await process_image(upload_file, detect_objects, extract_text, enhance, analyze, conversation_id, multimodal_service)


@router.post(
    "/video",
    response_model=MediaAnalysisResponse,
    responses=ERROR_RESPONSES
)
async def process_video_simple(
    file: Optional[UploadFile] = File(None),
    video: Optional[UploadFile] = File(None),
    extract_frames: bool = Form(False),
    transcribe_audio: bool = Form(True),
    analyze: bool = Form(False),
    frame_count: int = Form(10),
    conversation_id: Optional[str] = Form(None),
    options: Optional[str] = Form(None),
    multimodal_service: MultiModalService = Depends(get_multimodal_service)
):
    """
    Process video file with frame extraction, audio transcription, and analysis (simplified endpoint).
    """
    # Determine which file parameter was provided
    upload_file = file if file else video
    if not upload_file:
        raise HTTPException(status_code=422, detail="Either 'file' or 'video' parameter is required")

    # Parse options if provided
    if options:
        try:
            import json
            opts = json.loads(options)
            extract_frames = opts.get("extract_frames", extract_frames)
            transcribe_audio = opts.get("transcribe_audio", transcribe_audio)
            analyze = opts.get("analyze", analyze)
            frame_count = opts.get("frame_count", frame_count)
        except (json.JSONDecodeError, AttributeError):
            pass  # Use default values if parsing fails

    return await process_video(upload_file, extract_frames, transcribe_audio, analyze, frame_count, conversation_id, multimodal_service)


@router.post(
    "/process/audio",
    response_model=MediaAnalysisResponse,
    responses=ERROR_RESPONSES
)
async def process_audio(
    file: UploadFile = File(...),
    transcribe: bool = Form(True),
    analyze: bool = Form(False),
    conversation_id: Optional[str] = Form(None),
    multimodal_service: MultiModalService = Depends(get_multimodal_service)
):
    """
    Process audio file with speech-to-text and analysis capabilities.
    
    - **file**: Audio file to process (WAV, MP3, M4A, etc.)
    - **transcribe**: Whether to transcribe speech to text
    - **analyze**: Whether to perform audio analysis
    - **conversation_id**: Optional conversation ID to associate with
    """
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('audio/'):
            raise ValidationException(
                error_message="Invalid file type for audio processing",
                validation_errors=[ValidationErrorDetail(
                    field="file",
                    message="File must be an audio file",
                    invalid_value=file.content_type,
                    expected_type="audio/*"
                )]
            )

        # Read file data
        audio_data = await file.read()

        if len(audio_data) == 0:
            raise ValidationException(
                error_message="Empty audio file provided",
                validation_errors=[ValidationErrorDetail(
                    field="file",
                    message="Audio file cannot be empty",
                    invalid_value="0 bytes",
                    expected_type="non-empty audio file"
                )]
            )
        
        # Process audio
        processing_options = {
            'transcribe': transcribe,
            'analyze': analyze
        }

        try:
            result = await multimodal_processor.process_media(
                media_data=audio_data,
                media_type='audio',
                processing_options=processing_options
            )

            # Check if processing failed
            if not result.get('success', False):
                error_details = result.get('error', 'Unknown audio processing error')
                raise MultiModalProcessingException(
                    error_message="Audio processing failed",
                    media_type="audio",
                    error_details=error_details,
                    processing_step="audio_processing",
                    fallback_available=True
                )

        except MultiModalProcessingException:
            raise
        except Exception as e:
            raise MultiModalProcessingException(
                error_message="Unexpected error during audio processing",
                media_type="audio",
                error_details=str(e),
                processing_step="audio_processing",
                fallback_available=False
            )
        
        # Save to database if conversation_id provided
        if conversation_id and result.get('success'):
            await multimodal_service.save_multimodal_content(
                conversation_id=conversation_id,
                media_type='audio',
                filename=file.filename,
                content_data=audio_data,
                processing_result=result
            )
        
        # Extract nested result data for backward compatibility
        result_data = result.get('result', {})

        # Create response with expected structure
        response_data = {
            "success": result.get('success', False),
            "media_type": 'audio',
            "filename": file.filename,
            "processing_time": result.get('processing_time', 0),
            "result": result_data,
            "error": result.get('error'),
            "timestamp": result.get('timestamp', datetime.now().isoformat())
        }

        # Add transcription and analysis at top level for test compatibility
        if 'transcription' in result_data:
            response_data['transcription'] = result_data['transcription']
        if 'analysis' in result_data:
            response_data['analysis'] = result_data['analysis']

        return MediaAnalysisResponse(**response_data)
        
    except (ValidationException, MultiModalProcessingException):
        raise
    except Exception as e:
        logger.error(f"Unexpected error in audio processing endpoint: {e}")
        raise MultiModalProcessingException(
            error_message="Unexpected error in audio processing endpoint",
            media_type="audio",
            error_details=str(e),
            processing_step="endpoint_handling",
            fallback_available=False
        )


@router.post("/process/video", response_model=MediaAnalysisResponse)
async def process_video(
    file: UploadFile = File(...),
    extract_frames: bool = Form(False),
    transcribe_audio: bool = Form(True),
    analyze: bool = Form(False),
    frame_count: int = Form(10),
    conversation_id: Optional[str] = Form(None),
    multimodal_service: MultiModalService = Depends(get_multimodal_service)
):
    """
    Process video file with frame extraction, audio transcription, and analysis.
    
    - **file**: Video file to process (MP4, AVI, MOV, etc.)
    - **extract_frames**: Whether to extract key frames
    - **transcribe_audio**: Whether to transcribe audio track
    - **analyze**: Whether to perform video analysis
    - **frame_count**: Number of frames to extract (if extract_frames=True)
    - **conversation_id**: Optional conversation ID to associate with
    """
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('video/'):
            raise HTTPException(status_code=400, detail="File must be a video file")
        
        # Read file data
        video_data = await file.read()
        
        if len(video_data) == 0:
            raise HTTPException(status_code=400, detail="Empty video file")
        
        # Process video
        processing_options = {
            'extract_frames': extract_frames,
            'transcribe_audio': transcribe_audio,
            'analyze': analyze,
            'frame_count': frame_count
        }
        
        result = await multimodal_processor.process_media(
            media_data=video_data,
            media_type='video',
            processing_options=processing_options
        )
        
        # Save to database if conversation_id provided
        if conversation_id and result.get('success'):
            await multimodal_service.save_multimodal_content(
                conversation_id=conversation_id,
                media_type='video',
                filename=file.filename,
                content_data=video_data,
                processing_result=result
            )
        
        # Extract nested result data for backward compatibility
        result_data = result.get('result', {})

        # Create response with expected structure
        response_data = {
            "success": result.get('success', False),
            "media_type": 'video',
            "filename": file.filename,
            "processing_time": result.get('processing_time', 0),
            "result": result_data,
            "error": result.get('error'),
            "timestamp": result.get('timestamp', datetime.now().isoformat())
        }

        # Add video-specific fields at top level for test compatibility
        if 'frames' in result_data:
            response_data['frames'] = result_data['frames']
        if 'audio_transcription' in result_data:
            response_data['audio_transcription'] = result_data['audio_transcription']
        if 'analysis' in result_data:
            response_data['analysis'] = result_data['analysis']

        return MediaAnalysisResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Video processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Video processing failed: {str(e)}")


@router.post("/process/image", response_model=MediaAnalysisResponse)
async def process_image(
    file: UploadFile = File(...),
    detect_objects: bool = Form(False),
    extract_text: bool = Form(False),
    enhance: bool = Form(False),
    analyze: bool = Form(True),
    conversation_id: Optional[str] = Form(None),
    multimodal_service: MultiModalService = Depends(get_multimodal_service)
):
    """
    Process image file with computer vision and analysis capabilities.
    
    - **file**: Image file to process (JPG, PNG, GIF, etc.)
    - **detect_objects**: Whether to detect objects in the image
    - **extract_text**: Whether to extract text using OCR
    - **enhance**: Whether to enhance image quality
    - **analyze**: Whether to perform image analysis
    - **conversation_id**: Optional conversation ID to associate with
    """
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Unsupported image format")
        
        # Read file data
        image_data = await file.read()
        
        if len(image_data) == 0:
            raise HTTPException(status_code=400, detail="Empty image file")
        
        # Process image
        processing_options = {
            'detect_objects': detect_objects,
            'extract_text': extract_text,
            'enhance': enhance,
            'analyze': analyze
        }
        
        result = await multimodal_processor.process_media(
            media_data=image_data,
            media_type='image',
            processing_options=processing_options
        )
        
        # Save to database if conversation_id provided
        if conversation_id and result.get('success'):
            await multimodal_service.save_multimodal_content(
                conversation_id=conversation_id,
                media_type='image',
                filename=file.filename,
                content_data=image_data,
                processing_result=result
            )
        
        # Extract nested result data for backward compatibility
        result_data = result.get('result', {})

        # Create response with expected structure
        response_data = {
            "success": result.get('success', False),
            "media_type": 'image',
            "filename": file.filename,
            "processing_time": result.get('processing_time', 0),
            "result": result_data,
            "error": result.get('error'),
            "timestamp": result.get('timestamp', datetime.now().isoformat())
        }

        # Add analysis and other fields at top level for test compatibility
        if 'analysis' in result_data:
            response_data['analysis'] = result_data['analysis']
        if 'objects' in result_data:
            response_data['objects'] = result_data['objects']
        if 'text' in result_data:
            response_data['text'] = result_data['text']

        return MediaAnalysisResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Image processing failed: {str(e)}")


@router.post("/process/multimodal", response_model=MultiModalProcessResponse)
async def process_multimodal(
    files: List[UploadFile] = File(...),
    fusion_strategy: str = Form("concatenate"),
    conversation_id: Optional[str] = Form(None),
    multimodal_service: MultiModalService = Depends(get_multimodal_service)
):
    """
    Process multiple media files and fuse results into unified output.
    
    - **files**: List of media files (audio, video, image)
    - **fusion_strategy**: Strategy for fusing results ('concatenate', 'weighted', 'semantic')
    - **conversation_id**: Optional conversation ID to associate with
    """
    try:
        if len(files) == 0:
            raise HTTPException(status_code=400, detail="At least one file must be provided")
        
        media_results = []
        
        # Process each file
        for file in files:
            # Determine media type from content type
            if file.content_type.startswith('audio/'):
                media_type = 'audio'
                processing_options = {'transcribe': True, 'analyze': False}
            elif file.content_type.startswith('video/'):
                media_type = 'video'
                processing_options = {'transcribe_audio': True, 'extract_frames': False, 'analyze': False}
            elif file.content_type.startswith('image/'):
                media_type = 'image'
                processing_options = {'analyze': True, 'detect_objects': False, 'extract_text': False}
            else:
                logger.warning(f"Unsupported file type: {file.content_type}")
                continue
            
            # Read and process file
            file_data = await file.read()
            
            result = await multimodal_processor.process_media(
                media_data=file_data,
                media_type=media_type,
                processing_options=processing_options
            )
            
            result['filename'] = file.filename
            media_results.append(result)
            
            # Save individual results if conversation_id provided
            if conversation_id and result.get('success'):
                await multimodal_service.save_multimodal_content(
                    conversation_id=conversation_id,
                    media_type=media_type,
                    filename=file.filename,
                    content_data=file_data,
                    processing_result=result
                )
        
        # Fuse results
        fused_result = await multimodal_processor.fuse_multimodal_data(
            media_results=media_results,
            fusion_strategy=fusion_strategy
        )
        
        return MultiModalProcessResponse(
            success=True,
            processed_files=len(media_results),
            fusion_strategy=fusion_strategy,
            individual_results=media_results,
            fused_result=fused_result,
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Multi-modal processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Multi-modal processing failed: {str(e)}")


@router.get("/capabilities")
async def get_multimodal_capabilities():
    """
    Get available multi-modal processing capabilities.
    
    Returns information about which processing features are available
    based on installed dependencies.
    """
    try:
        capabilities = multimodal_processor.capabilities
        
        return {
            "success": True,
            "capabilities": capabilities,
            "supported_media_types": ["audio", "video", "image"],
            "supported_audio_formats": ["wav", "mp3", "m4a", "flac"],
            "supported_video_formats": ["mp4", "avi", "mov", "mkv"],
            "supported_image_formats": ["jpg", "jpeg", "png", "gif", "bmp"],
            "fusion_strategies": ["concatenate", "weighted", "semantic"],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get capabilities: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get capabilities: {str(e)}")


@router.get("/conversation/{conversation_id}/multimodal")
async def get_conversation_multimodal_content(
    conversation_id: str,
    media_type: Optional[str] = None,
    multimodal_service: MultiModalService = Depends(get_multimodal_service)
):
    """
    Get multi-modal content associated with a conversation.
    
    - **conversation_id**: ID of the conversation
    - **media_type**: Optional filter by media type ('audio', 'video', 'image')
    """
    try:
        content = await multimodal_service.get_conversation_multimodal_content(
            conversation_id=conversation_id,
            media_type=media_type
        )
        
        return {
            "success": True,
            "conversation_id": conversation_id,
            "content_count": len(content),
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get conversation multimodal content: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get content: {str(e)}")


@router.delete("/content/{content_id}")
async def delete_multimodal_content(
    content_id: str,
    multimodal_service: MultiModalService = Depends(get_multimodal_service)
):
    """
    Delete multi-modal content by ID.
    
    - **content_id**: ID of the content to delete
    """
    try:
        success = await multimodal_service.delete_multimodal_content(content_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Content not found")
        
        return {
            "success": True,
            "message": "Content deleted successfully",
            "content_id": content_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete multimodal content: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete content: {str(e)}")


@router.post("/text-to-speech")
async def text_to_speech(
    text: str = Form(...),
    output_format: str = Form("wav"),
    multimodal_service: MultiModalService = Depends(get_multimodal_service)
):
    """
    Convert text to speech.
    
    - **text**: Text to convert to speech
    - **output_format**: Output audio format (wav, mp3)
    """
    try:
        if not text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        result = await multimodal_processor.audio_processor.text_to_speech(text)
        
        return {
            "success": result.get("success", False),
            "text": text,
            "output_format": output_format,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Text-to-speech failed: {e}")
        raise HTTPException(status_code=500, detail=f"Text-to-speech failed: {str(e)}")


@router.get("/health")
async def multimodal_health_check():
    """
    Health check endpoint for multi-modal services.
    """
    try:
        capabilities = multimodal_processor.capabilities
        
        # Count available capabilities
        available_count = sum(1 for available in capabilities.values() if available)
        total_count = len(capabilities)
        
        health_status = "healthy" if available_count > 0 else "degraded"
        
        return {
            "status": health_status,
            "available_capabilities": available_count,
            "total_capabilities": total_count,
            "capabilities": capabilities,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
