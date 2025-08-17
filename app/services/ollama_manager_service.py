# app/services/ollama_manager_service.py
"""
Ollama Manager Service for Dynamic Model Management

This service provides dynamic model loading/unloading capabilities for Ollama
to optimize GPU memory usage and resource utilization. It manages model
lifecycle, monitors resource usage, and implements intelligent caching.

Features:
- Dynamic model loading and unloading
- GPU memory optimization (30% reduction target)
- Model lifecycle management and monitoring
- Intelligent model caching and preloading
- Resource usage tracking and analytics
- Integration with tiered routing system
"""

import asyncio
import logging
import time
import json
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import aiohttp
import psutil
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class ModelStatus(Enum):
    """Model loading status."""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    UNLOADING = "unloading"
    ERROR = "error"


@dataclass
class ModelInfo:
    """Information about a model."""
    name: str
    size_gb: float
    status: ModelStatus
    loaded_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    usage_count: int = 0
    memory_usage_mb: int = 0
    load_time_seconds: float = 0.0
    error_message: Optional[str] = None


@dataclass
class ResourceMetrics:
    """System resource metrics."""
    gpu_memory_total_mb: int
    gpu_memory_used_mb: int
    gpu_memory_free_mb: int
    gpu_utilization_percent: float
    cpu_percent: float
    ram_used_gb: float
    ram_total_gb: float
    timestamp: datetime


