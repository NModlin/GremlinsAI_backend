#!/usr/bin/env python3
"""
Multimodal Content Ingestion Script

This script processes media files (images and videos) and ingests them into
Weaviate's MultiModalContent class for cross-modal search capabilities.

Features:
- Video processing with frame extraction using VideoService
- Image processing and analysis
- Metadata extraction and content analysis
- Batch processing with progress tracking
- Error handling and recovery
- Performance monitoring
"""

import os
import sys
import asyncio
import argparse
import logging
import hashlib
import mimetypes
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import weaviate
from weaviate.exceptions import WeaviateBaseError

# Import our services
from app.services.video_service import VideoService, VideoProcessingConfig

# Create a simple Weaviate client function for demo
def get_weaviate_client():
    """Get Weaviate client (mock for demo)."""
    import weaviate
    # In production, this would connect to actual Weaviate instance
    # For demo, we'll create a mock client
    return None

# Try to import image processing libraries
try:
    from PIL import Image, ImageStat
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logging.warning("PIL not available. Image processing will be limited.")

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logging.warning("OpenCV not available. Video processing will be limited.")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MultiModalIngester:
    """
    Multimodal content ingestion service.
    
    Processes images and videos for cross-modal search capabilities.
    """
    
    def __init__(self, weaviate_client: weaviate.WeaviateClient):
        """Initialize ingester with Weaviate client."""
        self.client = weaviate_client
        self.video_service = VideoService()
        
        # Supported file types
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
        self.video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'}
        
        # Processing statistics
        self.stats = {
            'total_files': 0,
            'processed_files': 0,
            'failed_files': 0,
            'images_processed': 0,
            'videos_processed': 0,
            'total_frames_extracted': 0,
            'processing_time': 0.0
        }
    
    async def ingest_directory(
        self,
        directory_path: str,
        conversation_id: Optional[str] = None,
        batch_size: int = 10
    ) -> Dict[str, Any]:
        """
        Ingest all media files from a directory.
        
        Args:
            directory_path: Path to directory containing media files
            conversation_id: Optional conversation ID for grouping
            batch_size: Number of files to process in each batch
            
        Returns:
            Dictionary with ingestion results and statistics
        """
        start_time = datetime.now()
        
        logger.info(f"Starting multimodal ingestion from: {directory_path}")
        
        # Find all media files
        media_files = self._find_media_files(directory_path)
        self.stats['total_files'] = len(media_files)
        
        logger.info(f"Found {len(media_files)} media files to process")
        
        # Process files in batches
        results = []
        for i in range(0, len(media_files), batch_size):
            batch = media_files[i:i + batch_size]
            batch_results = await self._process_batch(batch, conversation_id)
            results.extend(batch_results)
            
            # Log progress
            processed = min(i + batch_size, len(media_files))
            logger.info(f"Processed {processed}/{len(media_files)} files")
        
        # Calculate final statistics
        end_time = datetime.now()
        self.stats['processing_time'] = (end_time - start_time).total_seconds()
        
        return {
            'results': results,
            'statistics': self.stats,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        }
    
    def _find_media_files(self, directory_path: str) -> List[Path]:
        """Find all supported media files in directory."""
        media_files = []
        directory = Path(directory_path)
        
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory_path}")
        
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                extension = file_path.suffix.lower()
                if extension in self.image_extensions or extension in self.video_extensions:
                    media_files.append(file_path)
        
        return sorted(media_files)
    
    async def _process_batch(
        self,
        file_paths: List[Path],
        conversation_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Process a batch of media files."""
        results = []
        
        for file_path in file_paths:
            try:
                result = await self._process_file(file_path, conversation_id)
                results.append(result)
                self.stats['processed_files'] += 1
                
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
                results.append({
                    'file_path': str(file_path),
                    'status': 'failed',
                    'error': str(e)
                })
                self.stats['failed_files'] += 1
        
        return results
    
    async def _process_file(
        self,
        file_path: Path,
        conversation_id: Optional[str]
    ) -> Dict[str, Any]:
        """Process a single media file."""
        logger.info(f"Processing file: {file_path}")
        
        # Determine file type
        extension = file_path.suffix.lower()
        is_image = extension in self.image_extensions
        is_video = extension in self.video_extensions
        
        # Extract basic file information
        file_info = self._extract_file_info(file_path)
        
        # Process based on file type
        if is_image:
            processing_result = await self._process_image(file_path)
            self.stats['images_processed'] += 1
        elif is_video:
            processing_result = await self._process_video(file_path)
            self.stats['videos_processed'] += 1
            self.stats['total_frames_extracted'] += processing_result.get('total_key_frames', 0)
        else:
            raise ValueError(f"Unsupported file type: {extension}")
        
        # Create multimodal content object
        content_data = {
            'content_id': str(uuid.uuid4()),
            'media_type': 'image' if is_image else 'video',
            'filename': file_path.name,
            'storage_path': str(file_path),
            'file_size': file_info['file_size'],
            'content_hash': file_info['content_hash'],
            'created_at': file_info['created_at'],
            'updated_at': datetime.now(),
            'processing_status': 'completed',
            'processing_result': processing_result,
            'text_content': self._generate_text_description(processing_result, is_image),
            'conversation_id': conversation_id,
            'metadata': {
                'original_path': str(file_path),
                'mime_type': file_info['mime_type'],
                'processing_timestamp': datetime.now().isoformat()
            }
        }
        
        # Ingest into Weaviate
        object_id = await self._ingest_to_weaviate(content_data)
        
        return {
            'file_path': str(file_path),
            'status': 'success',
            'object_id': object_id,
            'media_type': content_data['media_type'],
            'processing_result': processing_result
        }
    
    def _extract_file_info(self, file_path: Path) -> Dict[str, Any]:
        """Extract basic file information."""
        stat = file_path.stat()
        
        # Calculate file hash
        with open(file_path, 'rb') as f:
            content_hash = hashlib.sha256(f.read()).hexdigest()
        
        # Get MIME type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        
        return {
            'file_size': stat.st_size,
            'content_hash': content_hash,
            'created_at': datetime.fromtimestamp(stat.st_ctime),
            'modified_at': datetime.fromtimestamp(stat.st_mtime),
            'mime_type': mime_type or 'application/octet-stream'
        }
    
    async def _process_image(self, file_path: Path) -> Dict[str, Any]:
        """Process an image file."""
        result = {
            'type': 'image',
            'width': 0,
            'height': 0,
            'channels': 0,
            'color_analysis': {},
            'quality_metrics': {}
        }
        
        if not PIL_AVAILABLE:
            logger.warning("PIL not available, skipping detailed image analysis")
            return result
        
        try:
            with Image.open(file_path) as img:
                # Basic image properties
                result['width'] = img.width
                result['height'] = img.height
                result['channels'] = len(img.getbands())
                result['format'] = img.format
                result['mode'] = img.mode
                
                # Color analysis
                if img.mode in ['RGB', 'RGBA']:
                    stat = ImageStat.Stat(img)
                    result['color_analysis'] = {
                        'mean_colors': stat.mean,
                        'std_colors': stat.stddev,
                        'extrema': stat.extrema
                    }
                
                # Quality metrics
                result['quality_metrics'] = {
                    'resolution': img.width * img.height,
                    'aspect_ratio': img.width / img.height if img.height > 0 else 0,
                    'file_size_per_pixel': file_path.stat().st_size / (img.width * img.height) if img.width * img.height > 0 else 0
                }
                
        except Exception as e:
            logger.error(f"Failed to analyze image {file_path}: {e}")
            result['error'] = str(e)
        
        return result
    
    async def _process_video(self, file_path: Path) -> Dict[str, Any]:
        """Process a video file using VideoService."""
        try:
            # Use our VideoService to process the video
            video_result = await self.video_service.process_video(str(file_path))
            
            # Convert VideoProcessingResult to dictionary
            return video_result.to_dict()
            
        except Exception as e:
            logger.error(f"Failed to process video {file_path}: {e}")
            return {
                'type': 'video',
                'error': str(e),
                'scenes': [],
                'total_key_frames': 0
            }
    
    def _generate_text_description(
        self,
        processing_result: Dict[str, Any],
        is_image: bool
    ) -> str:
        """Generate text description for cross-modal search."""
        descriptions = []
        
        if is_image:
            # Image description
            descriptions.append("Image content")
            
            if 'width' in processing_result and 'height' in processing_result:
                width = processing_result['width']
                height = processing_result['height']
                descriptions.append(f"Resolution: {width}x{height}")
                
                # Aspect ratio description
                if width > height * 1.5:
                    descriptions.append("landscape orientation wide image")
                elif height > width * 1.5:
                    descriptions.append("portrait orientation tall image")
                else:
                    descriptions.append("square or standard aspect ratio")
            
            # Color analysis
            color_analysis = processing_result.get('color_analysis', {})
            if color_analysis:
                descriptions.append("colorful visual content")
        
        else:
            # Video description
            descriptions.append("Video content")
            
            # Duration and scenes
            duration = processing_result.get('video_duration', 0)
            if duration > 0:
                descriptions.append(f"Duration: {duration:.1f} seconds")
            
            scenes = processing_result.get('scenes', [])
            if scenes:
                descriptions.append(f"{len(scenes)} scenes detected")
                
                # Scene types
                scene_types = set()
                for scene in scenes:
                    scene_type = scene.get('scene_type', 'unknown')
                    if scene_type != 'unknown':
                        scene_types.add(scene_type)
                
                if scene_types:
                    descriptions.append(f"Scene types: {', '.join(scene_types)}")
            
            # Frame information
            total_frames = processing_result.get('total_key_frames', 0)
            if total_frames > 0:
                descriptions.append(f"{total_frames} key frames extracted")
        
        return " ".join(descriptions)
    
    async def _ingest_to_weaviate(self, content_data: Dict[str, Any]) -> str:
        """Ingest content data into Weaviate MultiModalContent class."""
        try:
            collection = self.client.collections.get("MultiModalContent")
            
            # Insert object
            object_id = collection.data.insert(
                properties=content_data
            )
            
            logger.info(f"Successfully ingested {content_data['filename']} with ID: {object_id}")
            return str(object_id)
            
        except WeaviateBaseError as e:
            logger.error(f"Failed to ingest to Weaviate: {e}")
            raise
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get ingestion statistics."""
        return self.stats.copy()


async def main():
    """Main ingestion function."""
    parser = argparse.ArgumentParser(description="Ingest multimodal content into Weaviate")
    parser.add_argument("directory", help="Directory containing media files")
    parser.add_argument("--conversation-id", help="Optional conversation ID for grouping")
    parser.add_argument("--batch-size", type=int, default=10, help="Batch size for processing")
    parser.add_argument("--output", help="Output file for results (JSON)")
    
    args = parser.parse_args()
    
    try:
        # Initialize Weaviate client
        client = get_weaviate_client()
        
        # Create ingester
        ingester = MultiModalIngester(client)
        
        # Run ingestion
        results = await ingester.ingest_directory(
            args.directory,
            args.conversation_id,
            args.batch_size
        )
        
        # Output results
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"Results saved to: {args.output}")
        
        # Print summary
        stats = results['statistics']
        logger.info("Ingestion completed!")
        logger.info(f"Total files: {stats['total_files']}")
        logger.info(f"Processed: {stats['processed_files']}")
        logger.info(f"Failed: {stats['failed_files']}")
        logger.info(f"Images: {stats['images_processed']}")
        logger.info(f"Videos: {stats['videos_processed']}")
        logger.info(f"Frames extracted: {stats['total_frames_extracted']}")
        logger.info(f"Processing time: {stats['processing_time']:.2f}s")
        
        return 0
        
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        return 1


if __name__ == "__main__":
    import uuid
    sys.exit(asyncio.run(main()))
