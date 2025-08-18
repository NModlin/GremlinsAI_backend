"""
Metrics Service for Phase 4, Task 4.2: Monitoring & Observability

This module provides comprehensive metrics collection using Prometheus client library.
It tracks application-level, system-level, and business-level metrics for operational
excellence and production monitoring.

Features:
- Request latency and throughput metrics
- Error rate and status code tracking
- System resource utilization
- Business KPIs (documents processed, RAG queries, etc.)
- WebSocket connection monitoring
- LLM and Weaviate performance metrics
"""

import time
import psutil
import threading
from typing import Dict, Optional, Any
from datetime import datetime
from collections import defaultdict

from prometheus_client import (
    Counter, Gauge, Histogram, Info, Enum,
    CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
)

from app.core.config import get_settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


class MetricsService:
    """
    Comprehensive metrics service for GremlinsAI application monitoring.
    
    Provides Prometheus-compatible metrics for application performance,
    system health, and business KPIs with production-ready observability.
    """
    
    def __init__(self):
        """Initialize metrics service with all required metrics."""
        self.registry = CollectorRegistry()
        self._initialize_metrics()
        self._start_system_metrics_collector()
        
        logger.info("MetricsService initialized with comprehensive monitoring")
    
    def _initialize_metrics(self):
        """Initialize all Prometheus metrics."""
        
        # === APPLICATION METRICS ===
        
        # Request metrics
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total number of HTTP requests',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )
        
        self.http_request_duration_seconds = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint'],
            buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self.registry
        )
        
        self.http_request_size_bytes = Histogram(
            'http_request_size_bytes',
            'HTTP request size in bytes',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        self.http_response_size_bytes = Histogram(
            'http_response_size_bytes',
            'HTTP response size in bytes',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        # Active connections and users
        self.active_connections = Gauge(
            'active_connections_total',
            'Number of active connections',
            ['connection_type'],
            registry=self.registry
        )
        
        self.active_users = Gauge(
            'active_users_total',
            'Number of active authenticated users',
            registry=self.registry
        )
        
        # === SYSTEM METRICS ===
        
        self.cpu_usage_percent = Gauge(
            'cpu_usage_percent',
            'CPU usage percentage',
            ['cpu'],
            registry=self.registry
        )
        
        self.memory_usage_bytes = Gauge(
            'memory_usage_bytes',
            'Memory usage in bytes',
            ['type'],
            registry=self.registry
        )
        
        self.disk_usage_bytes = Gauge(
            'disk_usage_bytes',
            'Disk usage in bytes',
            ['mountpoint', 'type'],
            registry=self.registry
        )
        
        self.network_bytes_total = Counter(
            'network_bytes_total',
            'Total network bytes',
            ['direction', 'interface'],
            registry=self.registry
        )
        
        # === BUSINESS METRICS ===
        
        # Document processing
        self.documents_processed_total = Counter(
            'documents_processed_total',
            'Total number of documents processed',
            ['document_type', 'status'],
            registry=self.registry
        )
        
        self.document_processing_duration_seconds = Histogram(
            'document_processing_duration_seconds',
            'Document processing duration in seconds',
            ['document_type'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0],
            registry=self.registry
        )
        
        # RAG system metrics
        self.rag_queries_total = Counter(
            'rag_queries_total',
            'Total number of RAG queries',
            ['query_type', 'status'],
            registry=self.registry
        )
        
        self.rag_query_duration_seconds = Histogram(
            'rag_query_duration_seconds',
            'RAG query duration in seconds',
            ['query_type'],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0],
            registry=self.registry
        )
        
        self.rag_similarity_scores = Histogram(
            'rag_similarity_scores',
            'RAG similarity scores distribution',
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            registry=self.registry
        )
        
        # Multi-agent metrics
        self.multi_agent_tasks_total = Counter(
            'multi_agent_tasks_total',
            'Total number of multi-agent tasks',
            ['workflow_type', 'status'],
            registry=self.registry
        )
        
        self.multi_agent_task_duration_seconds = Histogram(
            'multi_agent_task_duration_seconds',
            'Multi-agent task duration in seconds',
            ['workflow_type'],
            buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0],
            registry=self.registry
        )
        
        self.agent_interactions_total = Counter(
            'agent_interactions_total',
            'Total number of agent interactions',
            ['agent_type', 'interaction_type'],
            registry=self.registry
        )
        
        # LLM metrics
        self.llm_requests_total = Counter(
            'llm_requests_total',
            'Total number of LLM requests',
            ['provider', 'model', 'status'],
            registry=self.registry
        )
        
        self.llm_request_duration_seconds = Histogram(
            'llm_request_duration_seconds',
            'LLM request duration in seconds',
            ['provider', 'model'],
            buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0],
            registry=self.registry
        )
        
        self.llm_tokens_total = Counter(
            'llm_tokens_total',
            'Total number of LLM tokens',
            ['provider', 'model', 'type'],
            registry=self.registry
        )
        
        # Weaviate metrics
        self.weaviate_queries_total = Counter(
            'weaviate_queries_total',
            'Total number of Weaviate queries',
            ['query_type', 'status'],
            registry=self.registry
        )
        
        self.weaviate_query_duration_seconds = Histogram(
            'weaviate_query_duration_seconds',
            'Weaviate query duration in seconds',
            ['query_type'],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0],
            registry=self.registry
        )
        
        # WebSocket metrics
        self.websocket_connections_total = Gauge(
            'websocket_connections_total',
            'Number of active WebSocket connections',
            ['endpoint'],
            registry=self.registry
        )
        
        self.websocket_messages_total = Counter(
            'websocket_messages_total',
            'Total number of WebSocket messages',
            ['endpoint', 'direction'],
            registry=self.registry
        )
        
        # Security metrics
        self.security_events_total = Counter(
            'security_events_total',
            'Total number of security events',
            ['event_type', 'severity'],
            registry=self.registry
        )
        
        self.authentication_attempts_total = Counter(
            'authentication_attempts_total',
            'Total number of authentication attempts',
            ['status', 'method'],
            registry=self.registry
        )
        
        # Application info
        self.app_info = Info(
            'app_info',
            'Application information',
            registry=self.registry
        )
        
        self.app_info.info({
            'version': getattr(settings, 'version', '1.0.0'),
            'environment': getattr(settings, 'environment', 'development'),
            'build_time': datetime.utcnow().isoformat()
        })
        
        # Application status
        self.app_status = Enum(
            'app_status',
            'Application status',
            states=['starting', 'healthy', 'degraded', 'unhealthy'],
            registry=self.registry
        )
        
        self.app_status.state('healthy')
    
    def _start_system_metrics_collector(self):
        """Start background thread to collect system metrics."""
        def collect_system_metrics():
            while True:
                try:
                    # CPU metrics
                    cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
                    for i, cpu in enumerate(cpu_percent):
                        self.cpu_usage_percent.labels(cpu=f'cpu{i}').set(cpu)
                    
                    # Memory metrics
                    memory = psutil.virtual_memory()
                    self.memory_usage_bytes.labels(type='used').set(memory.used)
                    self.memory_usage_bytes.labels(type='available').set(memory.available)
                    self.memory_usage_bytes.labels(type='total').set(memory.total)
                    
                    # Disk metrics
                    for partition in psutil.disk_partitions():
                        try:
                            usage = psutil.disk_usage(partition.mountpoint)
                            self.disk_usage_bytes.labels(
                                mountpoint=partition.mountpoint,
                                type='used'
                            ).set(usage.used)
                            self.disk_usage_bytes.labels(
                                mountpoint=partition.mountpoint,
                                type='free'
                            ).set(usage.free)
                            self.disk_usage_bytes.labels(
                                mountpoint=partition.mountpoint,
                                type='total'
                            ).set(usage.total)
                        except PermissionError:
                            continue
                    
                    # Network metrics
                    network = psutil.net_io_counters(pernic=True)
                    for interface, stats in network.items():
                        self.network_bytes_total.labels(
                            direction='sent',
                            interface=interface
                        )._value._value = stats.bytes_sent
                        
                        self.network_bytes_total.labels(
                            direction='received',
                            interface=interface
                        )._value._value = stats.bytes_recv
                
                except Exception as e:
                    logger.error(f"Error collecting system metrics: {e}")
                
                time.sleep(30)  # Collect every 30 seconds
        
        thread = threading.Thread(target=collect_system_metrics, daemon=True)
        thread.start()
        logger.info("System metrics collector started")
    
    def record_http_request(self, method: str, endpoint: str, status_code: int, 
                          duration: float, request_size: int = 0, response_size: int = 0):
        """Record HTTP request metrics."""
        self.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        self.http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
        
        if request_size > 0:
            self.http_request_size_bytes.labels(
                method=method,
                endpoint=endpoint
            ).observe(request_size)
        
        if response_size > 0:
            self.http_response_size_bytes.labels(
                method=method,
                endpoint=endpoint
            ).observe(response_size)
    
    def record_document_processing(self, document_type: str, status: str, duration: float):
        """Record document processing metrics."""
        self.documents_processed_total.labels(
            document_type=document_type,
            status=status
        ).inc()
        
        self.document_processing_duration_seconds.labels(
            document_type=document_type
        ).observe(duration)
    
    def record_rag_query(self, query_type: str, status: str, duration: float, 
                        similarity_score: Optional[float] = None):
        """Record RAG query metrics."""
        self.rag_queries_total.labels(
            query_type=query_type,
            status=status
        ).inc()
        
        self.rag_query_duration_seconds.labels(
            query_type=query_type
        ).observe(duration)
        
        if similarity_score is not None:
            self.rag_similarity_scores.observe(similarity_score)
    
    def record_multi_agent_task(self, workflow_type: str, status: str, duration: float):
        """Record multi-agent task metrics."""
        self.multi_agent_tasks_total.labels(
            workflow_type=workflow_type,
            status=status
        ).inc()
        
        self.multi_agent_task_duration_seconds.labels(
            workflow_type=workflow_type
        ).observe(duration)
    
    def record_llm_request(self, provider: str, model: str, status: str, 
                          duration: float, input_tokens: int = 0, output_tokens: int = 0):
        """Record LLM request metrics."""
        self.llm_requests_total.labels(
            provider=provider,
            model=model,
            status=status
        ).inc()
        
        self.llm_request_duration_seconds.labels(
            provider=provider,
            model=model
        ).observe(duration)
        
        if input_tokens > 0:
            self.llm_tokens_total.labels(
                provider=provider,
                model=model,
                type='input'
            ).inc(input_tokens)
        
        if output_tokens > 0:
            self.llm_tokens_total.labels(
                provider=provider,
                model=model,
                type='output'
            ).inc(output_tokens)
    
    def record_weaviate_query(self, query_type: str, status: str, duration: float):
        """Record Weaviate query metrics."""
        self.weaviate_queries_total.labels(
            query_type=query_type,
            status=status
        ).inc()
        
        self.weaviate_query_duration_seconds.labels(
            query_type=query_type
        ).observe(duration)
    
    def record_security_event(self, event_type: str, severity: str):
        """Record security event metrics."""
        self.security_events_total.labels(
            event_type=event_type,
            severity=severity
        ).inc()
    
    def set_active_connections(self, connection_type: str, count: int):
        """Set active connections count."""
        self.active_connections.labels(connection_type=connection_type).set(count)
    
    def set_active_users(self, count: int):
        """Set active users count."""
        self.active_users.set(count)
    
    def set_websocket_connections(self, endpoint: str, count: int):
        """Set WebSocket connections count."""
        self.websocket_connections_total.labels(endpoint=endpoint).set(count)
    
    def record_websocket_message(self, endpoint: str, direction: str):
        """Record WebSocket message."""
        self.websocket_messages_total.labels(
            endpoint=endpoint,
            direction=direction
        ).inc()
    
    def get_metrics(self) -> str:
        """Get metrics in Prometheus format."""
        return generate_latest(self.registry).decode('utf-8')
    
    def get_content_type(self) -> str:
        """Get Prometheus metrics content type."""
        return CONTENT_TYPE_LATEST


# Global metrics service instance
metrics_service = MetricsService()