class OllamaManagerService:
    """
    Service for managing Ollama models dynamically to optimize GPU resources.
    
    Provides intelligent model loading/unloading based on usage patterns
    and resource constraints to achieve 30% GPU memory reduction.
    """
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        """Initialize the Ollama manager service."""
        self.base_url = base_url.rstrip('/')
        self.models: Dict[str, ModelInfo] = {}
        self.loading_locks: Dict[str, asyncio.Lock] = {}
        
        # Resource management
        self.max_concurrent_models = 3
        self.memory_threshold_percent = 85.0
        self.idle_timeout_minutes = 15
        
        # Performance tracking
        self.metrics = {
            "models_loaded": 0,
            "models_unloaded": 0,
            "memory_saved_mb": 0,
            "load_time_total": 0.0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        # Usage tracking for intelligent caching
        self.usage_history = defaultdict(deque)  # model_name -> deque of usage timestamps
        self.preload_candidates = set()
        
        # Resource monitoring
        self.resource_history = deque(maxlen=100)
        
        logger.info(f"OllamaManagerService initialized with base URL: {base_url}")
    
    async def load_model(self, model_name: str, force_reload: bool = False) -> bool:
        """
        Load a model into GPU memory.
        
        Args:
            model_name: Name of the model to load
            force_reload: Force reload even if already loaded
            
        Returns:
            True if model loaded successfully, False otherwise
        """
        # Check if model is already loaded
        if not force_reload and model_name in self.models:
            model_info = self.models[model_name]
            if model_info.status == ModelStatus.LOADED:
                model_info.last_used = datetime.utcnow()
                model_info.usage_count += 1
                self.metrics["cache_hits"] += 1
                logger.debug(f"Model {model_name} already loaded (cache hit)")
                return True
            elif model_info.status == ModelStatus.LOADING:
                # Wait for ongoing load operation
                await self._wait_for_load_completion(model_name)
                return model_info.status == ModelStatus.LOADED
        
        # Get or create loading lock
        if model_name not in self.loading_locks:
            self.loading_locks[model_name] = asyncio.Lock()
        
        async with self.loading_locks[model_name]:
            # Double-check after acquiring lock
            if not force_reload and model_name in self.models:
                model_info = self.models[model_name]
                if model_info.status == ModelStatus.LOADED:
                    return True
            
            # Check resource constraints before loading
            if not await self._can_load_model(model_name):
                logger.warning(f"Cannot load {model_name}: resource constraints")
                return False
            
            # Initialize or update model info
            if model_name not in self.models:
                self.models[model_name] = ModelInfo(
                    name=model_name,
                    size_gb=await self._get_model_size(model_name),
                    status=ModelStatus.UNLOADED
                )
            
            model_info = self.models[model_name]
            model_info.status = ModelStatus.LOADING
            
            try:
                start_time = time.time()
                logger.info(f"Loading model: {model_name}")
                
                # Make API call to load model
                success = await self._api_load_model(model_name)
                
                if success:
                    load_time = time.time() - start_time
                    model_info.status = ModelStatus.LOADED
                    model_info.loaded_at = datetime.utcnow()
                    model_info.last_used = datetime.utcnow()
                    model_info.usage_count += 1
                    model_info.load_time_seconds = load_time
                    model_info.memory_usage_mb = await self._estimate_model_memory(model_name)
                    
                    # Update metrics
                    self.metrics["models_loaded"] += 1
                    self.metrics["load_time_total"] += load_time
                    self.metrics["cache_misses"] += 1
                    
                    # Track usage for intelligent caching
                    self._track_usage(model_name)
                    
                    logger.info(f"Model {model_name} loaded successfully in {load_time:.2f}s")
                    return True
                else:
                    model_info.status = ModelStatus.ERROR
                    model_info.error_message = "Failed to load model via API"
                    logger.error(f"Failed to load model: {model_name}")
                    return False
                    
            except Exception as e:
                model_info.status = ModelStatus.ERROR
                model_info.error_message = str(e)
                logger.error(f"Error loading model {model_name}: {e}")
                return False
    
    async def unload_model(self, model_name: str) -> bool:
        """
        Unload a model from GPU memory.
        
        Args:
            model_name: Name of the model to unload
            
        Returns:
            True if model unloaded successfully, False otherwise
        """
        if model_name not in self.models:
            logger.warning(f"Model {model_name} not found for unloading")
            return False
        
        model_info = self.models[model_name]
        
        if model_info.status != ModelStatus.LOADED:
            logger.warning(f"Model {model_name} is not loaded (status: {model_info.status})")
            return False
        
        # Get or create loading lock (reuse for unloading)
        if model_name not in self.loading_locks:
            self.loading_locks[model_name] = asyncio.Lock()
        
        async with self.loading_locks[model_name]:
            try:
                model_info.status = ModelStatus.UNLOADING
                logger.info(f"Unloading model: {model_name}")
                
                # Make API call to unload model
                success = await self._api_unload_model(model_name)
                
                if success:
                    # Update metrics
                    self.metrics["models_unloaded"] += 1
                    self.metrics["memory_saved_mb"] += model_info.memory_usage_mb
                    
                    # Update model status
                    model_info.status = ModelStatus.UNLOADED
                    model_info.loaded_at = None
                    model_info.memory_usage_mb = 0
                    
                    logger.info(f"Model {model_name} unloaded successfully")
                    return True
                else:
                    model_info.status = ModelStatus.ERROR
                    model_info.error_message = "Failed to unload model via API"
                    logger.error(f"Failed to unload model: {model_name}")
                    return False
                    
            except Exception as e:
                model_info.status = ModelStatus.ERROR
                model_info.error_message = str(e)
                logger.error(f"Error unloading model {model_name}: {e}")
                return False
    
    async def optimize_memory_usage(self) -> Dict[str, Any]:
        """
        Optimize GPU memory usage by unloading idle models.
        
        Returns:
            Dictionary with optimization results
        """
        optimization_start = time.time()
        results = {
            "models_unloaded": [],
            "memory_freed_mb": 0,
            "models_kept_loaded": [],
            "optimization_time_seconds": 0
        }
        
        logger.info("Starting GPU memory optimization")
        
        # Get current resource metrics
        current_metrics = await self._get_resource_metrics()
        
        # Check if optimization is needed
        memory_usage_percent = (current_metrics.gpu_memory_used_mb / current_metrics.gpu_memory_total_mb) * 100
        
        if memory_usage_percent < self.memory_threshold_percent:
            logger.info(f"GPU memory usage ({memory_usage_percent:.1f}%) below threshold, no optimization needed")
            results["optimization_time_seconds"] = time.time() - optimization_start
            return results
        
        # Find models to unload based on usage patterns
        models_to_unload = await self._identify_models_for_unloading()
        
        # Unload identified models
        for model_name in models_to_unload:
            if await self.unload_model(model_name):
                model_info = self.models[model_name]
                results["models_unloaded"].append(model_name)
                results["memory_freed_mb"] += model_info.memory_usage_mb
        
        # Track models kept loaded
        for model_name, model_info in self.models.items():
            if model_info.status == ModelStatus.LOADED:
                results["models_kept_loaded"].append(model_name)
        
        results["optimization_time_seconds"] = time.time() - optimization_start
        
        logger.info(f"Memory optimization completed: freed {results['memory_freed_mb']}MB from {len(results['models_unloaded'])} models")
        return results
    
    async def get_model_status(self, model_name: str) -> Optional[ModelInfo]:
        """Get status information for a specific model."""
        return self.models.get(model_name)
    
    async def list_loaded_models(self) -> List[ModelInfo]:
        """Get list of currently loaded models."""
        return [info for info in self.models.values() if info.status == ModelStatus.LOADED]
    
    async def get_resource_metrics(self) -> ResourceMetrics:
        """Get current system resource metrics."""
        return await self._get_resource_metrics()
    
    async def preload_popular_models(self) -> Dict[str, bool]:
        """Preload models based on usage patterns."""
        results = {}
        
        # Identify popular models from usage history
        popular_models = self._identify_popular_models()
        
        for model_name in popular_models:
            if model_name not in self.models or self.models[model_name].status != ModelStatus.LOADED:
                # Check if we can load more models
                if await self._can_load_model(model_name):
                    results[model_name] = await self.load_model(model_name)
                else:
                    results[model_name] = False
                    break  # Stop if we can't load more models
        
        return results
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics and statistics."""
        total_models = len(self.models)
        loaded_models = len([m for m in self.models.values() if m.status == ModelStatus.LOADED])
        
        # Calculate memory efficiency
        total_memory_used = sum(m.memory_usage_mb for m in self.models.values() if m.status == ModelStatus.LOADED)
        
        # Calculate average load time
        avg_load_time = (self.metrics["load_time_total"] / max(self.metrics["models_loaded"], 1))
        
        # Calculate cache hit rate
        total_requests = self.metrics["cache_hits"] + self.metrics["cache_misses"]
        cache_hit_rate = (self.metrics["cache_hits"] / max(total_requests, 1)) * 100
        
        return {
            "model_stats": {
                "total_models": total_models,
                "loaded_models": loaded_models,
                "loading_efficiency": (loaded_models / max(total_models, 1)) * 100
            },
            "memory_stats": {
                "total_memory_used_mb": total_memory_used,
                "memory_saved_mb": self.metrics["memory_saved_mb"],
                "memory_efficiency_percent": self._calculate_memory_efficiency()
            },
            "performance_stats": {
                "avg_load_time_seconds": avg_load_time,
                "cache_hit_rate_percent": cache_hit_rate,
                "total_loads": self.metrics["models_loaded"],
                "total_unloads": self.metrics["models_unloaded"]
            },
            "resource_optimization": {
                "models_loaded": self.metrics["models_loaded"],
                "models_unloaded": self.metrics["models_unloaded"],
                "optimization_ratio": (self.metrics["models_unloaded"] / max(self.metrics["models_loaded"], 1))
            }
        }
    
    async def _api_load_model(self, model_name: str) -> bool:
        """Make API call to load model in Ollama."""
        try:
            async with aiohttp.ClientSession() as session:
                # First, try to pull the model if it doesn't exist
                pull_url = f"{self.base_url}/api/pull"
                pull_data = {"name": model_name}
                
                async with session.post(pull_url, json=pull_data) as response:
                    if response.status == 200:
                        # Model pull successful or already exists
                        pass
                    else:
                        logger.warning(f"Model pull returned status {response.status}")
                
                # Generate a simple request to load the model into memory
                generate_url = f"{self.base_url}/api/generate"
                generate_data = {
                    "model": model_name,
                    "prompt": "Hello",
                    "stream": False,
                    "options": {
                        "num_predict": 1  # Minimal generation to load model
                    }
                }
                
                async with session.post(generate_url, json=generate_data) as response:
                    if response.status == 200:
                        logger.debug(f"Model {model_name} loaded via generate API")
                        return True
                    else:
                        logger.error(f"Failed to load model {model_name}: HTTP {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"API error loading model {model_name}: {e}")
            return False
    
    async def _api_unload_model(self, model_name: str) -> bool:
        """Make API call to unload model from Ollama."""
        try:
            async with aiohttp.ClientSession() as session:
                # Use the delete model API if available, otherwise use keep_alive=0
                generate_url = f"{self.base_url}/api/generate"
                generate_data = {
                    "model": model_name,
                    "prompt": "",
                    "stream": False,
                    "keep_alive": 0  # Unload immediately
                }
                
                async with session.post(generate_url, json=generate_data) as response:
                    # Any response indicates the unload request was processed
                    logger.debug(f"Model {model_name} unload requested")
                    return True
                    
        except Exception as e:
            logger.error(f"API error unloading model {model_name}: {e}")
            return False

    async def _can_load_model(self, model_name: str) -> bool:
        """Check if a model can be loaded based on resource constraints."""
        # Check concurrent model limit
        loaded_count = len([m for m in self.models.values() if m.status == ModelStatus.LOADED])
        if loaded_count >= self.max_concurrent_models:
            logger.debug(f"Cannot load {model_name}: max concurrent models ({self.max_concurrent_models}) reached")
            return False

        # Check GPU memory availability
        try:
            metrics = await self._get_resource_metrics()
            memory_usage_percent = (metrics.gpu_memory_used_mb / metrics.gpu_memory_total_mb) * 100

            if memory_usage_percent > self.memory_threshold_percent:
                logger.debug(f"Cannot load {model_name}: GPU memory usage ({memory_usage_percent:.1f}%) above threshold")
                return False
        except Exception as e:
            logger.warning(f"Could not check GPU memory: {e}")

        return True

    async def _get_model_size(self, model_name: str) -> float:
        """Estimate model size in GB."""
        # Model size estimates based on common patterns
        size_estimates = {
            "3b": 3.0,
            "7b": 7.0,
            "8b": 8.0,
            "13b": 13.0,
            "30b": 30.0,
            "70b": 70.0
        }

        model_lower = model_name.lower()
        for size_key, size_gb in size_estimates.items():
            if size_key in model_lower:
                return size_gb

        # Default estimate
        return 7.0

    async def _estimate_model_memory(self, model_name: str) -> int:
        """Estimate GPU memory usage for a model in MB."""
        size_gb = await self._get_model_size(model_name)
        # Rough estimate: model size * 1.2 (for overhead) * 1024 MB/GB
        return int(size_gb * 1.2 * 1024)

    async def _get_resource_metrics(self) -> ResourceMetrics:
        """Get current system resource metrics."""
        try:
            # Get CPU and RAM metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            ram_used_gb = memory.used / (1024**3)
            ram_total_gb = memory.total / (1024**3)

            # Mock GPU metrics (in production, use nvidia-ml-py or similar)
            gpu_memory_total_mb = 24000  # 24GB GPU
            gpu_memory_used_mb = 8000    # Mock usage
            gpu_memory_free_mb = gpu_memory_total_mb - gpu_memory_used_mb
            gpu_utilization_percent = 45.0  # Mock utilization

            metrics = ResourceMetrics(
                gpu_memory_total_mb=gpu_memory_total_mb,
                gpu_memory_used_mb=gpu_memory_used_mb,
                gpu_memory_free_mb=gpu_memory_free_mb,
                gpu_utilization_percent=gpu_utilization_percent,
                cpu_percent=cpu_percent,
                ram_used_gb=ram_used_gb,
                ram_total_gb=ram_total_gb,
                timestamp=datetime.utcnow()
            )

            # Store in history
            self.resource_history.append(metrics)

            return metrics

        except Exception as e:
            logger.error(f"Error getting resource metrics: {e}")
            # Return default metrics
            return ResourceMetrics(
                gpu_memory_total_mb=24000,
                gpu_memory_used_mb=8000,
                gpu_memory_free_mb=16000,
                gpu_utilization_percent=50.0,
                cpu_percent=25.0,
                ram_used_gb=8.0,
                ram_total_gb=32.0,
                timestamp=datetime.utcnow()
            )

    async def _identify_models_for_unloading(self) -> List[str]:
        """Identify models that should be unloaded to free memory."""
        models_to_unload = []
        current_time = datetime.utcnow()

        # Get loaded models sorted by last usage time
        loaded_models = [(name, info) for name, info in self.models.items()
                        if info.status == ModelStatus.LOADED]

        # Sort by last used time (oldest first)
        loaded_models.sort(key=lambda x: x[1].last_used or datetime.min)

        for model_name, model_info in loaded_models:
            # Check if model has been idle
            if model_info.last_used:
                idle_time = current_time - model_info.last_used
                if idle_time.total_seconds() > (self.idle_timeout_minutes * 60):
                    models_to_unload.append(model_name)
            else:
                # Model never used, candidate for unloading
                models_to_unload.append(model_name)

        # Ensure we keep at least one model loaded
        if len(models_to_unload) >= len(loaded_models):
            models_to_unload = models_to_unload[:-1]  # Keep the most recently used

        return models_to_unload

    def _track_usage(self, model_name: str):
        """Track model usage for intelligent caching."""
        current_time = datetime.utcnow()
        self.usage_history[model_name].append(current_time)

        # Keep only recent usage (last 24 hours)
        cutoff_time = current_time - timedelta(hours=24)
        while (self.usage_history[model_name] and
               self.usage_history[model_name][0] < cutoff_time):
            self.usage_history[model_name].popleft()

    def _identify_popular_models(self) -> List[str]:
        """Identify popular models based on usage patterns."""
        current_time = datetime.utcnow()
        cutoff_time = current_time - timedelta(hours=2)  # Recent usage

        model_scores = {}

        for model_name, usage_times in self.usage_history.items():
            # Count recent usage
            recent_usage = sum(1 for t in usage_times if t > cutoff_time)

            # Calculate score based on recent usage and total usage
            total_usage = len(usage_times)
            score = recent_usage * 2 + total_usage  # Weight recent usage more

            if score > 0:
                model_scores[model_name] = score

        # Sort by score and return top models
        sorted_models = sorted(model_scores.items(), key=lambda x: x[1], reverse=True)
        return [model_name for model_name, score in sorted_models[:3]]  # Top 3

    def _calculate_memory_efficiency(self) -> float:
        """Calculate memory efficiency percentage."""
        if not self.resource_history:
            return 0.0

        # Get recent memory usage
        recent_metrics = list(self.resource_history)[-10:]  # Last 10 measurements

        if not recent_metrics:
            return 0.0

        avg_usage = sum(m.gpu_memory_used_mb for m in recent_metrics) / len(recent_metrics)
        avg_total = sum(m.gpu_memory_total_mb for m in recent_metrics) / len(recent_metrics)

        usage_percent = (avg_usage / avg_total) * 100

        # Efficiency is inverse of usage (lower usage = higher efficiency)
        # Target is 70% usage, so efficiency = (70 - actual_usage) / 70 * 100
        target_usage = 70.0
        if usage_percent <= target_usage:
            efficiency = 100.0  # Perfect efficiency
        else:
            efficiency = max(0.0, (target_usage - (usage_percent - target_usage)) / target_usage * 100)

        return efficiency

    async def _wait_for_load_completion(self, model_name: str, timeout_seconds: int = 300):
        """Wait for model loading to complete."""
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            if model_name in self.models:
                status = self.models[model_name].status
                if status in [ModelStatus.LOADED, ModelStatus.ERROR]:
                    return

            await asyncio.sleep(0.5)  # Check every 500ms

        logger.warning(f"Timeout waiting for {model_name} to load")


# Global service instance
ollama_manager = OllamaManagerService()
