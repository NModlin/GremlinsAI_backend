# tests/fixtures/multimodal_fixtures.py
"""
Test fixtures for multi-modal processing tests.

Provides mock data, files, and responses for testing multi-modal endpoints
including audio, image, and video processing functionality.
"""

import pytest
import io
import json
from unittest.mock import Mock


@pytest.fixture
def mock_audio_file():
    """Create a mock audio file for testing."""
    # Create fake audio data
    audio_content = b"RIFF\x24\x08\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x02\x00\x44\xac\x00\x00\x10\xb1\x02\x00\x04\x00\x10\x00data\x00\x08\x00\x00"
    return io.BytesIO(audio_content)


@pytest.fixture
def mock_image_file():
    """Create a mock image file for testing."""
    # Create fake JPEG header
    jpeg_header = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00"
    jpeg_content = jpeg_header + b"\x00" * 1000  # Pad with zeros
    return io.BytesIO(jpeg_content)


@pytest.fixture
def mock_video_file():
    """Create a mock video file for testing."""
    # Create fake MP4 header
    mp4_header = b"\x00\x00\x00\x20ftypmp41\x00\x00\x00\x00mp41isom"
    mp4_content = mp4_header + b"\x00" * 2000  # Pad with zeros
    return io.BytesIO(mp4_content)


@pytest.fixture
def audio_processing_response():
    """Mock audio processing response."""
    return {
        "id": "audio-test-123",
        "type": "audio",
        "processing_status": "completed",
        "results": {
            "transcription": {
                "text": "This is a test audio transcription for unit testing purposes.",
                "confidence": 0.95,
                "language": "en",
                "duration": 5.2,
                "words": [
                    {"word": "This", "start": 0.0, "end": 0.3, "confidence": 0.98},
                    {"word": "is", "start": 0.3, "end": 0.5, "confidence": 0.97},
                    {"word": "a", "start": 0.5, "end": 0.6, "confidence": 0.95},
                    {"word": "test", "start": 0.6, "end": 1.0, "confidence": 0.99}
                ]
            },
            "metadata": {
                "format": "wav",
                "sample_rate": 44100,
                "channels": 2,
                "bitrate": 1411,
                "duration": 5.2
            }
        },
        "created_at": "2023-01-01T00:00:00Z",
        "processing_time": 2.1
    }


@pytest.fixture
def image_processing_response():
    """Mock image processing response."""
    return {
        "id": "image-test-456",
        "type": "image",
        "processing_status": "completed",
        "results": {
            "analysis": {
                "description": "A test image showing a cat sitting on a windowsill with natural lighting",
                "confidence": 0.92,
                "dominant_colors": ["brown", "white", "blue", "green"],
                "dimensions": {"width": 1920, "height": 1080},
                "format": "JPEG",
                "objects": [
                    {"label": "cat", "confidence": 0.95, "bbox": [300, 200, 500, 400]},
                    {"label": "window", "confidence": 0.87, "bbox": [0, 0, 1920, 600]},
                    {"label": "windowsill", "confidence": 0.82, "bbox": [0, 600, 1920, 800]}
                ]
            },
            "text_extraction": {
                "text": "Welcome to our pet store",
                "confidence": 0.88,
                "language": "en",
                "bounding_boxes": [
                    {
                        "text": "Welcome",
                        "x": 100, "y": 50,
                        "width": 200, "height": 30,
                        "confidence": 0.92
                    },
                    {
                        "text": "to our pet store",
                        "x": 320, "y": 50,
                        "width": 300, "height": 30,
                        "confidence": 0.85
                    }
                ]
            },
            "metadata": {
                "file_size": 245760,
                "color_space": "RGB",
                "has_transparency": False,
                "exif_data": {
                    "camera": "Test Camera",
                    "date_taken": "2023-01-01T12:00:00Z"
                }
            }
        },
        "created_at": "2023-01-01T00:00:00Z",
        "processing_time": 3.2
    }


