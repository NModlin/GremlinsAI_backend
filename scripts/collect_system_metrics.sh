#!/bin/bash
# System Metrics Collection Script for Load Testing
# Phase 4, Task 4.4: Load Testing & Optimization
#
# This script collects comprehensive system metrics during load testing
# to identify performance bottlenecks and validate resource utilization.
#
# Usage: ./collect_system_metrics.sh [output_file]

set -euo pipefail

# Configuration
OUTPUT_FILE="${1:-system_metrics_$(date +%Y%m%d_%H%M%S).json}"
COLLECTION_INTERVAL=10  # seconds
MAX_DURATION=7200      # 2 hours maximum

# Metrics storage
METRICS_DATA=()
START_TIME=$(date +%s)

# Logging
log() {
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" >&2
}

# Collect CPU metrics
collect_cpu_metrics() {
    local cpu_usage
    cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | sed 's/%us,//')
    
    # Get per-core CPU usage
    local cpu_cores
    cpu_cores=$(nproc)
    
    # Get load average
    local load_avg
    load_avg=$(uptime | awk -F'load average:' '{print $2}' | sed 's/^ *//')
    
    echo "{\"cpu_usage_percent\": ${cpu_usage:-0}, \"cpu_cores\": ${cpu_cores}, \"load_average\": \"${load_avg}\"}"
}

# Collect memory metrics
collect_memory_metrics() {
    local mem_info
    mem_info=$(free -m | awk 'NR==2{printf "{\"total_mb\": %s, \"used_mb\": %s, \"free_mb\": %s, \"usage_percent\": %.2f}", $2, $3, $4, $3*100/$2}')
    
    echo "${mem_info}"
}

# Collect disk metrics
collect_disk_metrics() {
    local disk_usage
    disk_usage=$(df -h / | awk 'NR==2{printf "{\"total\": \"%s\", \"used\": \"%s\", \"available\": \"%s\", \"usage_percent\": \"%s\"}", $2, $3, $4, $5}')
    
    # Get disk I/O stats
    local disk_io=""
    if command -v iostat &> /dev/null; then
        disk_io=$(iostat -d 1 2 | tail -n +4 | awk 'NR==1{printf ", \"io_reads_per_sec\": %.2f, \"io_writes_per_sec\": %.2f", $4, $5}')
    fi
    
    echo "${disk_usage}${disk_io}"
}

# Collect network metrics
collect_network_metrics() {
    local network_stats=""
    
    if [[ -f /proc/net/dev ]]; then
        # Get network interface stats
        local rx_bytes tx_bytes
        rx_bytes=$(cat /proc/net/dev | awk 'NR>2{sum+=$2} END{print sum+0}')
        tx_bytes=$(cat /proc/net/dev | awk 'NR>2{sum+=$10} END{print sum+0}')
        
        network_stats="{\"rx_bytes\": ${rx_bytes}, \"tx_bytes\": ${tx_bytes}}"
    else
        network_stats="{\"rx_bytes\": 0, \"tx_bytes\": 0}"
    fi
    
    echo "${network_stats}"
}

# Collect Kubernetes metrics (if available)
collect_kubernetes_metrics() {
    local k8s_metrics="{}"
    
    if command -v kubectl &> /dev/null; then
        # Get pod resource usage
        local pod_cpu pod_memory
        pod_cpu=$(kubectl top pods -n gremlinsai --no-headers 2>/dev/null | awk '{sum+=$2} END{print sum+0}' || echo "0")
        pod_memory=$(kubectl top pods -n gremlinsai --no-headers 2>/dev/null | awk '{sum+=$3} END{print sum+0}' || echo "0")
        
        # Get pod count
        local pod_count
        pod_count=$(kubectl get pods -n gremlinsai --no-headers 2>/dev/null | wc -l || echo "0")
        
        # Get HPA status
        local hpa_replicas=""
        if kubectl get hpa -n gremlinsai &>/dev/null; then
            hpa_replicas=$(kubectl get hpa -n gremlinsai -o json 2>/dev/null | jq -r '.items[0].status.currentReplicas // 0' || echo "0")
        else
            hpa_replicas="0"
        fi
        
        k8s_metrics="{\"pod_cpu_total\": \"${pod_cpu}\", \"pod_memory_total\": \"${pod_memory}\", \"pod_count\": ${pod_count}, \"hpa_replicas\": ${hpa_replicas}}"
    fi
    
    echo "${k8s_metrics}"
}

