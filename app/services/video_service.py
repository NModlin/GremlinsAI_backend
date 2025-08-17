"""
Video Processing Service with Frame Extraction and Scene Detection

This module provides comprehensive video processing capabilities including:
- Scene detection using multiple algorithms
- Intelligent key frame extraction
- Video format support and optimization
- Memory-efficient processing for large files
- Performance monitoring and quality assessment
"""

import logging
import time
import os
import tempfile
import uuid
import math
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import asyncio

# Video processing libraries
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logging.warning("OpenCV not available. Video processing will be disabled.")

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    raise ImportError("numpy is required for video processing")

# Scene detection
try:
    from scenedetect import VideoManager, SceneManager
    from scenedetect.detectors import ContentDetector, ThresholdDetector
    from scenedetect.video_splitter import split_video_ffmpeg
    SCENEDETECT_AVAILABLE = True
except ImportError:
    SCENEDETECT_AVAILABLE = False
    logging.warning("PySceneDetect not available. Advanced scene detection will be disabled.")

# Image processing
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logging.warning("PIL not available. Image processing will be limited.")

logger = logging.getLogger(__name__)


class SceneDetectionMethod(Enum):
    """Available scene detection methods."""
    CONTENT_DETECTOR = "content"
    THRESHOLD_DETECTOR = "threshold"
    ADAPTIVE_DETECTOR = "adaptive"
    HISTOGRAM_DETECTOR = "histogram"


class FrameExtractionMethod(Enum):
    """Frame extraction methods."""
    UNIFORM = "uniform"          # Extract frames at uniform intervals
    KEYFRAME = "keyframe"        # Extract actual video keyframes
    HISTOGRAM = "histogram"      # Extract frames with diverse histograms
    MOTION = "motion"           # Extract frames with significant motion
    ADAPTIVE = "adaptive"       # Combine multiple methods


class VideoFormat(Enum):
    """Supported video formats."""
    MP4 = "mp4"
    AVI = "avi"
    MOV = "mov"
    MKV = "mkv"
    WMV = "wmv"
    FLV = "flv"
    WEBM = "webm"


@dataclass
class KeyFrame:
    """Individual key frame with metadata."""
    
    # Frame information
    frame_number: int
    timestamp: float
    frame_path: str
    
    # Frame characteristics
    width: int
    height: int
    channels: int
    
    # Quality metrics
    sharpness_score: float = 0.0
    brightness_score: float = 0.0
    contrast_score: float = 0.0
    histogram_diversity: float = 0.0
    
    # Motion information
    motion_score: float = 0.0
    is_keyframe: bool = False
    
    # Metadata
    frame_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert frame to dictionary."""
        return {
            "frame_id": self.frame_id,
            "frame_number": self.frame_number,
            "timestamp": self.timestamp,
            "frame_path": self.frame_path,
            "width": self.width,
            "height": self.height,
            "channels": self.channels,
            "sharpness_score": self.sharpness_score,
            "brightness_score": self.brightness_score,
            "contrast_score": self.contrast_score,
            "histogram_diversity": self.histogram_diversity,
            "motion_score": self.motion_score,
            "is_keyframe": self.is_keyframe,
            "metadata": self.metadata
        }


@dataclass
class VideoScene:
    """Individual video scene with timing and content."""
    
    # Scene information
    scene_number: int
    start_time: float
    end_time: float
    duration: float
    
    # Frame information
    start_frame: int
    end_frame: int
    key_frames: List[KeyFrame]
    
    # Scene characteristics
    scene_type: str = "unknown"  # action, dialogue, transition, etc.
    motion_intensity: float = 0.0
    color_diversity: float = 0.0
    brightness_variation: float = 0.0
    
    # Quality metrics
    scene_quality: float = 0.0
    frame_count: int = 0
    
    # Metadata
    scene_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert scene to dictionary."""
        return {
            "scene_id": self.scene_id,
            "scene_number": self.scene_number,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "start_frame": self.start_frame,
            "end_frame": self.end_frame,
            "key_frames": [frame.to_dict() for frame in self.key_frames],
            "scene_type": self.scene_type,
            "motion_intensity": self.motion_intensity,
            "color_diversity": self.color_diversity,
            "brightness_variation": self.brightness_variation,
            "scene_quality": self.scene_quality,
            "frame_count": self.frame_count,
            "metadata": self.metadata
        }