@pytest.fixture
def video_processing_response():
    """Mock video processing response."""
    return {
        "id": "video-test-789",
        "type": "video",
        "processing_status": "completed",
        "results": {
            "video_analysis": {
                "duration": 120.5,
                "fps": 30,
                "resolution": "1920x1080",
                "format": "mp4",
                "codec": "h264",
                "scenes": [
                    {
                        "start": 0,
                        "end": 30,
                        "description": "Person speaking to camera in office setting",
                        "confidence": 0.89
                    },
                    {
                        "start": 30,
                        "end": 60,
                        "description": "Presentation slides with charts and graphs",
                        "confidence": 0.94
                    },
                    {
                        "start": 60,
                        "end": 120.5,
                        "description": "Q&A session with multiple speakers",
                        "confidence": 0.87
                    }
                ]
            },
            "audio_transcription": {
                "text": "Welcome to this presentation about artificial intelligence and machine learning. Today we'll cover the latest developments in AI technology and their practical applications in business.",
                "confidence": 0.93,
                "language": "en",
                "duration": 120.5,
                "timestamps": [
                    {
                        "start": 0.5,
                        "end": 5.2,
                        "text": "Welcome to this presentation about artificial intelligence"
                    },
                    {
                        "start": 5.2,
                        "end": 10.8,
                        "text": "and machine learning."
                    },
                    {
                        "start": 11.0,
                        "end": 18.5,
                        "text": "Today we'll cover the latest developments in AI technology"
                    }
                ]
            },
            "key_frames": [
                {
                    "timestamp": 5.0,
                    "description": "Title slide: AI Presentation 2023",
                    "confidence": 0.96,
                    "image_url": "/frames/video-test-789/frame_005.jpg"
                },
                {
                    "timestamp": 35.2,
                    "description": "Chart showing AI adoption rates",
                    "confidence": 0.91,
                    "image_url": "/frames/video-test-789/frame_035.jpg"
                },
                {
                    "timestamp": 75.8,
                    "description": "Speaker answering questions",
                    "confidence": 0.88,
                    "image_url": "/frames/video-test-789/frame_075.jpg"
                }
            ],
            "metadata": {
                "file_size": 52428800,  # 50MB
                "bitrate": 3500,
                "audio_codec": "aac",
                "has_subtitles": False
            }
        },
        "created_at": "2023-01-01T00:00:00Z",
        "processing_time": 45.7
    }


@pytest.fixture
def multimodal_processing_options():
    """Common processing options for multimodal tests."""
    return {
        "audio_options": {
            "transcribe": True,
            "language": "auto",
            "format": "wav",
            "enhance_audio": False,
            "speaker_detection": False
        },
        "image_options": {
            "analyze": True,
            "extract_text": True,
            "detect_objects": True,
            "enhance_image": False,
            "generate_alt_text": True
        },
        "video_options": {
            "extract_frames": True,
            "transcribe_audio": True,
            "analyze_content": True,
            "detect_scenes": True,
            "generate_summary": True,
            "frame_interval": 5.0
        }
    }


@pytest.fixture
def multimodal_error_responses():
    """Mock error responses for multimodal processing."""
    return {
        "unsupported_format": {
            "detail": "Unsupported file format. Supported formats: wav, mp3, mp4, jpg, png, gif",
            "error_code": "MULTIMODAL_001",
            "supported_formats": {
                "audio": ["wav", "mp3", "m4a", "flac"],
                "image": ["jpg", "jpeg", "png", "gif", "bmp"],
                "video": ["mp4", "avi", "mov", "mkv"]
            }
        },
        "file_too_large": {
            "detail": "File size exceeds maximum limit",
            "error_code": "MULTIMODAL_002",
            "max_sizes": {
                "audio": "100MB",
                "image": "50MB", 
                "video": "500MB"
            }
        },
        "processing_failed": {
            "detail": "Multimodal processing failed due to corrupted file",
            "error_code": "MULTIMODAL_003",
            "retry_possible": False
        },
        "quota_exceeded": {
            "detail": "Processing quota exceeded for this API key",
            "error_code": "MULTIMODAL_004",
            "quota_reset": "2023-01-02T00:00:00Z"
        }
    }


@pytest.fixture
def mock_multimodal_service():
    """Mock multimodal service for testing."""
    service = Mock()
    
    # Configure default return values
    service.process_audio.return_value = {
        "id": "audio-mock-123",
        "type": "audio",
        "processing_status": "completed",
        "results": {"transcription": {"text": "Mock transcription", "confidence": 0.9}},
        "created_at": "2023-01-01T00:00:00Z",
        "processing_time": 1.5
    }
    
    service.process_image.return_value = {
        "id": "image-mock-456",
        "type": "image", 
        "processing_status": "completed",
        "results": {"analysis": {"description": "Mock image analysis", "confidence": 0.85}},
        "created_at": "2023-01-01T00:00:00Z",
        "processing_time": 2.1
    }
    
    service.process_video.return_value = {
        "id": "video-mock-789",
        "type": "video",
        "processing_status": "completed", 
        "results": {"video_analysis": {"duration": 60.0, "scenes": []}},
        "created_at": "2023-01-01T00:00:00Z",
        "processing_time": 30.5
    }
    
    return service
