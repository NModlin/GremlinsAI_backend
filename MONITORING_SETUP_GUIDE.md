# GremlinsAI Monitoring & Observability Setup Guide

## Phase 4, Task 4.2: Monitoring & Observability - Complete Implementation

This guide provides comprehensive instructions for setting up and operating the GremlinsAI monitoring and observability stack.

## 🎯 **Overview**

The monitoring stack provides:
- **Metrics Collection**: Prometheus with comprehensive application and system metrics
- **Visualization**: Grafana dashboards for operational insights
- **Distributed Tracing**: OpenTelemetry with Jaeger for request flow analysis
- **Alerting**: Prometheus AlertManager with multi-channel notifications
- **Log Aggregation**: Loki and Promtail for centralized logging

## 📊 **Architecture**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   GremlinsAI    │───▶│   Prometheus    │───▶│    Grafana      │
│   Application   │    │   (Metrics)     │    │  (Dashboards)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐              │
         │              │  AlertManager   │              │
         │              │   (Alerting)    │              │
         │              └─────────────────┘              │
         │                                               │
         ▼                                               ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Jaeger      │    │      Loki       │    │   Monitoring    │
│   (Tracing)     │    │   (Logging)     │    │   Dashboard     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 **Quick Start**

### 1. **Start Monitoring Stack**

```bash
# Start the complete monitoring stack
cd ops/
docker-compose -f docker-compose.monitoring.yml up -d

# Verify all services are running
docker-compose -f docker-compose.monitoring.yml ps
```

### 2. **Access Monitoring Services**

- **Grafana**: http://localhost:3000 (admin/admin123)
- **Prometheus**: http://localhost:9090
- **Jaeger**: http://localhost:16686
- **AlertManager**: http://localhost:9093

### 3. **Start GremlinsAI with Monitoring**

```bash
# Ensure monitoring dependencies are installed
pip install prometheus-client opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi

# Start the application
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 📈 **Metrics Collection**

### **Application Metrics**

The application exposes metrics at `/metrics` endpoint:

```bash
curl http://localhost:8000/metrics
```

**Key Metrics:**
- `http_requests_total` - Total HTTP requests by method, endpoint, status
- `http_request_duration_seconds` - Request latency histograms
- `rag_queries_total` - RAG system queries by type and status
- `multi_agent_tasks_total` - Multi-agent tasks by workflow and status
- `llm_requests_total` - LLM API calls by provider and model
- `weaviate_queries_total` - Vector database queries
- `websocket_connections_total` - Active WebSocket connections
- `security_events_total` - Security events by type and severity

### **System Metrics**

Collected via Node Exporter and cAdvisor:
- CPU usage per core
- Memory usage (used, available, total)
- Disk usage by mount point
- Network I/O by interface
- Container resource usage

### **Business Metrics**

Key performance indicators:
- Documents processed per hour
- RAG query success rate
- Multi-agent task completion time
- LLM token usage
- User activity metrics

## 📊 **Grafana Dashboards**

### **Main Application Overview**
- **File**: `ops/grafana/dashboards/main-application-overview.json`
- **URL**: http://localhost:3000/d/gremlinsai-main-overview
- **Panels**:
  - Request Rate (RPS)
  - Error Rate (%)
  - Request Latency (95th/99th percentiles)
  - Active WebSocket Connections
  - CPU Usage per Core
  - Memory Usage

### **Business Metrics Dashboard**
- **File**: `ops/grafana/dashboards/business-metrics.json`
- **URL**: http://localhost:3000/d/gremlinsai-business-metrics
- **Panels**:
  - Documents Processed (24h)
  - RAG Queries (24h)
  - Multi-Agent Tasks (24h)
  - LLM Tokens Used (24h)
  - Processing Rates and Durations

### **Dashboard Import**

```bash
# Import dashboards via API
curl -X POST \
  http://admin:admin123@localhost:3000/api/dashboards/db \
  -H 'Content-Type: application/json' \
  -d @ops/grafana/dashboards/main-application-overview.json
```

## 🔍 **Distributed Tracing**

### **Jaeger Configuration**

Traces are automatically collected for:
- HTTP requests (via FastAPI instrumentation)
- RAG system operations
- Multi-agent workflows
- LLM API calls
- Weaviate queries
- Database operations

### **Viewing Traces**

1. Open Jaeger UI: http://localhost:16686
2. Select service: `gremlinsai`
3. Search for traces by operation or time range
4. Analyze request flows and performance bottlenecks

### **Custom Tracing**

```python
from app.core.tracing_service import tracing_service

# Trace a custom operation
with tracing_service.trace_operation("custom_operation") as span:
    span.set_attribute("custom.attribute", "value")
    # Your code here