@dataclass
class VideoProcessingConfig:
    """Configuration for video processing."""
    
    # Scene detection settings
    scene_detection_method: SceneDetectionMethod = SceneDetectionMethod.CONTENT_DETECTOR
    scene_threshold: float = 30.0  # Sensitivity for scene detection
    min_scene_length: float = 1.0  # Minimum scene length in seconds
    
    # Frame extraction settings
    frame_extraction_method: FrameExtractionMethod = FrameExtractionMethod.ADAPTIVE
    frames_per_scene: int = 5  # Number of key frames per scene
    max_frames_total: int = 100  # Maximum total frames to extract
    
    # Quality settings
    min_frame_quality: float = 0.5
    target_frame_width: int = 1280
    target_frame_height: int = 720
    
    # Performance settings
    max_file_size_gb: float = 2.0
    processing_timeout_s: int = 600  # 10 minutes
    memory_limit_mb: int = 2048
    
    # Output settings
    save_frames: bool = True
    frame_format: str = "jpg"
    frame_quality: int = 85
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "scene_detection_method": self.scene_detection_method.value,
            "scene_threshold": self.scene_threshold,
            "min_scene_length": self.min_scene_length,
            "frame_extraction_method": self.frame_extraction_method.value,
            "frames_per_scene": self.frames_per_scene,
            "max_frames_total": self.max_frames_total,
            "min_frame_quality": self.min_frame_quality,
            "target_frame_width": self.target_frame_width,
            "target_frame_height": self.target_frame_height,
            "max_file_size_gb": self.max_file_size_gb,
            "processing_timeout_s": self.processing_timeout_s,
            "memory_limit_mb": self.memory_limit_mb,
            "save_frames": self.save_frames,
            "frame_format": self.frame_format,
            "frame_quality": self.frame_quality
        }


@dataclass
class VideoProcessingResult:
    """Complete video processing result."""
    
    # Core results
    scenes: List[VideoScene]
    total_key_frames: int
    
    # Video information
    video_file_path: str
    video_duration: float
    video_format: str
    frame_rate: float
    total_frames: int
    
    # Video properties
    width: int
    height: int
    file_size_mb: float
    
    # Processing metadata
    processing_time: float
    scene_detection_method: str
    frame_extraction_method: str
    
    # Quality metrics
    scene_detection_confidence: float
    frame_extraction_quality: float
    overall_video_quality: float
    
    # Performance metrics
    processing_speed_ratio: float  # processing_time / video_duration
    frames_per_second_processed: float
    memory_usage_mb: float
    
    # Configuration used
    config_used: VideoProcessingConfig
    
    # Output paths
    frames_directory: Optional[str] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "scenes": [scene.to_dict() for scene in self.scenes],
            "total_key_frames": self.total_key_frames,
            "video_file_path": self.video_file_path,
            "video_duration": self.video_duration,
            "video_format": self.video_format,
            "frame_rate": self.frame_rate,
            "total_frames": self.total_frames,
            "width": self.width,
            "height": self.height,
            "file_size_mb": self.file_size_mb,
            "processing_time": self.processing_time,
            "scene_detection_method": self.scene_detection_method,
            "frame_extraction_method": self.frame_extraction_method,
            "scene_detection_confidence": self.scene_detection_confidence,
            "frame_extraction_quality": self.frame_extraction_quality,
            "overall_video_quality": self.overall_video_quality,
            "processing_speed_ratio": self.processing_speed_ratio,
            "frames_per_second_processed": self.frames_per_second_processed,
            "memory_usage_mb": self.memory_usage_mb,
            "config_used": self.config_used.to_dict(),
            "frames_directory": self.frames_directory,
            "metadata": self.metadata
        }


