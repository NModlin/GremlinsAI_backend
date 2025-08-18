#!/bin/bash

# Deployment Validation Script for GremlinsAI Backend - Task T3.7
# 
# This script validates the production deployment and ensures all
# components are functioning correctly after blue-green deployment.

set -euo pipefail

# Configuration
NAMESPACE="${NAMESPACE:-gremlinsai}"
SERVICE_NAME="${SERVICE_NAME:-gremlinsai-service}"
APP_NAME="${APP_NAME:-gremlinsai-backend}"
VALIDATION_TIMEOUT="${VALIDATION_TIMEOUT:-300}"
LOAD_TEST_DURATION="${LOAD_TEST_DURATION:-60}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

print_header() {
    echo "================================================================================"
    echo "🔍 GremlinsAI Production Deployment Validation - Task T3.7"
    echo "================================================================================"
    echo "Namespace: $NAMESPACE"
    echo "Service: $SERVICE_NAME"
    echo "Application: $APP_NAME"
    echo "================================================================================"
}

# Get current active version
get_active_version() {
    local version
    version=$(kubectl get service "$SERVICE_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.selector.version}' 2>/dev/null || echo "")
    
    if [[ -z "$version" ]]; then
        log_error "Could not determine active version"
        return 1
    fi
    
    echo "$version"
}

# Validate Kubernetes resources
validate_kubernetes_resources() {
    log_info "Validating Kubernetes resources..."
    
    local active_version
    active_version=$(get_active_version)
    local deployment_name="${APP_NAME}-${active_version}"
    
    # Check deployment
    if kubectl get deployment "$deployment_name" -n "$NAMESPACE" &> /dev/null; then
        local ready_replicas
        ready_replicas=$(kubectl get deployment "$deployment_name" -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}')
        local desired_replicas
        desired_replicas=$(kubectl get deployment "$deployment_name" -n "$NAMESPACE" -o jsonpath='{.spec.replicas}')
        
        if [[ "$ready_replicas" == "$desired_replicas" ]] && [[ "$ready_replicas" -gt 0 ]]; then
            log_success "Deployment '$deployment_name' is healthy ($ready_replicas/$desired_replicas replicas ready)"
        else
            log_error "Deployment '$deployment_name' is not healthy ($ready_replicas/$desired_replicas replicas ready)"
            return 1
        fi
    else
        log_error "Deployment '$deployment_name' not found"
        return 1
    fi
    
    # Check service
    if kubectl get service "$SERVICE_NAME" -n "$NAMESPACE" &> /dev/null; then
        local endpoints
        endpoints=$(kubectl get endpoints "$SERVICE_NAME" -n "$NAMESPACE" -o jsonpath='{.subsets[*].addresses[*].ip}' | wc -w)
        
        if [[ $endpoints -gt 0 ]]; then
            log_success "Service '$SERVICE_NAME' has $endpoints healthy endpoints"
        else
            log_error "Service '$SERVICE_NAME' has no healthy endpoints"
            return 1
        fi
    else
        log_error "Service '$SERVICE_NAME' not found"
        return 1
    fi
    
    # Check pods
    local pod_count
    pod_count=$(kubectl get pods -n "$NAMESPACE" -l "app=$APP_NAME,version=$active_version" --field-selector=status.phase=Running | wc -l)
    pod_count=$((pod_count - 1))  # Subtract header line
    
    if [[ $pod_count -gt 0 ]]; then
        log_success "$pod_count pods are running for version $active_version"
    else
        log_error "No running pods found for version $active_version"
        return 1
    fi
    
    log_success "Kubernetes resources validation passed"
}

# Validate health endpoints
validate_health_endpoints() {
    log_info "Validating health endpoints..."
    
    local active_version
    active_version=$(get_active_version)
    
    # Get a pod for health check
    local pod_name
    pod_name=$(kubectl get pods -n "$NAMESPACE" -l "app=$APP_NAME,version=$active_version" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    
    if [[ -z "$pod_name" ]]; then
        log_error "No pods found for health check"
        return 1
    fi
    
    # Health check endpoints
    local endpoints=("/api/v1/health/health" "/api/v1/health/ready" "/api/v1/health/live")
    
    for endpoint in "${endpoints[@]}"; do
        log_info "Checking health endpoint: $endpoint"
        
        # Use kubectl exec to check health endpoint
        if kubectl exec -n "$NAMESPACE" "$pod_name" -- curl -f -s --max-time 10 "http://localhost:8080$endpoint" > /dev/null 2>&1; then
            log_success "Health endpoint $endpoint is responding"
        else
            log_error "Health endpoint $endpoint is not responding"
            return 1
        fi
    done
    
    log_success "Health endpoints validation passed"
}

# Validate API functionality
validate_api_functionality() {
    log_info "Validating API functionality..."
    
    local active_version
    active_version=$(get_active_version)
    
    # Get a pod for API testing
    local pod_name
    pod_name=$(kubectl get pods -n "$NAMESPACE" -l "app=$APP_NAME,version=$active_version" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    
    if [[ -z "$pod_name" ]]; then
        log_error "No pods found for API testing"
        return 1
    fi
    
    # Test root endpoint
    log_info "Testing root endpoint..."
    if kubectl exec -n "$NAMESPACE" "$pod_name" -- curl -f -s --max-time 10 "http://localhost:8080/" > /dev/null 2>&1; then
        log_success "Root endpoint is responding"
    else
        log_error "Root endpoint is not responding"
        return 1
    fi
    
    # Test capabilities endpoint
    log_info "Testing capabilities endpoint..."
    if kubectl exec -n "$NAMESPACE" "$pod_name" -- curl -f -s --max-time 10 "http://localhost:8080/api/v1/multi-agent/capabilities" > /dev/null 2>&1; then
        log_success "Capabilities endpoint is responding"
    else
        log_warning "Capabilities endpoint is not responding (may be expected)"
    fi
    
    # Test metrics endpoint
    log_info "Testing metrics endpoint..."
    if kubectl exec -n "$NAMESPACE" "$pod_name" -- curl -f -s --max-time 10 "http://localhost:8080/api/v1/metrics" > /dev/null 2>&1; then
        log_success "Metrics endpoint is responding"
    else
        log_error "Metrics endpoint is not responding"
        return 1
    fi
    
    log_success "API functionality validation passed"
}

# Validate monitoring integration
validate_monitoring() {
    log_info "Validating monitoring integration..."
    
    # Check if Prometheus is scraping metrics
    local active_version
    active_version=$(get_active_version)
    
    # Check pod annotations for Prometheus
    local pod_name
    pod_name=$(kubectl get pods -n "$NAMESPACE" -l "app=$APP_NAME,version=$active_version" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    
    if [[ -n "$pod_name" ]]; then
        local scrape_annotation
        scrape_annotation=$(kubectl get pod "$pod_name" -n "$NAMESPACE" -o jsonpath='{.metadata.annotations.prometheus\.io/scrape}' 2>/dev/null || echo "")
        
        if [[ "$scrape_annotation" == "true" ]]; then
            log_success "Prometheus scraping is enabled"
        else
            log_warning "Prometheus scraping annotation not found"
        fi
    fi
    
    # Check ServiceMonitor if it exists
    if kubectl get servicemonitor "$APP_NAME" -n "$NAMESPACE" &> /dev/null; then
        log_success "ServiceMonitor exists for Prometheus integration"
    else
        log_warning "ServiceMonitor not found (may be expected)"
    fi
    
    log_success "Monitoring integration validation passed"
}

# Validate network connectivity
validate_network_connectivity() {
    log_info "Validating network connectivity..."
    
    local active_version
    active_version=$(get_active_version)
    
    # Get a pod for network testing
    local pod_name
    pod_name=$(kubectl get pods -n "$NAMESPACE" -l "app=$APP_NAME,version=$active_version" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    
    if [[ -z "$pod_name" ]]; then
        log_error "No pods found for network testing"
        return 1
    fi
    
    # Test DNS resolution
    log_info "Testing DNS resolution..."
    if kubectl exec -n "$NAMESPACE" "$pod_name" -- nslookup kubernetes.default.svc.cluster.local > /dev/null 2>&1; then
        log_success "DNS resolution is working"
    else
        log_warning "DNS resolution test failed (may be expected in some environments)"
    fi
    
    # Test service connectivity
    log_info "Testing service connectivity..."
    if kubectl exec -n "$NAMESPACE" "$pod_name" -- curl -f -s --max-time 5 "http://$SERVICE_NAME.$NAMESPACE.svc.cluster.local/api/v1/health/health" > /dev/null 2>&1; then
        log_success "Service connectivity is working"
    else
        log_error "Service connectivity test failed"
        return 1
    fi
    
    log_success "Network connectivity validation passed"
}

# Validate resource utilization
validate_resource_utilization() {
    log_info "Validating resource utilization..."
    
    local active_version
    active_version=$(get_active_version)
    
    # Check resource usage
    local pods
    mapfile -t pods < <(kubectl get pods -n "$NAMESPACE" -l "app=$APP_NAME,version=$active_version" -o jsonpath='{.items[*].metadata.name}')
    
    for pod in "${pods[@]}"; do
        if [[ -n "$pod" ]]; then
            # Get resource usage (if metrics-server is available)
            if kubectl top pod "$pod" -n "$NAMESPACE" &> /dev/null; then
                local cpu_usage memory_usage
                cpu_usage=$(kubectl top pod "$pod" -n "$NAMESPACE" --no-headers | awk '{print $2}')
                memory_usage=$(kubectl top pod "$pod" -n "$NAMESPACE" --no-headers | awk '{print $3}')
                log_info "Pod $pod resource usage: CPU=$cpu_usage, Memory=$memory_usage"
            else
                log_warning "Resource metrics not available for pod $pod"
            fi
        fi
    done
    
    log_success "Resource utilization validation completed"
}

# Run basic load test
run_basic_load_test() {
    log_info "Running basic load test for $LOAD_TEST_DURATION seconds..."
    
    local active_version
    active_version=$(get_active_version)
    
    # Get a pod for load testing
    local pod_name
    pod_name=$(kubectl get pods -n "$NAMESPACE" -l "app=$APP_NAME,version=$active_version" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    
    if [[ -z "$pod_name" ]]; then
        log_error "No pods found for load testing"
        return 1
    fi
    
    # Simple load test using curl in a loop
    local success_count=0
    local failure_count=0
    local start_time
    start_time=$(date +%s)
    local end_time=$((start_time + LOAD_TEST_DURATION))
    
    while [[ $(date +%s) -lt $end_time ]]; do
        if kubectl exec -n "$NAMESPACE" "$pod_name" -- curl -f -s --max-time 5 "http://localhost:8080/api/v1/health/health" > /dev/null 2>&1; then
            ((success_count++))
        else
            ((failure_count++))
        fi
        sleep 1
    done
    
    local total_requests=$((success_count + failure_count))
    local success_rate=0
    
    if [[ $total_requests -gt 0 ]]; then
        success_rate=$((success_count * 100 / total_requests))
    fi
    
    log_info "Load test results: $success_count successful, $failure_count failed (${success_rate}% success rate)"
    
    if [[ $success_rate -ge 95 ]]; then
        log_success "Load test passed with ${success_rate}% success rate"
    else
        log_error "Load test failed with ${success_rate}% success rate"
        return 1
    fi
}

# Generate validation report
generate_validation_report() {
    local active_version
    active_version=$(get_active_version)
    
    echo ""
    echo "================================================================================"
    echo "📊 Production Deployment Validation Report"
    echo "================================================================================"
    echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Namespace: $NAMESPACE"
    echo "Active Version: $active_version"
    echo "Service: $SERVICE_NAME"
    echo "Application: $APP_NAME"
    echo ""
    echo "Validation Results:"
    echo "✅ Kubernetes Resources: PASSED"
    echo "✅ Health Endpoints: PASSED"
    echo "✅ API Functionality: PASSED"
    echo "✅ Monitoring Integration: PASSED"
    echo "✅ Network Connectivity: PASSED"
    echo "✅ Resource Utilization: CHECKED"
    echo "✅ Basic Load Test: PASSED"
    echo ""
    echo "🎉 Production deployment validation SUCCESSFUL!"
    echo "================================================================================"
}

# Main validation function
main() {
    print_header
    
    log_info "Starting production deployment validation..."
    
    # Step 1: Validate Kubernetes resources
    if ! validate_kubernetes_resources; then
        log_error "Kubernetes resources validation failed"
        exit 1
    fi
    
    # Step 2: Validate health endpoints
    if ! validate_health_endpoints; then
        log_error "Health endpoints validation failed"
        exit 1
    fi
    
    # Step 3: Validate API functionality
    if ! validate_api_functionality; then
        log_error "API functionality validation failed"
        exit 1
    fi
    
    # Step 4: Validate monitoring integration
    validate_monitoring  # Non-critical, warnings only
    
    # Step 5: Validate network connectivity
    if ! validate_network_connectivity; then
        log_error "Network connectivity validation failed"
        exit 1
    fi
    
    # Step 6: Validate resource utilization
    validate_resource_utilization  # Informational only
    
    # Step 7: Run basic load test
    if ! run_basic_load_test; then
        log_error "Basic load test failed"
        exit 1
    fi
    
    # Generate validation report
    generate_validation_report
    
    log_success "🎉 Production deployment validation completed successfully!"
}

# Run main function
main "$@"
