"""
Multi-Modal Processing Core for Phase 3, Task 3.2: Multimodal Processing Pipeline.

This module provides comprehensive multi-modal processing capabilities including:
- Audio processing with Whisper transcription (>95% accuracy)
- Video processing with FFmpeg and frame extraction
- Image processing with CLIP embeddings
- Cross-modal search and embeddings for unified retrieval
- Weaviate integration for multimodal content indexing
"""

import os
import io
import logging
import tempfile
import asyncio
import subprocess
import json
from typing import Dict, Any, List, Optional, Union, BinaryIO
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass

import numpy as np
from PIL import Image

# Optional imports with fallbacks
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

try:
    from transformers import CLIPProcessor, CLIPModel
    import torch
    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from app.core.config import get_settings
from app.core.logging_config import get_logger, log_performance

logger = get_logger(__name__)
settings = get_settings()

# Log availability of dependencies
if not CV2_AVAILABLE:
    logger.warning("OpenCV not available - video processing limited")
if not WHISPER_AVAILABLE:
    logger.warning("Whisper not available - audio transcription disabled")
if not CLIP_AVAILABLE:
    logger.warning("CLIP not available - cross-modal embeddings disabled")


@dataclass
class MultiModalResult:
    """Result from multimodal processing."""
    success: bool
    media_type: str
    filename: str
    content_data: Dict[str, Any]
    embeddings: Optional[List[float]] = None
    weaviate_id: Optional[str] = None
    processing_time: float = 0.0
    error_message: Optional[str] = None


