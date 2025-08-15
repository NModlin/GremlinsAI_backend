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

logger = logging.getLogger(__name__)

router = APIRouter()

# Dependency to get multimodal service
def get_multimodal_service() -> MultiModalService:
    return MultiModalService()


@router.post("/process/audio", response_model=MediaAnalysisResponse)
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
            raise HTTPException(status_code=400, detail="File must be an audio file")
        
        # Read file data
        audio_data = await file.read()
        
        if len(audio_data) == 0:
            raise HTTPException(status_code=400, detail="Empty audio file")
        
        # Process audio
        processing_options = {
            'transcribe': transcribe,
            'analyze': analyze
        }
        
        result = await multimodal_processor.process_media(
            media_data=audio_data,
            media_type='audio',
            processing_options=processing_options
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
        
        return MediaAnalysisResponse(
            success=result.get('success', False),
            media_type='audio',
            filename=file.filename,
            processing_time=result.get('processing_time', 0),
            result=result.get('result', {}),
            error=result.get('error'),
            timestamp=result.get('timestamp', datetime.now().isoformat())
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audio processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Audio processing failed: {str(e)}")


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
        
        return MediaAnalysisResponse(
            success=result.get('success', False),
            media_type='video',
            filename=file.filename,
            processing_time=result.get('processing_time', 0),
            result=result.get('result', {}),
            error=result.get('error'),
            timestamp=result.get('timestamp', datetime.now().isoformat())
        )
        
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
            raise HTTPException(status_code=400, detail="File must be an image file")
        
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
        
        return MediaAnalysisResponse(
            success=result.get('success', False),
            media_type='image',
            filename=file.filename,
            processing_time=result.get('processing_time', 0),
            result=result.get('result', {}),
            error=result.get('error'),
            timestamp=result.get('timestamp', datetime.now().isoformat())
        )
        
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