```

## 🚨 **Alerting**

### **Alert Rules**

Defined in `ops/prometheus/rules/alerts.yml`:

**Critical Alerts:**
- `HighApiErrorRate`: >5% error rate for >5 minutes
- `HighApiLatency`: 95th percentile >2 seconds
- `HostOutOfMemory`: >90% memory usage
- `ApiDown`: Service unavailable

**Warning Alerts:**
- `HighCpuUsage`: >80% CPU for >10 minutes
- `DiskSpaceLow`: <10% disk space
- `LLMApiFailures`: >10% LLM failure rate
- `WeaviateQueryLatency`: >1s query latency

### **Alert Channels**

Configure in `ops/alertmanager/alertmanager.yml`:
- **Email**: Critical alerts to SRE team
- **Slack**: Real-time notifications
- **PagerDuty**: On-call escalation
- **Webhooks**: Custom integrations

### **Testing Alerts**

```bash
# Test alert firing
curl -X POST http://localhost:9093/api/v1/alerts \
  -H 'Content-Type: application/json' \
  -d '[{
    "labels": {
      "alertname": "TestAlert",
      "severity": "warning"
    },
    "annotations": {
      "summary": "Test alert"
    }
  }]'
```

## 🔧 **Configuration**

### **Environment Variables**

```bash
# Tracing configuration
export JAEGER_ENDPOINT=http://localhost:14268/api/traces
export OTLP_ENDPOINT=http://localhost:4317

# Metrics configuration
export PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus_multiproc_dir

# Application configuration
export MONITORING_ENABLED=true
export TRACING_ENABLED=true
```

### **Production Configuration**

For production deployment:

1. **Update Prometheus targets** in `prometheus.yml`
2. **Configure AlertManager** with real notification channels
3. **Set up external storage** for long-term metrics retention
4. **Configure TLS** for secure communication
5. **Set resource limits** for monitoring containers

## 📋 **Operational Runbooks**

### **High Error Rate Response**

1. **Check Grafana dashboard** for error patterns
2. **Review Jaeger traces** for failed requests
3. **Check application logs** in Loki
4. **Verify external dependencies** (LLM providers, Weaviate)
5. **Scale resources** if needed

### **High Latency Response**

1. **Identify slow endpoints** in Grafana
2. **Analyze traces** in Jaeger for bottlenecks
3. **Check system resources** (CPU, memory, disk)
4. **Review database performance**
5. **Optimize slow operations**

### **Memory Issues Response**

1. **Check memory usage trends** in Grafana
2. **Identify memory-intensive processes**
3. **Review application memory leaks**
4. **Scale vertically** or **restart services**
5. **Implement memory optimizations**

## 🧪 **Testing & Validation**

### **Metrics Validation**

```bash
# Check metrics endpoint
curl http://localhost:8000/metrics | grep http_requests_total

# Validate Prometheus scraping
curl http://localhost:9090/api/v1/query?query=up{job="gremlinsai"}
```

### **Tracing Validation**

```bash
# Generate test requests
for i in {1..10}; do
  curl http://localhost:8000/api/v1/health
done

# Check traces in Jaeger UI
```

### **Alerting Validation**

```bash
# Trigger test alert
curl -X POST http://localhost:8000/api/v1/test/error-rate

# Check AlertManager UI for firing alerts
```

## 🔒 **Security Considerations**

1. **Secure endpoints** with authentication
2. **Use TLS** for external communication
3. **Limit metric exposure** to internal networks
4. **Sanitize sensitive data** in traces and logs
5. **Regular security updates** for monitoring components

## 📚 **Troubleshooting**

### **Common Issues**

**Metrics not appearing:**
- Check application `/metrics` endpoint
- Verify Prometheus scraping configuration
- Check network connectivity

**Traces not showing:**
- Verify Jaeger endpoint configuration
- Check OpenTelemetry instrumentation
- Review application logs for tracing errors

**Alerts not firing:**
- Validate alert rule syntax
- Check Prometheus rule evaluation
- Verify AlertManager configuration

### **Log Locations**

```bash
# Application logs
docker logs gremlinsai-app

# Prometheus logs
docker logs gremlinsai-prometheus

# Grafana logs
docker logs gremlinsai-grafana

# Jaeger logs
docker logs gremlinsai-jaeger
```

## 🎯 **Performance Tuning**

### **Metrics Optimization**

- Adjust scrape intervals based on requirements
- Use recording rules for expensive queries
- Implement metric retention policies
- Optimize label cardinality

### **Tracing Optimization**

- Configure sampling rates for high-volume services
- Use head-based sampling for critical operations
- Implement trace filtering for noise reduction
- Optimize span attribute usage

### **Storage Optimization**

- Configure retention policies
- Use external storage for long-term data
- Implement data compression
- Regular cleanup of old data

## 📈 **Scaling Considerations**

### **High Availability**

- Deploy Prometheus in HA mode
- Use Grafana clustering
- Implement AlertManager clustering
- Set up external storage backends

### **Performance Scaling**

- Horizontal scaling of monitoring components
- Load balancing for high-traffic scenarios
- Distributed tracing backends
- Federated Prometheus setup

This monitoring setup provides comprehensive observability for GremlinsAI, enabling proactive issue detection, performance optimization, and operational excellence in production environments.
