"""
Service Monitoring and Degradation Handling

Provides utilities for monitoring external service availability and
managing graceful degradation when services are unavailable.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum

from app.core.exceptions import ServiceStatus, ErrorSeverity

logger = logging.getLogger(__name__)


class ServiceType(str, Enum):
    """Types of external services."""
    
    OPENAI_API = "openai_api"
    QDRANT = "qdrant"
    REDIS = "redis"
    WHISPER = "whisper"
    FFMPEG = "ffmpeg"
    OPENCV = "opencv"


class ServiceMonitor:
    """
    Monitor external service availability and manage graceful degradation.
    
    Tracks service health and provides fallback capability information.
    """
    
    def __init__(self):
        self._service_status: Dict[ServiceType, ServiceStatus] = {}
        self._last_check: Dict[ServiceType, datetime] = {}
        self._check_interval = timedelta(minutes=5)  # Check every 5 minutes
    
    def register_service_status(
        self,
        service_type: ServiceType,
        is_available: bool,
        capabilities_affected: List[str],
        fallback_available: bool = True
    ) -> ServiceStatus:
        """
        Register the current status of a service.
        
        Args:
            service_type: Type of service
            is_available: Whether the service is currently available
            capabilities_affected: List of capabilities affected when service is down
            fallback_available: Whether fallback functionality exists
            
        Returns:
            ServiceStatus object with current status
        """
        status = "available" if is_available else ("degraded" if fallback_available else "unavailable")
        
        service_status = ServiceStatus(
            service_name=service_type.value,
            status=status,
            fallback_available=fallback_available,
            capabilities_affected=capabilities_affected if not is_available else []
        )
        
        self._service_status[service_type] = service_status
        self._last_check[service_type] = datetime.now()
        
        if not is_available:
            # Use info level for optional services in development to reduce noise
            log_level = logger.info if service_type in [ServiceType.OPENAI_API, ServiceType.QDRANT] else logger.warning
            log_level(
                f"Service {service_type.value} is {status}",
                extra={
                    "service": service_type.value,
                    "status": status,
                    "fallback_available": fallback_available,
                    "capabilities_affected": capabilities_affected
                }
            )
        
        return service_status
    
    def get_service_status(self, service_type: ServiceType) -> Optional[ServiceStatus]:
        """Get the current status of a service."""
        return self._service_status.get(service_type)
    
    def get_all_service_status(self) -> List[ServiceStatus]:
        """Get status of all monitored services."""
        return list(self._service_status.values())
    
    def get_degraded_services(self) -> List[ServiceStatus]:
        """Get list of services that are degraded or unavailable."""
        return [
            status for status in self._service_status.values()
            if status.status in ["degraded", "unavailable"]
        ]
    
    def get_system_health_summary(self) -> Dict[str, Any]:
        """
        Get overall system health summary.
        
        Returns:
            Dictionary with system health information
        """
        all_services = list(self._service_status.values())
        
        if not all_services:
            return {
                "overall_status": "unknown",
                "available_services": 0,
                "degraded_services": 0,
                "unavailable_services": 0,
                "fallback_coverage": 0.0
            }
        
        available = len([s for s in all_services if s.status == "available"])
        degraded = len([s for s in all_services if s.status == "degraded"])
        unavailable = len([s for s in all_services if s.status == "unavailable"])
        
        # Calculate fallback coverage
        services_with_fallback = len([s for s in all_services if s.fallback_available])
        fallback_coverage = services_with_fallback / len(all_services) if all_services else 0.0
        
        # Determine overall status
        if unavailable == 0 and degraded == 0:
            overall_status = "healthy"
        elif unavailable == 0:
            overall_status = "degraded"
        elif fallback_coverage >= 0.8:
            overall_status = "degraded"
        else:
            overall_status = "critical"
        
        return {
            "overall_status": overall_status,
            "available_services": available,
            "degraded_services": degraded,
            "unavailable_services": unavailable,
            "total_services": len(all_services),
            "fallback_coverage": fallback_coverage,
            "last_updated": datetime.now().isoformat()
        }
    
    def should_use_fallback(self, service_type: ServiceType) -> bool:
        """
        Determine if fallback should be used for a service.
        
        Args:
            service_type: Type of service to check
            
        Returns:
            True if fallback should be used, False otherwise
        """
        status = self._service_status.get(service_type)
        if not status:
            return True  # Use fallback if status unknown
        
        return status.status != "available"
    
    def get_affected_capabilities(self, service_types: List[ServiceType]) -> List[str]:
        """
        Get all capabilities affected by the given services.
        
        Args:
            service_types: List of service types to check
            
        Returns:
            Combined list of affected capabilities
        """
        affected_capabilities = set()
        
        for service_type in service_types:
            status = self._service_status.get(service_type)
            if status and status.status != "available":
                affected_capabilities.update(status.capabilities_affected)
        
        return list(affected_capabilities)
    
    def create_degradation_context(self, service_types: List[ServiceType]) -> Dict[str, Any]:
        """
        Create context information for service degradation scenarios.
        
        Args:
            service_types: List of services that might be affected
            
        Returns:
            Context dictionary with degradation information
        """
        degraded_services = []
        affected_capabilities = set()
        fallback_available = True
        
        for service_type in service_types:
            status = self._service_status.get(service_type)
            if status and status.status != "available":
                degraded_services.append(status)
                affected_capabilities.update(status.capabilities_affected)
                if not status.fallback_available:
                    fallback_available = False
        
        return {
            "degraded_services": degraded_services,
            "affected_capabilities": list(affected_capabilities),
            "fallback_available": fallback_available,
            "severity": ErrorSeverity.MEDIUM if fallback_available else ErrorSeverity.HIGH
        }


# Global service monitor instance
service_monitor = ServiceMonitor()


def check_openai_availability() -> ServiceStatus:
    """Check OpenAI API availability and register status."""
    try:
        # Check if API key is configured
        import os
        from app.core.config import settings

        api_key = os.getenv("OPENAI_API_KEY")
        is_available = bool(api_key)

        # For local development, don't warn if OpenAI is not configured
        # since we're using local LLMs (Ollama)
        if not is_available and not settings.debug:
            # Only log info in development mode, not warning
            logger.info("OpenAI API not configured - using local LLM fallback")

        return service_monitor.register_service_status(
            ServiceType.OPENAI_API,
            is_available=is_available,
            capabilities_affected=["gpt_analysis", "advanced_reasoning", "multi_agent_collaboration"] if not is_available else [],
            fallback_available=True
        )
    except Exception as e:
        logger.error(f"Failed to check OpenAI availability: {e}")
        return service_monitor.register_service_status(
            ServiceType.OPENAI_API,
            is_available=False,
            capabilities_affected=["gpt_analysis", "advanced_reasoning", "multi_agent_collaboration"],
            fallback_available=True
        )


def check_qdrant_availability() -> ServiceStatus:
    """Check Qdrant availability and register status."""
    try:
        from app.core.vector_store import vector_store
        from app.core.config import settings

        is_available = vector_store.is_connected

        # For local development, don't warn if Qdrant is not running
        # since it's an optional enhancement service
        if not is_available:
            logger.info("Qdrant vector database not available - basic document search will be used as fallback")

        return service_monitor.register_service_status(
            ServiceType.QDRANT,
            is_available=is_available,
            capabilities_affected=["semantic_search", "document_similarity", "rag_enhancement"] if not is_available else [],
            fallback_available=True
        )
    except Exception as e:
        logger.info(f"Qdrant not available: {e} - using fallback document search")
        return service_monitor.register_service_status(
            ServiceType.QDRANT,
            is_available=False,
            capabilities_affected=["semantic_search", "document_similarity", "rag_enhancement"],
            fallback_available=True
        )


def check_multimodal_dependencies() -> List[ServiceStatus]:
    """Check multi-modal processing dependencies and register status."""
    statuses = []
    
    # Check Whisper availability
    try:
        import whisper
        whisper_available = True
    except ImportError:
        whisper_available = False
    
    statuses.append(service_monitor.register_service_status(
        ServiceType.WHISPER,
        is_available=whisper_available,
        capabilities_affected=["speech_to_text", "audio_transcription"],
        fallback_available=False
    ))
    
    # Check OpenCV availability
    try:
        import cv2
        opencv_available = True
    except ImportError:
        opencv_available = False
    
    statuses.append(service_monitor.register_service_status(
        ServiceType.OPENCV,
        is_available=opencv_available,
        capabilities_affected=["video_processing", "frame_extraction", "video_analysis"],
        fallback_available=False
    ))
    
    # Check FFmpeg availability (binary, not Python package)
    try:
        import subprocess
        import shutil

        # First check if ffmpeg binary is in PATH
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path:
            # Test if ffmpeg actually works
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            ffmpeg_available = result.returncode == 0
        else:
            ffmpeg_available = False

        if ffmpeg_available:
            logger.info(f"FFmpeg found at: {ffmpeg_path}")
        else:
            logger.info("FFmpeg binary not found in PATH")

    except Exception as e:
        logger.info(f"FFmpeg check failed: {e}")
        ffmpeg_available = False
    
    statuses.append(service_monitor.register_service_status(
        ServiceType.FFMPEG,
        is_available=ffmpeg_available,
        capabilities_affected=["video_audio_extraction", "format_conversion"],
        fallback_available=False
    ))
    
    return statuses


def initialize_service_monitoring():
    """Initialize service monitoring for all external dependencies."""
    logger.info("Initializing service monitoring...")
    
    # Check all services
    check_openai_availability()
    check_qdrant_availability()
    check_multimodal_dependencies()
    
    # Log summary
    health_summary = service_monitor.get_system_health_summary()
    logger.info(
        f"Service monitoring initialized - Overall status: {health_summary['overall_status']}",
        extra=health_summary
    )