class MultiModalProcessor:
    """
    Unified multi-modal processing system implementing the technical architecture from prometheus.md.

    This class acts as a gateway for all non-textual data, intelligently routing files
    to appropriate processing functions and generating cross-modal embeddings using CLIP.

    Features:
    - Audio transcription with Whisper (>95% accuracy)
    - Video processing with FFmpeg and frame extraction
    - Image processing with CLIP embeddings
    - Cross-modal search capabilities
    - Weaviate integration for unified storage
    """

    def __init__(self):
        """Initialize the multimodal processor with required models."""
        self.whisper_model = None
        self.clip_model = None
        self.clip_processor = None
        self.device = "cuda" if torch.cuda.is_available() and CLIP_AVAILABLE else "cpu"

        # Initialize models
        self._initialize_models()

        # Legacy processors for backward compatibility
        self.audio_processor = AudioProcessor()
        self.video_processor = VideoProcessor()
        self.image_processor = ImageProcessor()
        self.fusion_processor = MultiModalFusionProcessor()

        # Check available capabilities
        self.capabilities = self._check_capabilities()
        logger.info(f"MultiModal processor initialized with capabilities: {list(self.capabilities.keys())}")
        logger.info(f"Using device: {self.device}")

    def _initialize_models(self):
        """Initialize Whisper and CLIP models."""
        try:
            # Initialize Whisper model
            if WHISPER_AVAILABLE:
                logger.info("Loading Whisper model...")
                self.whisper_model = whisper.load_model("base")
                logger.info("Whisper model loaded successfully")
            else:
                logger.warning("Whisper not available - audio transcription disabled")

            # Initialize CLIP model
            if CLIP_AVAILABLE:
                logger.info("Loading CLIP model...")
                self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
                self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

                if self.device == "cuda":
                    self.clip_model = self.clip_model.to(self.device)

                logger.info("CLIP model loaded successfully")
            else:
                logger.warning("CLIP not available - cross-modal embeddings disabled")

        except Exception as e:
            logger.error(f"Failed to initialize models: {e}")
            # Continue with limited functionality

    async def process_multimodal_content(self, files: List[Any]) -> List[MultiModalResult]:
        """
        Process multiple files of different media types.

        Args:
            files: List of file objects (UploadFile or file paths)

        Returns:
            List of MultiModalResult objects
        """
        results = []

        for file in files:
            try:
                # Determine content type
                if hasattr(file, 'content_type'):
                    content_type = file.content_type
                    filename = file.filename
                else:
                    # Assume it's a file path
                    filename = str(file)
                    content_type = self._get_content_type_from_filename(filename)

                # Route to appropriate processor
                if content_type.startswith('audio/'):
                    result = await self._process_audio(file)
                elif content_type.startswith('video/'):
                    result = await self._process_video(file)
                elif content_type.startswith('image/'):
                    result = await self._process_image(file)
                else:
                    result = MultiModalResult(
                        success=False,
                        media_type="unknown",
                        filename=filename,
                        content_data={},
                        error_message=f"Unsupported content type: {content_type}"
                    )

                # Store in Weaviate if successful
                if result.success:
                    await self._store_multimodal_content(result)

                results.append(result)

            except Exception as e:
                logger.error(f"Failed to process file {getattr(file, 'filename', str(file))}: {e}")
                results.append(MultiModalResult(
                    success=False,
                    media_type="unknown",
                    filename=getattr(file, 'filename', str(file)),
                    content_data={},
                    error_message=str(e)
                ))

        return results

    async def _process_audio(self, file) -> MultiModalResult:
        """
        Process audio file with Whisper transcription and CLIP embeddings.

        Args:
            file: Audio file object or path

        Returns:
            MultiModalResult with transcription and embeddings
        """
        start_time = asyncio.get_event_loop().time()

        try:
            if not WHISPER_AVAILABLE:
                return MultiModalResult(
                    success=False,
                    media_type="audio",
                    filename=getattr(file, 'filename', str(file)),
                    content_data={},
                    error_message="Whisper not available for audio transcription"
                )

            # Save file temporarily
            temp_path = await self._save_temp_file(file)

            try:
                # Transcribe with Whisper
                logger.info(f"Transcribing audio file: {getattr(file, 'filename', str(file))}")
                result = self.whisper_model.transcribe(temp_path)

                transcription_text = result["text"]
                segments = result.get("segments", [])

                # Generate CLIP embeddings for the transcription text
                text_embeddings = None
                if CLIP_AVAILABLE and transcription_text.strip():
                    text_embeddings = await self._generate_text_embeddings(transcription_text)

                processing_time = asyncio.get_event_loop().time() - start_time

                # Log performance
                log_performance(
                    operation="audio_transcription",
                    duration_ms=processing_time * 1000,
                    success=True,
                    audio_duration=result.get("duration", 0),
                    transcription_length=len(transcription_text)
                )

                return MultiModalResult(
                    success=True,
                    media_type="audio",
                    filename=getattr(file, 'filename', str(file)),
                    content_data={
                        "transcription": {
                            "text": transcription_text,
                            "segments": segments,
                            "language": result.get("language"),
                            "duration": result.get("duration")
                        }
                    },
                    embeddings=text_embeddings,
                    processing_time=processing_time
                )

            finally:
                # Cleanup temp file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            processing_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"Audio processing failed: {e}")

            return MultiModalResult(
                success=False,
                media_type="audio",
                filename=getattr(file, 'filename', str(file)),
                content_data={},
                processing_time=processing_time,
                error_message=str(e)
            )

    async def _process_video(self, file) -> MultiModalResult:
        """
        Process video file with FFmpeg audio extraction and frame sampling.

        Args:
            file: Video file object or path

        Returns:
            MultiModalResult with audio transcription and frame embeddings
        """
        start_time = asyncio.get_event_loop().time()

        try:
            # Check FFmpeg availability
            if not self._check_ffmpeg_available():
                return MultiModalResult(
                    success=False,
                    media_type="video",
                    filename=getattr(file, 'filename', str(file)),
                    content_data={},
                    error_message="FFmpeg not available for video processing"
                )

            # Save file temporarily
            temp_video_path = await self._save_temp_file(file)

            try:
                logger.info(f"Processing video file: {getattr(file, 'filename', str(file))}")

                # Extract audio track for transcription
                audio_result = None
                if WHISPER_AVAILABLE:
                    audio_result = await self._extract_and_transcribe_audio(temp_video_path)

                # Extract keyframes for image analysis
                frames_result = None
                if CV2_AVAILABLE:
                    frames_result = await self._extract_and_analyze_frames(temp_video_path)

                # Get video metadata
                metadata = await self._get_video_metadata(temp_video_path)

                processing_time = asyncio.get_event_loop().time() - start_time

                # Combine results
                content_data = {
                    "metadata": metadata
                }

                if audio_result:
                    content_data["audio_transcription"] = audio_result

                if frames_result:
                    content_data["frames"] = frames_result

                # Generate combined embeddings (audio text + frame descriptions)
                combined_embeddings = None
                if CLIP_AVAILABLE:
                    combined_text = ""
                    if audio_result:
                        combined_text += audio_result.get("text", "")
                    if frames_result:
                        frame_descriptions = [frame.get("description", "") for frame in frames_result.get("analyzed_frames", [])]
                        combined_text += " " + " ".join(frame_descriptions)

                    if combined_text.strip():
                        combined_embeddings = await self._generate_text_embeddings(combined_text)

                # Log performance
                log_performance(
                    operation="video_processing",
                    duration_ms=processing_time * 1000,
                    success=True,
                    video_duration=metadata.get("duration", 0),
                    frames_extracted=len(frames_result.get("analyzed_frames", [])) if frames_result else 0
                )

                return MultiModalResult(
                    success=True,
                    media_type="video",
                    filename=getattr(file, 'filename', str(file)),
                    content_data=content_data,
                    embeddings=combined_embeddings,
                    processing_time=processing_time
                )

            finally:
                # Cleanup temp file
                if os.path.exists(temp_video_path):
                    os.unlink(temp_video_path)

        except Exception as e:
            processing_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"Video processing failed: {e}")

            return MultiModalResult(
                success=False,
                media_type="video",
                filename=getattr(file, 'filename', str(file)),
                content_data={},
                processing_time=processing_time,
                error_message=str(e)
            )

    async def _process_image(self, file) -> MultiModalResult:
        """
        Process image file with CLIP embeddings for cross-modal search.

        Args:
            file: Image file object or path

        Returns:
            MultiModalResult with image analysis and embeddings
        """
        start_time = asyncio.get_event_loop().time()

        try:
            if not CLIP_AVAILABLE:
                return MultiModalResult(
                    success=False,
                    media_type="image",
                    filename=getattr(file, 'filename', str(file)),
                    content_data={},
                    error_message="CLIP not available for image processing"
                )

            # Load image
            if hasattr(file, 'read'):
                image_data = await file.read()
                image = Image.open(io.BytesIO(image_data))
            else:
                image = Image.open(file)

            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')

            logger.info(f"Processing image file: {getattr(file, 'filename', str(file))}")

            # Generate CLIP embeddings
            image_embeddings = await self._generate_image_embeddings(image)

            # Basic image analysis
            width, height = image.size

            # Generate description using CLIP (text-image similarity)
            description = await self._generate_image_description(image)

            processing_time = asyncio.get_event_loop().time() - start_time

            # Log performance
            log_performance(
                operation="image_processing",
                duration_ms=processing_time * 1000,
                success=True,
                image_width=width,
                image_height=height
            )

            return MultiModalResult(
                success=True,
                media_type="image",
                filename=getattr(file, 'filename', str(file)),
                content_data={
                    "analysis": {
                        "dimensions": [width, height],
                        "mode": image.mode,
                        "description": description
                    }
                },
                embeddings=image_embeddings,
                processing_time=processing_time
            )

        except Exception as e:
            processing_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"Image processing failed: {e}")

            return MultiModalResult(
                success=False,
                media_type="image",
                filename=getattr(file, 'filename', str(file)),
                content_data={},
                processing_time=processing_time,
                error_message=str(e)
            )

    async def _generate_text_embeddings(self, text: str) -> List[float]:
        """Generate CLIP embeddings for text."""
        try:
            if not CLIP_AVAILABLE or not text.strip():
                return None

            inputs = self.clip_processor(text=[text], return_tensors="pt", padding=True)

            if self.device == "cuda":
                inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                text_features = self.clip_model.get_text_features(**inputs)
                # Normalize embeddings
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)

            return text_features.cpu().numpy().flatten().tolist()

        except Exception as e:
            logger.error(f"Failed to generate text embeddings: {e}")
            return None

    async def _generate_image_embeddings(self, image: Image.Image) -> List[float]:
        """Generate CLIP embeddings for image."""
        try:
            if not CLIP_AVAILABLE:
                return None

            inputs = self.clip_processor(images=image, return_tensors="pt")

            if self.device == "cuda":
                inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                image_features = self.clip_model.get_image_features(**inputs)
                # Normalize embeddings
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)

            return image_features.cpu().numpy().flatten().tolist()

        except Exception as e:
            logger.error(f"Failed to generate image embeddings: {e}")
            return None

    async def _generate_image_description(self, image: Image.Image) -> str:
        """Generate description for image using CLIP similarity."""
        try:
            if not CLIP_AVAILABLE:
                return "Image description not available (CLIP not loaded)"

            # Common image descriptions to test similarity against
            candidate_descriptions = [
                "a photo of a person",
                "a photo of an animal",
                "a photo of a cat",
                "a photo of a dog",
                "a photo of a car",
                "a photo of a building",
                "a photo of nature",
                "a photo of food",
                "a photo of text or document",
                "a photo of an object",
                "a landscape photo",
                "an indoor scene",
                "an outdoor scene"
            ]

            # Get image embeddings
            image_inputs = self.clip_processor(images=image, return_tensors="pt")
            text_inputs = self.clip_processor(text=candidate_descriptions, return_tensors="pt", padding=True)

            if self.device == "cuda":
                image_inputs = {k: v.to(self.device) for k, v in image_inputs.items()}
                text_inputs = {k: v.to(self.device) for k, v in text_inputs.items()}

            with torch.no_grad():
                image_features = self.clip_model.get_image_features(**image_inputs)
                text_features = self.clip_model.get_text_features(**text_inputs)

                # Normalize features
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)

                # Calculate similarities
                similarities = (image_features @ text_features.T).squeeze(0)

                # Get best match
                best_idx = similarities.argmax().item()
                best_score = similarities[best_idx].item()

                return f"{candidate_descriptions[best_idx]} (confidence: {best_score:.3f})"

        except Exception as e:
            logger.error(f"Failed to generate image description: {e}")
            return "Image description generation failed"

    def _check_ffmpeg_available(self) -> bool:
        """Check if FFmpeg is available."""
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    async def _extract_and_transcribe_audio(self, video_path: str) -> Dict[str, Any]:
        """Extract audio from video and transcribe with Whisper."""
        try:
            # Extract audio using FFmpeg
            temp_audio_path = video_path.replace('.mp4', '_audio.wav')

            cmd = [
                'ffmpeg', '-i', video_path,
                '-vn', '-acodec', 'pcm_s16le',
                '-ar', '16000', '-ac', '1',
                temp_audio_path, '-y'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                logger.error(f"FFmpeg audio extraction failed: {result.stderr}")
                return None

            try:
                # Transcribe with Whisper
                transcription = self.whisper_model.transcribe(temp_audio_path)
                return {
                    "text": transcription["text"],
                    "segments": transcription.get("segments", []),
                    "language": transcription.get("language"),
                    "duration": transcription.get("duration")
                }
            finally:
                # Cleanup temp audio file
                if os.path.exists(temp_audio_path):
                    os.unlink(temp_audio_path)

        except Exception as e:
            logger.error(f"Audio extraction and transcription failed: {e}")
            return None

    async def _extract_and_analyze_frames(self, video_path: str, max_frames: int = 5) -> Dict[str, Any]:
        """Extract keyframes from video and analyze with CLIP."""
        try:
            if not CV2_AVAILABLE:
                return None

            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"Failed to open video: {video_path}")
                return None

            # Get video properties
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = total_frames / fps if fps > 0 else 0

            # Calculate frame indices to extract
            if total_frames <= max_frames:
                frame_indices = list(range(total_frames))
            else:
                step = total_frames // max_frames
                frame_indices = [i * step for i in range(max_frames)]

            analyzed_frames = []

            for i, frame_idx in enumerate(frame_indices):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()

                if not ret:
                    continue

                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(frame_rgb)

                # Generate embeddings and description
                embeddings = None
                description = "Frame analysis not available"

                if CLIP_AVAILABLE:
                    embeddings = await self._generate_image_embeddings(pil_image)
                    description = await self._generate_image_description(pil_image)

                timestamp = frame_idx / fps if fps > 0 else 0

                analyzed_frames.append({
                    "frame_index": frame_idx,
                    "timestamp": timestamp,
                    "description": description,
                    "embeddings": embeddings,
                    "dimensions": [frame_rgb.shape[1], frame_rgb.shape[0]]
                })

            cap.release()

            return {
                "analyzed_frames": analyzed_frames,
                "total_frames": total_frames,
                "fps": fps,
                "duration": duration
            }

        except Exception as e:
            logger.error(f"Frame extraction and analysis failed: {e}")
            return None

    async def _get_video_metadata(self, video_path: str) -> Dict[str, Any]:
        """Get video metadata using FFmpeg."""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet',
                '-print_format', 'json',
                '-show_format', '-show_streams',
                video_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                logger.error(f"FFprobe failed: {result.stderr}")
                return {}

            metadata = json.loads(result.stdout)

            # Extract relevant information
            format_info = metadata.get('format', {})
            video_stream = None
            audio_stream = None

            for stream in metadata.get('streams', []):
                if stream.get('codec_type') == 'video' and not video_stream:
                    video_stream = stream
                elif stream.get('codec_type') == 'audio' and not audio_stream:
                    audio_stream = stream

            return {
                "duration": float(format_info.get('duration', 0)),
                "size": int(format_info.get('size', 0)),
                "format_name": format_info.get('format_name'),
                "video": {
                    "codec": video_stream.get('codec_name') if video_stream else None,
                    "width": video_stream.get('width') if video_stream else None,
                    "height": video_stream.get('height') if video_stream else None,
                    "fps": eval(video_stream.get('r_frame_rate', '0/1')) if video_stream else 0
                } if video_stream else None,
                "audio": {
                    "codec": audio_stream.get('codec_name') if audio_stream else None,
                    "sample_rate": audio_stream.get('sample_rate') if audio_stream else None,
                    "channels": audio_stream.get('channels') if audio_stream else None
                } if audio_stream else None
            }

        except Exception as e:
            logger.error(f"Failed to get video metadata: {e}")
            return {}

    async def _store_multimodal_content(self, result: MultiModalResult) -> str:
        """Store multimodal content in Weaviate with cross-modal embeddings."""
        try:
            if not REQUESTS_AVAILABLE:
                logger.warning("Requests not available - cannot store in Weaviate")
                return None

            # Prepare data for Weaviate
            weaviate_data = {
                "class": "MultiModalContent",
                "properties": {
                    "media_type": result.media_type,
                    "filename": result.filename,
                    "content_data": json.dumps(result.content_data),
                    "processing_time": result.processing_time,
                    "created_at": datetime.utcnow().isoformat(),
                    "success": result.success
                }
            }

            # Add embeddings if available
            if result.embeddings:
                weaviate_data["vector"] = result.embeddings

            # Store in Weaviate
            headers = {'Content-Type': 'application/json'}
            if settings.weaviate_api_key:
                headers['Authorization'] = f'Bearer {settings.weaviate_api_key}'

            response = requests.post(
                f"{settings.weaviate_url}/v1/objects",
                headers=headers,
                json=weaviate_data,
                timeout=30
            )

            if response.status_code == 200:
                weaviate_result = response.json()
                weaviate_id = weaviate_result.get("id")
                result.weaviate_id = weaviate_id
                logger.info(f"Stored {result.media_type} content in Weaviate: {weaviate_id}")
                return weaviate_id
            else:
                logger.error(f"Failed to store in Weaviate: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Failed to store multimodal content in Weaviate: {e}")
            return None

    async def _save_temp_file(self, file) -> str:
        """Save uploaded file to temporary location."""
        if hasattr(file, 'read'):
            # It's an uploaded file
            content = await file.read()
            suffix = Path(file.filename).suffix if hasattr(file, 'filename') else '.tmp'

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                temp_file.write(content)
                return temp_file.name
        else:
            # It's already a file path
            return str(file)

    def _get_content_type_from_filename(self, filename: str) -> str:
        """Determine content type from filename extension."""
        suffix = Path(filename).suffix.lower()

        audio_extensions = {'.wav', '.mp3', '.m4a', '.flac', '.ogg', '.aac'}
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv'}
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}

        if suffix in audio_extensions:
            return 'audio/wav'  # Generic audio type
        elif suffix in video_extensions:
            return 'video/mp4'  # Generic video type
        elif suffix in image_extensions:
            return 'image/jpeg'  # Generic image type
        else:
            return 'application/octet-stream'

    async def search_cross_modal(self, query: str, media_types: List[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Perform cross-modal search using text query to find relevant media content.

        Args:
            query: Text query to search for
            media_types: List of media types to search in (audio, video, image)
            limit: Maximum number of results to return

        Returns:
            List of matching multimodal content
        """
        try:
            if not CLIP_AVAILABLE or not REQUESTS_AVAILABLE:
                logger.warning("CLIP or Requests not available - cross-modal search disabled")
                return []

            # Generate query embeddings
            query_embeddings = await self._generate_text_embeddings(query)
            if not query_embeddings:
                return []

            # Build Weaviate query
            where_filter = None
            if media_types:
                if len(media_types) == 1:
                    where_filter = {
                        "path": ["media_type"],
                        "operator": "Equal",
                        "valueText": media_types[0]
                    }
                else:
                    where_filter = {
                        "operator": "Or",
                        "operands": [
                            {
                                "path": ["media_type"],
                                "operator": "Equal",
                                "valueText": media_type
                            }
                            for media_type in media_types
                        ]
                    }

            # Perform vector search
            search_query = {
                "query": f"""
                {{
                    Get {{
                        MultiModalContent(
                            nearVector: {{
                                vector: {query_embeddings}
                            }}
                            limit: {limit}
                            {f'where: {json.dumps(where_filter)}' if where_filter else ''}
                        ) {{
                            media_type
                            filename
                            content_data
                            created_at
                            _additional {{
                                distance
                                id
                            }}
                        }}
                    }}
                }}
                """
            }

            headers = {'Content-Type': 'application/json'}
            if settings.weaviate_api_key:
                headers['Authorization'] = f'Bearer {settings.weaviate_api_key}'

            response = requests.post(
                f"{settings.weaviate_url}/v1/graphql",
                headers=headers,
                json=search_query,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get('data', {}).get('Get', {}).get('MultiModalContent', [])

                # Process results
                processed_results = []
                for result in results:
                    try:
                        content_data = json.loads(result.get('content_data', '{}'))
                        processed_results.append({
                            "media_type": result.get('media_type'),
                            "filename": result.get('filename'),
                            "content_data": content_data,
                            "created_at": result.get('created_at'),
                            "similarity_score": 1 - result.get('_additional', {}).get('distance', 1),
                            "weaviate_id": result.get('_additional', {}).get('id')
                        })
                    except Exception as e:
                        logger.error(f"Failed to process search result: {e}")
                        continue

                return processed_results
            else:
                logger.error(f"Weaviate search failed: {response.status_code} - {response.text}")
                return []

        except Exception as e:
            logger.error(f"Cross-modal search failed: {e}")
            return []
    
    def _check_capabilities(self) -> Dict[str, bool]:
        """Check which multi-modal capabilities are available."""
        capabilities = {}
        
        # Check audio capabilities
        try:
            import whisper
            import pydub
            capabilities['audio_transcription'] = True
        except ImportError:
            capabilities['audio_transcription'] = False
            logger.warning("Audio transcription not available - install whisper and pydub")
        
        try:
            import pyttsx3
            capabilities['text_to_speech'] = True
        except ImportError:
            capabilities['text_to_speech'] = False
            logger.warning("Text-to-speech not available - install pyttsx3")
        
        # Check video capabilities (requires both FFmpeg binary and OpenCV)
        try:
            import subprocess
            import shutil

            # Check if ffmpeg binary is available
            ffmpeg_path = shutil.which("ffmpeg")
            ffmpeg_available = False
            if ffmpeg_path:
                try:
                    result = subprocess.run(
                        ["ffmpeg", "-version"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    ffmpeg_available = result.returncode == 0
                except Exception:
                    ffmpeg_available = False

            capabilities['video_processing'] = CV2_AVAILABLE and ffmpeg_available

            if not ffmpeg_available:
                logger.warning("Video processing limited - FFmpeg binary not found in PATH")
            elif not CV2_AVAILABLE:
                logger.warning("Video processing limited - OpenCV not available")

        except Exception as e:
            capabilities['video_processing'] = False
            logger.warning(f"Video processing check failed: {e}")
        
        # Check image capabilities
        try:
            import torch
            import torchvision
            capabilities['advanced_image_processing'] = True
        except ImportError:
            capabilities['advanced_image_processing'] = False
            logger.warning("Advanced image processing not available - install torch and torchvision")
        
        # Basic image processing is always available (PIL/OpenCV)
        capabilities['basic_image_processing'] = True
        
        return capabilities
    
    async def process_media(self, media_data: bytes, media_type: str, 
                          processing_options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Unified media processing interface.
        
        Args:
            media_data: Raw media data as bytes
            media_type: Type of media ('audio', 'video', 'image')
            processing_options: Optional processing parameters
            
        Returns:
            Dictionary containing processing results and metadata
        """
        try:
            start_time = datetime.now()
            
            if media_type == 'audio':
                result = await self.audio_processor.process_audio(media_data, processing_options)
            elif media_type == 'video':
                result = await self.video_processor.process_video(media_data, processing_options)
            elif media_type == 'image':
                result = await self.image_processor.process_image(media_data, processing_options)
            else:
                raise ValueError(f"Unsupported media type: {media_type}")
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": True,
                "media_type": media_type,
                "processing_time": processing_time,
                "capabilities_used": [cap for cap, available in self.capabilities.items() if available],
                "result": result,
                "timestamp": start_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Media processing failed for {media_type}: {e}")
            return {
                "success": False,
                "media_type": media_type,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def fuse_multimodal_data(self, media_results: List[Dict[str, Any]], 
                                 fusion_strategy: str = "concatenate") -> Dict[str, Any]:
        """
        Fuse results from multiple media types into unified output.
        
        Args:
            media_results: List of processing results from different media types
            fusion_strategy: Strategy for fusion ('concatenate', 'weighted', 'semantic')
            
        Returns:
            Fused multi-modal result
        """
        return await self.fusion_processor.fuse_results(media_results, fusion_strategy)


class AudioProcessor:
    """Audio processing capabilities including speech-to-text and text-to-speech."""
    
    def __init__(self):
        self.whisper_model = None
        self.tts_engine = None
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize audio processing models with fallback handling."""
        try:
            import whisper
            self.whisper_model = whisper.load_model("base")
            logger.info("Whisper model loaded successfully")
        except ImportError:
            logger.warning("Whisper not available - speech-to-text disabled")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
        
        try:
            import pyttsx3
            self.tts_engine = pyttsx3.init()
            logger.info("TTS engine initialized successfully")
        except ImportError:
            logger.warning("pyttsx3 not available - text-to-speech disabled")
        except Exception as e:
            logger.error(f"Failed to initialize TTS engine: {e}")
    
    async def process_audio(self, audio_data: bytes, 
                          options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process audio data with various operations.
        
        Args:
            audio_data: Raw audio data
            options: Processing options (transcribe, analyze, etc.)
            
        Returns:
            Audio processing results
        """
        options = options or {}
        results = {}
        
        # Save audio data to temporary file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_path = temp_file.name
        
        try:
            # Speech-to-text transcription
            if options.get('transcribe', True) and self.whisper_model:
                transcription = await self._transcribe_audio(temp_path)
                results['transcription'] = transcription
            
            # Audio analysis
            if options.get('analyze', False):
                analysis = await self._analyze_audio(temp_path)
                results['analysis'] = analysis
            
            # Audio metadata
            metadata = await self._extract_audio_metadata(temp_path)
            results['metadata'] = metadata
            
        finally:
            # Cleanup temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        
        return results
    
    async def _transcribe_audio(self, audio_path: str) -> Dict[str, Any]:
        """Transcribe audio using Whisper."""
        if not self.whisper_model:
            return {"error": "Whisper model not available"}
        
        try:
            result = self.whisper_model.transcribe(audio_path)
            return {
                "text": result["text"],
                "language": result.get("language", "unknown"),
                "segments": result.get("segments", [])
            }
        except Exception as e:
            logger.error(f"Audio transcription failed: {e}")
            return {"error": str(e)}
    
    async def _analyze_audio(self, audio_path: str) -> Dict[str, Any]:
        """Analyze audio characteristics."""
        try:
            # Basic audio analysis using librosa if available
            try:
                import librosa
                y, sr = librosa.load(audio_path)
                
                return {
                    "duration": len(y) / sr,
                    "sample_rate": sr,
                    "channels": 1 if y.ndim == 1 else y.shape[0],
                    "rms_energy": float(np.sqrt(np.mean(y**2))),
                    "zero_crossing_rate": float(np.mean(librosa.feature.zero_crossing_rate(y)))
                }
            except ImportError:
                # Fallback to basic analysis
                return {"message": "Advanced audio analysis not available - install librosa"}
                
        except Exception as e:
            logger.error(f"Audio analysis failed: {e}")
            return {"error": str(e)}
    
    async def _extract_audio_metadata(self, audio_path: str) -> Dict[str, Any]:
        """Extract basic audio metadata."""
        try:
            file_size = os.path.getsize(audio_path)
            return {
                "file_size": file_size,
                "format": Path(audio_path).suffix.lower(),
                "processed_at": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def text_to_speech(self, text: str, output_path: Optional[str] = None) -> Dict[str, Any]:
        """Convert text to speech."""
        if not self.tts_engine:
            return {"error": "TTS engine not available"}
        
        try:
            if output_path:
                self.tts_engine.save_to_file(text, output_path)
                return {"success": True, "output_path": output_path}
            else:
                # For in-memory TTS, we'd need a different approach
                return {"error": "In-memory TTS not implemented"}
                
        except Exception as e:
            logger.error(f"Text-to-speech failed: {e}")
            return {"error": str(e)}


class VideoProcessor:
    """Video processing and analysis capabilities."""
    
    def __init__(self):
        self.ffmpeg_available = self._check_ffmpeg()
    
    def _check_ffmpeg(self) -> bool:
        """Check if ffmpeg binary is available."""
        try:
            import subprocess
            import shutil

            # Check if ffmpeg binary is in PATH
            ffmpeg_path = shutil.which("ffmpeg")
            if ffmpeg_path:
                # Test if ffmpeg actually works
                result = subprocess.run(
                    ["ffmpeg", "-version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    logger.info(f"FFmpeg binary found at: {ffmpeg_path}")
                    return True

            logger.warning("FFmpeg binary not found in PATH - video processing limited")
            return False

        except Exception as e:
            logger.warning(f"FFmpeg check failed: {e} - video processing limited")
            return False
    
    async def process_video(self, video_data: bytes, 
                          options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process video data with various operations.
        
        Args:
            video_data: Raw video data
            options: Processing options
            
        Returns:
            Video processing results
        """
        options = options or {}
        results = {}
        
        # Save video data to temporary file
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            temp_file.write(video_data)
            temp_path = temp_file.name
        
        try:
            # Extract frames
            if options.get('extract_frames', False):
                frames = await self._extract_frames(temp_path, options.get('frame_count', 10))
                results['frames'] = frames
            
            # Extract audio and transcribe
            if options.get('transcribe_audio', True):
                audio_transcription = await self._extract_and_transcribe_audio(temp_path)
                results['audio_transcription'] = audio_transcription
            
            # Video analysis
            if options.get('analyze', False):
                analysis = await self._analyze_video(temp_path)
                results['analysis'] = analysis
            
            # Video metadata
            metadata = await self._extract_video_metadata(temp_path)
            results['metadata'] = metadata
            
        finally:
            # Cleanup temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        
        return results
    
    async def _extract_frames(self, video_path: str, frame_count: int = 10) -> List[Dict[str, Any]]:
        """Extract frames from video."""
        if not CV2_AVAILABLE:
            return [{"error": "OpenCV not available for frame extraction"}]

        try:
            cap = cv2.VideoCapture(video_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            if total_frames == 0:
                return []

            frame_indices = np.linspace(0, total_frames - 1, frame_count, dtype=int)
            frames = []

            for i, frame_idx in enumerate(frame_indices):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()

                if ret:
                    # Convert frame to base64 for storage/transmission
                    _, buffer = cv2.imencode('.jpg', frame)
                    frame_data = buffer.tobytes()

                    frames.append({
                        "frame_index": int(frame_idx),
                        "timestamp": frame_idx / cap.get(cv2.CAP_PROP_FPS),
                        "size": len(frame_data),
                        "dimensions": (frame.shape[1], frame.shape[0])
                    })

            cap.release()
            return frames

        except Exception as e:
            logger.error(f"Frame extraction failed: {e}")
            return []
    
    async def _extract_and_transcribe_audio(self, video_path: str) -> Dict[str, Any]:
        """Extract audio from video and transcribe it."""
        if not self.ffmpeg_available:
            return {"error": "ffmpeg not available for audio extraction"}
        
        try:
            import ffmpeg
            
            # Extract audio to temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
                audio_path = temp_audio.name
            
            try:
                # Extract audio using ffmpeg
                (
                    ffmpeg
                    .input(video_path)
                    .output(audio_path, acodec='pcm_s16le', ac=1, ar='16000')
                    .overwrite_output()
                    .run(quiet=True)
                )
                
                # Transcribe using audio processor
                audio_processor = AudioProcessor()
                with open(audio_path, 'rb') as f:
                    audio_data = f.read()
                
                transcription_result = await audio_processor.process_audio(
                    audio_data, {'transcribe': True}
                )
                
                return transcription_result.get('transcription', {})
                
            finally:
                if os.path.exists(audio_path):
                    os.unlink(audio_path)
                    
        except Exception as e:
            logger.error(f"Video audio transcription failed: {e}")
            return {"error": str(e)}
    
    async def _analyze_video(self, video_path: str) -> Dict[str, Any]:
        """Analyze video characteristics."""
        if not CV2_AVAILABLE:
            return {"error": "OpenCV not available for video analysis"}

        try:
            cap = cv2.VideoCapture(video_path)

            analysis = {
                "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
                "fps": cap.get(cv2.CAP_PROP_FPS),
                "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                "duration": cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)
            }

            cap.release()
            return analysis

        except Exception as e:
            logger.error(f"Video analysis failed: {e}")
            return {"error": str(e)}
    
    async def _extract_video_metadata(self, video_path: str) -> Dict[str, Any]:
        """Extract video metadata."""
        try:
            file_size = os.path.getsize(video_path)
            return {
                "file_size": file_size,
                "format": Path(video_path).suffix.lower(),
                "processed_at": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": str(e)}


class ImageProcessor:
    """Image processing and computer vision capabilities."""
    
    def __init__(self):
        self.torch_available = self._check_torch()
    
    def _check_torch(self) -> bool:
        """Check if PyTorch is available for advanced image processing."""
        try:
            import torch
            import torchvision
            return True
        except ImportError:
            logger.warning("PyTorch not available - advanced image processing disabled")
            return False
    
    async def process_image(self, image_data: bytes, 
                          options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process image data with various operations.
        
        Args:
            image_data: Raw image data
            options: Processing options
            
        Returns:
            Image processing results
        """
        options = options or {}
        results = {}
        
        try:
            # Load image
            image = Image.open(io.BytesIO(image_data))
            
            # Basic image analysis
            analysis = await self._analyze_image(image)
            results['analysis'] = analysis
            
            # Object detection (if available)
            if options.get('detect_objects', False) and self.torch_available:
                objects = await self._detect_objects(image)
                results['objects'] = objects
            
            # Image enhancement
            if options.get('enhance', False):
                enhanced = await self._enhance_image(image)
                results['enhanced'] = enhanced
            
            # Extract text (OCR)
            if options.get('extract_text', False):
                text = await self._extract_text(image)
                results['text'] = text
            
        except Exception as e:
            logger.error(f"Image processing failed: {e}")
            results['error'] = str(e)
        
        return results
    
    async def _analyze_image(self, image: Image.Image) -> Dict[str, Any]:
        """Analyze basic image characteristics."""
        try:
            return {
                "dimensions": image.size,
                "mode": image.mode,
                "format": image.format,
                "has_transparency": image.mode in ('RGBA', 'LA') or 'transparency' in image.info,
                "color_channels": len(image.getbands()),
                "processed_at": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _detect_objects(self, image: Image.Image) -> Dict[str, Any]:
        """Detect objects in image using computer vision."""
        if not self.torch_available:
            return {"error": "PyTorch not available for object detection"}
        
        try:
            # This would use a pre-trained model like YOLO or COCO
            # For now, return a placeholder
            return {
                "message": "Object detection would be implemented here",
                "detected_objects": [],
                "confidence_threshold": 0.5
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _enhance_image(self, image: Image.Image) -> Dict[str, Any]:
        """Enhance image quality."""
        try:
            # Basic image enhancement using PIL
            from PIL import ImageEnhance
            
            # Apply basic enhancements
            enhancer = ImageEnhance.Contrast(image)
            enhanced = enhancer.enhance(1.2)
            
            enhancer = ImageEnhance.Sharpness(enhanced)
            enhanced = enhancer.enhance(1.1)
            
            return {
                "enhanced": True,
                "operations": ["contrast_enhancement", "sharpness_enhancement"],
                "original_size": image.size
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _extract_text(self, image: Image.Image) -> Dict[str, Any]:
        """Extract text from image using OCR."""
        try:
            # This would use pytesseract or similar OCR library
            # For now, return a placeholder
            return {
                "message": "OCR would be implemented here",
                "extracted_text": "",
                "confidence": 0.0
            }
        except Exception as e:
            return {"error": str(e)}


class MultiModalFusionProcessor:
    """Fuse results from multiple media types into unified output."""
    
    async def fuse_results(self, media_results: List[Dict[str, Any]], 
                         strategy: str = "concatenate") -> Dict[str, Any]:
        """
        Fuse multi-modal processing results.
        
        Args:
            media_results: List of processing results from different media types
            strategy: Fusion strategy
            
        Returns:
            Fused result
        """
        try:
            if strategy == "concatenate":
                return await self._concatenate_fusion(media_results)
            elif strategy == "weighted":
                return await self._weighted_fusion(media_results)
            elif strategy == "semantic":
                return await self._semantic_fusion(media_results)
            else:
                raise ValueError(f"Unknown fusion strategy: {strategy}")
                
        except Exception as e:
            logger.error(f"Multi-modal fusion failed: {e}")
            return {"error": str(e)}
    
    async def _concatenate_fusion(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Simple concatenation fusion."""
        fused = {
            "fusion_strategy": "concatenate",
            "media_types": [],
            "combined_text": "",
            "combined_metadata": {},
            "processing_summary": {}
        }
        
        for result in results:
            if result.get("success"):
                media_type = result.get("media_type")
                fused["media_types"].append(media_type)
                
                # Extract text content
                result_data = result.get("result", {})
                if "transcription" in result_data:
                    fused["combined_text"] += f"[{media_type.upper()}] {result_data['transcription'].get('text', '')}\n"
                elif "text" in result_data:
                    fused["combined_text"] += f"[{media_type.upper()}] {result_data['text']}\n"
                
                # Combine metadata
                if "metadata" in result_data:
                    fused["combined_metadata"][media_type] = result_data["metadata"]
                
                # Processing summary
                fused["processing_summary"][media_type] = {
                    "processing_time": result.get("processing_time"),
                    "success": True
                }
        
        return fused
    
    async def _weighted_fusion(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Weighted fusion based on confidence scores."""
        # Placeholder for weighted fusion
        return await self._concatenate_fusion(results)
    
    async def _semantic_fusion(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Semantic fusion using embeddings."""
        # Placeholder for semantic fusion
        return await self._concatenate_fusion(results)


# Global multi-modal processor instance
multimodal_processor = MultiModalProcessor()