# Collect application-specific metrics
collect_application_metrics() {
    local app_metrics="{}"
    
    # Try to get metrics from application health endpoint
    if command -v curl &> /dev/null; then
        local health_response
        health_response=$(curl -s -f http://localhost:8000/api/v1/health 2>/dev/null || echo "{}")
        
        if [[ "${health_response}" != "{}" ]]; then
            app_metrics="${health_response}"
        fi
    fi
    
    echo "${app_metrics}"
}

# Collect Prometheus metrics (if available)
collect_prometheus_metrics() {
    local prom_metrics="{}"
    
    if command -v curl &> /dev/null; then
        local prometheus_url="http://localhost:9090"
        
        # Check if Prometheus is available
        if curl -s -f "${prometheus_url}/api/v1/query?query=up" &>/dev/null; then
            # Get key application metrics
            local http_requests_rate
            http_requests_rate=$(curl -s "${prometheus_url}/api/v1/query?query=rate(http_requests_total[5m])" | jq -r '.data.result[0].value[1] // "0"' 2>/dev/null || echo "0")
            
            local http_request_duration
            http_request_duration=$(curl -s "${prometheus_url}/api/v1/query?query=histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))" | jq -r '.data.result[0].value[1] // "0"' 2>/dev/null || echo "0")
            
            local active_connections
            active_connections=$(curl -s "${prometheus_url}/api/v1/query?query=http_active_connections" | jq -r '.data.result[0].value[1] // "0"' 2>/dev/null || echo "0")
            
            prom_metrics="{\"http_requests_per_sec\": ${http_requests_rate}, \"http_p95_duration_sec\": ${http_request_duration}, \"active_connections\": ${active_connections}}"
        fi
    fi
    
    echo "${prom_metrics}"
}

# Collect comprehensive metrics
collect_metrics() {
    local timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    local epoch_time=$(date +%s)
    
    log "Collecting metrics at ${timestamp}"
    
    # Collect all metrics
    local cpu_metrics
    cpu_metrics=$(collect_cpu_metrics)
    
    local memory_metrics
    memory_metrics=$(collect_memory_metrics)
    
    local disk_metrics
    disk_metrics=$(collect_disk_metrics)
    
    local network_metrics
    network_metrics=$(collect_network_metrics)
    
    local k8s_metrics
    k8s_metrics=$(collect_kubernetes_metrics)
    
    local app_metrics
    app_metrics=$(collect_application_metrics)
    
    local prom_metrics
    prom_metrics=$(collect_prometheus_metrics)
    
    # Combine all metrics
    local combined_metrics
    combined_metrics=$(cat << EOF
{
    "timestamp": "${timestamp}",
    "epoch_time": ${epoch_time},
    "cpu": ${cpu_metrics},
    "memory": ${memory_metrics},
    "disk": ${disk_metrics},
    "network": ${network_metrics},
    "kubernetes": ${k8s_metrics},
    "application": ${app_metrics},
    "prometheus": ${prom_metrics}
}
EOF
)
    
    echo "${combined_metrics}"
}

# Save metrics to file
save_metrics() {
    local metrics_json="$1"
    
    # Create metrics array if file doesn't exist
    if [[ ! -f "${OUTPUT_FILE}" ]]; then
        echo '{"metrics": [], "collection_info": {}}' > "${OUTPUT_FILE}"
    fi
    
    # Add new metrics to array
    local temp_file=$(mktemp)
    jq --argjson new_metric "${metrics_json}" '.metrics += [$new_metric]' "${OUTPUT_FILE}" > "${temp_file}"
    mv "${temp_file}" "${OUTPUT_FILE}"
}

# Update collection info
update_collection_info() {
    local end_time=$(date +%s)
    local duration=$((end_time - START_TIME))
    local total_samples=$(jq '.metrics | length' "${OUTPUT_FILE}")
    
    local collection_info=$(cat << EOF
{
    "start_time": "${START_TIME}",
    "end_time": "${end_time}",
    "duration_seconds": ${duration},
    "collection_interval_seconds": ${COLLECTION_INTERVAL},
    "total_samples": ${total_samples},
    "output_file": "${OUTPUT_FILE}"
}
EOF
)
    
    local temp_file=$(mktemp)
    jq --argjson info "${collection_info}" '.collection_info = $info' "${OUTPUT_FILE}" > "${temp_file}"
    mv "${temp_file}" "${OUTPUT_FILE}"
}

# Signal handlers
cleanup() {
    log "Stopping metrics collection..."
    update_collection_info
    log "Metrics saved to: ${OUTPUT_FILE}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Main collection loop
main() {
    log "Starting system metrics collection"
    log "Output file: ${OUTPUT_FILE}"
    log "Collection interval: ${COLLECTION_INTERVAL} seconds"
    log "Maximum duration: ${MAX_DURATION} seconds"
    
    local iteration=0
    local max_iterations=$((MAX_DURATION / COLLECTION_INTERVAL))
    
    while [[ ${iteration} -lt ${max_iterations} ]]; do
        # Collect metrics
        local metrics
        metrics=$(collect_metrics)
        
        # Save to file
        save_metrics "${metrics}"
        
        # Sleep until next collection
        sleep "${COLLECTION_INTERVAL}"
        
        ((iteration++))
        
        # Log progress every 10 iterations
        if [[ $((iteration % 10)) -eq 0 ]]; then
            log "Collected ${iteration} samples ($(( iteration * COLLECTION_INTERVAL )) seconds elapsed)"
        fi
    done
    
    log "Maximum duration reached, stopping collection"
    cleanup
}

# Check if running as background process
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Running directly
    main "$@"
fi