class VideoService:
    """
    Comprehensive video processing service with scene detection and frame extraction.
    
    Provides advanced video processing capabilities:
    - Scene detection using multiple algorithms
    - Intelligent key frame extraction
    - Video format support and optimization
    - Memory-efficient processing for large files
    - Performance monitoring and quality assessment
    """
    
    def __init__(self, config: Optional[VideoProcessingConfig] = None):
        """Initialize video service."""
        self.config = config or VideoProcessingConfig()
        
        # Performance metrics
        self.metrics = {
            "total_videos_processed": 0,
            "total_processing_time": 0.0,
            "total_video_duration": 0.0,
            "total_scenes_detected": 0,
            "total_frames_extracted": 0,
            "average_quality": 0.0,
            "average_processing_speed": 0.0
        }
        
        logger.info(f"VideoService initialized with scene detection: {self.config.scene_detection_method.value}")
    
    def _validate_dependencies(self):
        """Validate required dependencies."""
        if not CV2_AVAILABLE:
            raise ImportError("OpenCV is not available. Please install with: pip install opencv-python")
        
        if not NUMPY_AVAILABLE:
            raise ImportError("numpy is not available. Please install with: pip install numpy")
        
        if not SCENEDETECT_AVAILABLE:
            logger.warning("PySceneDetect not available. Using basic scene detection.")
        
        if not PIL_AVAILABLE:
            logger.warning("PIL not available. Frame processing will be limited.")

    async def process_video(
        self,
        video_file_path: str,
        config: Optional[VideoProcessingConfig] = None
    ) -> VideoProcessingResult:
        """
        Process video file with scene detection and frame extraction.

        Args:
            video_file_path: Path to video file
            config: Optional processing configuration

        Returns:
            VideoProcessingResult with scenes and key frames
        """
        start_time = time.time()
        processing_config = config or self.config

        try:
            logger.info(f"Processing video file: {video_file_path}")

            # Validate dependencies
            self._validate_dependencies()

            # Validate and analyze video
            video_info = self._validate_video_file(video_file_path, processing_config)

            # Detect scenes
            scenes_data = await self._detect_scenes(video_file_path, processing_config)

            # Extract key frames for each scene
            scenes_with_frames = await self._extract_key_frames(
                video_file_path,
                scenes_data,
                processing_config
            )

            # Calculate quality metrics
            quality_metrics = self._calculate_quality_metrics(
                scenes_with_frames,
                video_info
            )

            # Calculate performance metrics
            processing_time = time.time() - start_time
            processing_speed_ratio = processing_time / video_info["duration"]
            frames_per_second_processed = video_info["total_frames"] / processing_time if processing_time > 0 else 0

            # Count total key frames
            total_key_frames = sum(len(scene.key_frames) for scene in scenes_with_frames)

            # Create result
            result = VideoProcessingResult(
                scenes=scenes_with_frames,
                total_key_frames=total_key_frames,
                video_file_path=video_file_path,
                video_duration=video_info["duration"],
                video_format=video_info["format"],
                frame_rate=video_info["frame_rate"],
                total_frames=video_info["total_frames"],
                width=video_info["width"],
                height=video_info["height"],
                file_size_mb=video_info["file_size_mb"],
                processing_time=processing_time,
                scene_detection_method=processing_config.scene_detection_method.value,
                frame_extraction_method=processing_config.frame_extraction_method.value,
                scene_detection_confidence=quality_metrics["scene_detection_confidence"],
                frame_extraction_quality=quality_metrics["frame_extraction_quality"],
                overall_video_quality=quality_metrics["overall_video_quality"],
                processing_speed_ratio=processing_speed_ratio,
                frames_per_second_processed=frames_per_second_processed,
                memory_usage_mb=quality_metrics["memory_usage_mb"],
                config_used=processing_config,
                frames_directory=quality_metrics.get("frames_directory"),
                metadata={
                    "scenes_detected": len(scenes_with_frames),
                    "average_scene_duration": np.mean([s.duration for s in scenes_with_frames]) if scenes_with_frames else 0,
                    "processing_method": "opencv_scenedetect",
                    "file_size_gb": video_info["file_size_mb"] / 1024
                }
            )

            # Update metrics
            self._update_metrics(result)

            logger.info(f"Video processing completed: {processing_time:.2f}s, "
                       f"{len(scenes_with_frames)} scenes, "
                       f"{total_key_frames} key frames")

            return result

        except Exception as e:
            logger.error(f"Video processing failed: {e}")
            raise

    def _validate_video_file(
        self,
        video_file_path: str,
        config: VideoProcessingConfig
    ) -> Dict[str, Any]:
        """Validate video file and extract basic information."""

        if not os.path.exists(video_file_path):
            raise FileNotFoundError(f"Video file not found: {video_file_path}")

        # Check file size
        file_size_mb = os.path.getsize(video_file_path) / (1024 * 1024)
        file_size_gb = file_size_mb / 1024

        if file_size_gb > config.max_file_size_gb:
            raise ValueError(f"File too large: {file_size_gb:.1f}GB > {config.max_file_size_gb}GB")

        # Get video information using OpenCV
        try:
            cap = cv2.VideoCapture(video_file_path)

            if not cap.isOpened():
                raise ValueError("Could not open video file")

            # Get video properties
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            duration = frame_count / fps if fps > 0 else 0

            # Detect format
            file_extension = Path(video_file_path).suffix.lower().lstrip('.')
            video_format = file_extension if file_extension in [f.value for f in VideoFormat] else "unknown"

            cap.release()

            return {
                "duration": duration,
                "frame_rate": fps,
                "total_frames": frame_count,
                "width": width,
                "height": height,
                "format": video_format,
                "file_size_mb": file_size_mb
            }

        except Exception as e:
            raise ValueError(f"Invalid video file: {e}")

    async def _detect_scenes(
        self,
        video_file_path: str,
        config: VideoProcessingConfig
    ) -> List[Dict[str, Any]]:
        """Detect scenes in video using specified method."""

        try:
            if SCENEDETECT_AVAILABLE and config.scene_detection_method in [
                SceneDetectionMethod.CONTENT_DETECTOR,
                SceneDetectionMethod.THRESHOLD_DETECTOR
            ]:
                return await self._detect_scenes_with_scenedetect(video_file_path, config)
            else:
                return await self._detect_scenes_basic(video_file_path, config)

        except Exception as e:
            logger.error(f"Scene detection failed: {e}")
            # Fallback to basic scene detection
            return await self._detect_scenes_basic(video_file_path, config)

    async def _detect_scenes_with_scenedetect(
        self,
        video_file_path: str,
        config: VideoProcessingConfig
    ) -> List[Dict[str, Any]]:
        """Detect scenes using PySceneDetect library."""

        logger.debug("Starting scene detection with PySceneDetect")

        # Create video manager
        video_manager = VideoManager([video_file_path])
        scene_manager = SceneManager()

        # Add detector based on configuration
        if config.scene_detection_method == SceneDetectionMethod.CONTENT_DETECTOR:
            scene_manager.add_detector(ContentDetector(threshold=config.scene_threshold))
        elif config.scene_detection_method == SceneDetectionMethod.THRESHOLD_DETECTOR:
            scene_manager.add_detector(ThresholdDetector(threshold=config.scene_threshold))

        # Start video manager
        video_manager.start()

        # Perform scene detection
        scene_manager.detect_scenes(frame_source=video_manager)

        # Get scene list
        scene_list = scene_manager.get_scene_list()

        # Convert to our format
        scenes_data = []
        for i, (start_time, end_time) in enumerate(scene_list):
            scene_data = {
                "scene_number": i + 1,
                "start_time": start_time.get_seconds(),
                "end_time": end_time.get_seconds(),
                "duration": (end_time - start_time).get_seconds(),
                "start_frame": start_time.get_frames(),
                "end_frame": end_time.get_frames()
            }

            # Filter by minimum scene length
            if scene_data["duration"] >= config.min_scene_length:
                scenes_data.append(scene_data)

        video_manager.release()

        logger.debug(f"Scene detection completed: {len(scenes_data)} scenes")
        return scenes_data

    async def _detect_scenes_basic(
        self,
        video_file_path: str,
        config: VideoProcessingConfig
    ) -> List[Dict[str, Any]]:
        """Basic scene detection using OpenCV histogram analysis."""

        logger.debug("Starting basic scene detection")

        cap = cv2.VideoCapture(video_file_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Handle edge cases
        if fps <= 0:
            fps = 30.0  # Default FPS
        if frame_count <= 0:
            frame_count = 300  # Default frame count

        scenes_data = []
        scene_boundaries = [0]  # Start with first frame

        prev_hist = None
        frame_number = 0

        # Sample frames for histogram comparison
        sample_interval = max(1, int(fps))  # Sample every second

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_number % sample_interval == 0:
                # Calculate histogram
                hist = cv2.calcHist([frame], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
                hist = cv2.normalize(hist, hist).flatten()

                if prev_hist is not None:
                    # Calculate histogram correlation
                    correlation = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)

                    # If correlation is low, we have a scene change
                    if correlation < (1.0 - config.scene_threshold / 100.0):
                        scene_boundaries.append(frame_number)

                prev_hist = hist

            frame_number += 1

        # Add final frame
        scene_boundaries.append(frame_count - 1)

        # Create scene data
        for i in range(len(scene_boundaries) - 1):
            start_frame = scene_boundaries[i]
            end_frame = scene_boundaries[i + 1]
            start_time = start_frame / fps if fps > 0 else 0
            end_time = end_frame / fps if fps > 0 else 1
            duration = end_time - start_time

            if duration >= config.min_scene_length:
                scene_data = {
                    "scene_number": len(scenes_data) + 1,
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration": duration,
                    "start_frame": start_frame,
                    "end_frame": end_frame
                }
                scenes_data.append(scene_data)

        cap.release()

        logger.debug(f"Basic scene detection completed: {len(scenes_data)} scenes")
        return scenes_data

    async def _extract_key_frames(
        self,
        video_file_path: str,
        scenes_data: List[Dict[str, Any]],
        config: VideoProcessingConfig
    ) -> List[VideoScene]:
        """Extract key frames for each detected scene."""

        logger.debug("Starting key frame extraction")

        # Create frames directory if saving frames
        frames_directory = None
        if config.save_frames:
            frames_directory = tempfile.mkdtemp(prefix="video_frames_")

        scenes_with_frames = []
        cap = cv2.VideoCapture(video_file_path)
        fps = cap.get(cv2.CAP_PROP_FPS)

        for scene_data in scenes_data:
            try:
                # Extract frames for this scene
                key_frames = await self._extract_scene_frames(
                    cap,
                    scene_data,
                    fps,
                    config,
                    frames_directory
                )

                # Calculate scene characteristics
                scene_characteristics = self._analyze_scene_characteristics(key_frames)

                # Create VideoScene object
                scene = VideoScene(
                    scene_number=scene_data["scene_number"],
                    start_time=scene_data["start_time"],
                    end_time=scene_data["end_time"],
                    duration=scene_data["duration"],
                    start_frame=scene_data["start_frame"],
                    end_frame=scene_data["end_frame"],
                    key_frames=key_frames,
                    scene_type=scene_characteristics["scene_type"],
                    motion_intensity=scene_characteristics["motion_intensity"],
                    color_diversity=scene_characteristics["color_diversity"],
                    brightness_variation=scene_characteristics["brightness_variation"],
                    scene_quality=scene_characteristics["scene_quality"],
                    frame_count=scene_data["end_frame"] - scene_data["start_frame"]
                )

                scenes_with_frames.append(scene)

            except Exception as e:
                logger.error(f"Failed to extract frames for scene {scene_data['scene_number']}: {e}")
                # Create scene without frames
                scene = VideoScene(
                    scene_number=scene_data["scene_number"],
                    start_time=scene_data["start_time"],
                    end_time=scene_data["end_time"],
                    duration=scene_data["duration"],
                    start_frame=scene_data["start_frame"],
                    end_frame=scene_data["end_frame"],
                    key_frames=[],
                    frame_count=scene_data["end_frame"] - scene_data["start_frame"]
                )
                scenes_with_frames.append(scene)

        cap.release()

        logger.debug(f"Key frame extraction completed: {len(scenes_with_frames)} scenes processed")
        return scenes_with_frames

    async def _extract_scene_frames(
        self,
        cap: cv2.VideoCapture,
        scene_data: Dict[str, Any],
        fps: float,
        config: VideoProcessingConfig,
        frames_directory: Optional[str]
    ) -> List[KeyFrame]:
        """Extract key frames from a specific scene."""

        start_frame = scene_data["start_frame"]
        end_frame = scene_data["end_frame"]
        scene_duration = scene_data["duration"]

        # Determine frame extraction strategy
        if config.frame_extraction_method == FrameExtractionMethod.UNIFORM:
            frame_indices = self._get_uniform_frame_indices(
                start_frame, end_frame, config.frames_per_scene
            )
        elif config.frame_extraction_method == FrameExtractionMethod.ADAPTIVE:
            frame_indices = await self._get_adaptive_frame_indices(
                cap, start_frame, end_frame, config.frames_per_scene
            )
        else:
            # Default to uniform
            frame_indices = self._get_uniform_frame_indices(
                start_frame, end_frame, config.frames_per_scene
            )

        key_frames = []

        for frame_idx in frame_indices:
            try:
                # Seek to frame
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()

                if not ret:
                    continue

                # Calculate frame timestamp
                timestamp = frame_idx / fps

                # Analyze frame quality
                frame_quality = self._analyze_frame_quality(frame)

                # Save frame if required
                frame_path = None
                if frames_directory and config.save_frames:
                    frame_filename = f"scene_{scene_data['scene_number']:03d}_frame_{frame_idx:06d}.{config.frame_format}"
                    frame_path = os.path.join(frames_directory, frame_filename)

                    # Resize frame if needed
                    if (frame.shape[1] != config.target_frame_width or
                        frame.shape[0] != config.target_frame_height):
                        frame_resized = cv2.resize(
                            frame,
                            (config.target_frame_width, config.target_frame_height)
                        )
                    else:
                        frame_resized = frame

                    # Save frame
                    cv2.imwrite(frame_path, frame_resized, [
                        cv2.IMWRITE_JPEG_QUALITY, config.frame_quality
                    ])

                # Create KeyFrame object
                key_frame = KeyFrame(
                    frame_number=frame_idx,
                    timestamp=timestamp,
                    frame_path=frame_path or "",
                    width=frame.shape[1],
                    height=frame.shape[0],
                    channels=frame.shape[2] if len(frame.shape) > 2 else 1,
                    sharpness_score=frame_quality["sharpness"],
                    brightness_score=frame_quality["brightness"],
                    contrast_score=frame_quality["contrast"],
                    histogram_diversity=frame_quality["histogram_diversity"],
                    motion_score=frame_quality.get("motion", 0.0),
                    is_keyframe=frame_quality.get("is_keyframe", False)
                )

                # Filter by quality if required
                if frame_quality["overall"] >= config.min_frame_quality:
                    key_frames.append(key_frame)

            except Exception as e:
                logger.error(f"Failed to extract frame {frame_idx}: {e}")
                continue

        return key_frames

    def _get_uniform_frame_indices(
        self,
        start_frame: int,
        end_frame: int,
        num_frames: int
    ) -> List[int]:
        """Get uniformly distributed frame indices."""

        if end_frame <= start_frame:
            return []

        frame_range = end_frame - start_frame
        if frame_range < num_frames:
            return list(range(start_frame, end_frame))

        # Calculate uniform intervals
        interval = frame_range / (num_frames - 1) if num_frames > 1 else frame_range

        indices = []
        for i in range(num_frames):
            frame_idx = start_frame + int(i * interval)
            if frame_idx < end_frame:
                indices.append(frame_idx)

        return indices

    async def _get_adaptive_frame_indices(
        self,
        cap: cv2.VideoCapture,
        start_frame: int,
        end_frame: int,
        num_frames: int
    ) -> List[int]:
        """Get adaptively selected frame indices based on content analysis."""

        # Start with uniform distribution
        candidate_indices = self._get_uniform_frame_indices(
            start_frame, end_frame, min(num_frames * 3, end_frame - start_frame)
        )

        frame_scores = []
        prev_frame = None

        for frame_idx in candidate_indices:
            try:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()

                if not ret:
                    continue

                # Calculate frame quality score
                quality = self._analyze_frame_quality(frame)

                # Calculate motion score if we have previous frame
                motion_score = 0.0
                if prev_frame is not None:
                    motion_score = self._calculate_motion_score(prev_frame, frame)

                # Combined score: quality + motion + diversity
                combined_score = (
                    quality["overall"] * 0.4 +
                    motion_score * 0.3 +
                    quality["histogram_diversity"] * 0.3
                )

                frame_scores.append((frame_idx, combined_score))
                prev_frame = frame

            except Exception as e:
                logger.error(f"Failed to analyze frame {frame_idx}: {e}")
                continue

        # Sort by score and select top frames
        frame_scores.sort(key=lambda x: x[1], reverse=True)
        selected_indices = [idx for idx, score in frame_scores[:num_frames]]
        selected_indices.sort()  # Sort by frame order

        return selected_indices

    def _analyze_frame_quality(self, frame: np.ndarray) -> Dict[str, float]:
        """Analyze frame quality metrics."""

        # Convert to grayscale for some analyses
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Sharpness (Laplacian variance)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        sharpness = min(laplacian_var / 1000.0, 1.0)  # Normalize

        # Brightness (mean intensity)
        brightness = np.mean(gray) / 255.0

        # Contrast (standard deviation)
        contrast = np.std(gray) / 255.0

        # Histogram diversity (entropy)
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist_norm = hist / hist.sum()
        hist_norm = hist_norm[hist_norm > 0]  # Remove zeros
        entropy = -np.sum(hist_norm * np.log2(hist_norm))
        histogram_diversity = entropy / 8.0  # Normalize (max entropy for 8-bit is 8)

        # Overall quality score
        overall = (sharpness * 0.3 + contrast * 0.3 + histogram_diversity * 0.2 +
                  (1.0 - abs(brightness - 0.5) * 2) * 0.2)  # Prefer mid-range brightness

        return {
            "sharpness": sharpness,
            "brightness": brightness,
            "contrast": contrast,
            "histogram_diversity": histogram_diversity,
            "overall": overall
        }

    def _calculate_motion_score(self, prev_frame: np.ndarray, curr_frame: np.ndarray) -> float:
        """Calculate motion score between two frames."""

        try:
            # Convert to grayscale
            prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
            curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)

            # Calculate absolute difference
            diff = cv2.absdiff(prev_gray, curr_gray)

            # Calculate motion score as mean difference
            motion_score = np.mean(diff) / 255.0

            return min(motion_score, 1.0)

        except Exception as e:
            logger.error(f"Failed to calculate motion score: {e}")
            return 0.0

    def _analyze_scene_characteristics(self, key_frames: List[KeyFrame]) -> Dict[str, Any]:
        """Analyze characteristics of a scene based on its key frames."""

        if not key_frames:
            return {
                "scene_type": "unknown",
                "motion_intensity": 0.0,
                "color_diversity": 0.0,
                "brightness_variation": 0.0,
                "scene_quality": 0.0
            }

        # Calculate average metrics
        avg_motion = np.mean([frame.motion_score for frame in key_frames])
        avg_brightness = np.mean([frame.brightness_score for frame in key_frames])
        avg_contrast = np.mean([frame.contrast_score for frame in key_frames])
        avg_histogram_diversity = np.mean([frame.histogram_diversity for frame in key_frames])

        # Calculate variations
        brightness_variation = np.std([frame.brightness_score for frame in key_frames])

        # Determine scene type based on characteristics
        scene_type = "unknown"
        if avg_motion > 0.3:
            scene_type = "action"
        elif brightness_variation > 0.2:
            scene_type = "transition"
        elif avg_contrast > 0.5:
            scene_type = "dialogue"
        else:
            scene_type = "static"

        # Calculate overall scene quality
        scene_quality = np.mean([
            avg_contrast * 0.3,
            avg_histogram_diversity * 0.3,
            (1.0 - abs(avg_brightness - 0.5) * 2) * 0.2,  # Prefer mid-range brightness
            min(avg_motion, 0.5) * 2 * 0.2  # Some motion is good, too much is bad
        ])

        return {
            "scene_type": scene_type,
            "motion_intensity": avg_motion,
            "color_diversity": avg_histogram_diversity,
            "brightness_variation": brightness_variation,
            "scene_quality": scene_quality
        }

    def _calculate_quality_metrics(
        self,
        scenes: List[VideoScene],
        video_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate overall quality metrics for the video processing."""

        if not scenes:
            return {
                "scene_detection_confidence": 0.0,
                "frame_extraction_quality": 0.0,
                "overall_video_quality": 0.0,
                "memory_usage_mb": 0.0,
                "frames_directory": None
            }

        # Scene detection confidence (based on scene count and duration distribution)
        total_duration = sum(scene.duration for scene in scenes)
        avg_scene_duration = total_duration / len(scenes)
        duration_std = np.std([scene.duration for scene in scenes])

        # Good scene detection has reasonable scene count and duration consistency
        scene_count_score = min(len(scenes) / 10.0, 1.0)  # Prefer 5-10 scenes
        duration_consistency = max(0, 1.0 - duration_std / avg_scene_duration) if avg_scene_duration > 0 else 0
        scene_detection_confidence = (scene_count_score * 0.5 + duration_consistency * 0.5)

        # Frame extraction quality (average frame quality)
        all_frames = [frame for scene in scenes for frame in scene.key_frames]
        if all_frames:
            avg_frame_quality = np.mean([
                (frame.sharpness_score * 0.3 +
                 frame.contrast_score * 0.3 +
                 frame.histogram_diversity * 0.2 +
                 (1.0 - abs(frame.brightness_score - 0.5) * 2) * 0.2)
                for frame in all_frames
            ])
        else:
            avg_frame_quality = 0.0

        # Overall video quality
        avg_scene_quality = np.mean([scene.scene_quality for scene in scenes])
        overall_quality = (scene_detection_confidence * 0.3 +
                          avg_frame_quality * 0.4 +
                          avg_scene_quality * 0.3)

        # Estimate memory usage (rough calculation)
        total_frames = len(all_frames)
        avg_frame_size = 1280 * 720 * 3 / (1024 * 1024)  # Rough MB per frame
        memory_usage_mb = total_frames * avg_frame_size

        return {
            "scene_detection_confidence": scene_detection_confidence,
            "frame_extraction_quality": avg_frame_quality,
            "overall_video_quality": overall_quality,
            "memory_usage_mb": memory_usage_mb,
            "frames_directory": None  # Will be set by caller if applicable
        }

    def _update_metrics(self, result: VideoProcessingResult) -> None:
        """Update service performance metrics."""

        self.metrics["total_videos_processed"] += 1
        self.metrics["total_processing_time"] += result.processing_time
        self.metrics["total_video_duration"] += result.video_duration
        self.metrics["total_scenes_detected"] += len(result.scenes)
        self.metrics["total_frames_extracted"] += result.total_key_frames

        # Update averages
        total_videos = self.metrics["total_videos_processed"]

        current_avg_quality = self.metrics["average_quality"]
        self.metrics["average_quality"] = (
            (current_avg_quality * (total_videos - 1) + result.overall_video_quality) / total_videos
        )

        current_avg_speed = self.metrics["average_processing_speed"]
        self.metrics["average_processing_speed"] = (
            (current_avg_speed * (total_videos - 1) + result.processing_speed_ratio) / total_videos
        )

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get video processing service statistics."""

        total_duration = self.metrics["total_video_duration"]
        total_time = self.metrics["total_processing_time"]

        return {
            "total_videos_processed": self.metrics["total_videos_processed"],
            "total_video_duration_hours": total_duration / 3600,
            "total_processing_time_hours": total_time / 3600,
            "total_scenes_detected": self.metrics["total_scenes_detected"],
            "total_frames_extracted": self.metrics["total_frames_extracted"],
            "average_quality": self.metrics["average_quality"],
            "average_processing_speed_ratio": self.metrics["average_processing_speed"],
            "overall_throughput_ratio": total_duration / total_time if total_time > 0 else 0.0,
            "scene_detection_method": self.config.scene_detection_method.value,
            "frame_extraction_method": self.config.frame_extraction_method.value,
            "dependencies_available": {
                "opencv": CV2_AVAILABLE,
                "scenedetect": SCENEDETECT_AVAILABLE,
                "pil": PIL_AVAILABLE,
                "numpy": NUMPY_AVAILABLE
            }
        }


def create_video_service(
    scene_detection_method: SceneDetectionMethod = SceneDetectionMethod.CONTENT_DETECTOR,
    frame_extraction_method: FrameExtractionMethod = FrameExtractionMethod.ADAPTIVE,
    frames_per_scene: int = 5,
    **kwargs
) -> VideoService:
    """
    Convenience function to create a VideoService with common settings.

    Args:
        scene_detection_method: Method for scene detection
        frame_extraction_method: Method for frame extraction
        frames_per_scene: Number of frames to extract per scene
        **kwargs: Additional configuration options

    Returns:
        Configured VideoService instance
    """
    config = VideoProcessingConfig(
        scene_detection_method=scene_detection_method,
        frame_extraction_method=frame_extraction_method,
        frames_per_scene=frames_per_scene,
        **kwargs
    )

    return VideoService(config)
