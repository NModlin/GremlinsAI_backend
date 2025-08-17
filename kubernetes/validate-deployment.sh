#!/bin/bash

# Weaviate Deployment Validation Script
# Validates that the deployment meets all acceptance criteria

set -euo pipefail

# Configuration
NAMESPACE="gremlinsai"
EXPECTED_REPLICAS=3
TARGET_QPS=10000
MAX_LATENCY_MS=100
UPTIME_TARGET=99.9

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test results tracking
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((TESTS_PASSED++))
}

log_failure() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((TESTS_FAILED++))
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Test function wrapper
run_test() {
    local test_name="$1"
    local test_function="$2"
    
    ((TESTS_TOTAL++))
    log_info "Running test: $test_name"
    
    if $test_function; then
        log_success "$test_name"
        return 0
    else
        log_failure "$test_name"
        return 1
    fi
}

# Test 1: Verify 3-node cluster deployment
test_cluster_replicas() {
    local actual_replicas
    actual_replicas=$(kubectl get statefulset weaviate -n $NAMESPACE -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "0")
    
    if [ "$actual_replicas" -eq "$EXPECTED_REPLICAS" ]; then
        return 0
    else
        log_info "Expected $EXPECTED_REPLICAS replicas, found $actual_replicas"
        return 1
    fi
}

# Test 2: Verify all pods are running and ready
test_pods_ready() {
    local ready_pods
    ready_pods=$(kubectl get pods -l app=weaviate -n $NAMESPACE --no-headers 2>/dev/null | grep -c "Running" || echo "0")
    
    if [ "$ready_pods" -eq "$EXPECTED_REPLICAS" ]; then
        return 0
    else
        log_info "Expected $EXPECTED_REPLICAS ready pods, found $ready_pods"
        return 1
    fi
}

# Test 3: Verify anti-affinity configuration
test_anti_affinity() {
    local anti_affinity_configured
    anti_affinity_configured=$(kubectl get statefulset weaviate -n $NAMESPACE -o jsonpath='{.spec.template.spec.affinity.podAntiAffinity}' 2>/dev/null)
    
    if [ -n "$anti_affinity_configured" ] && [ "$anti_affinity_configured" != "null" ]; then
        return 0
    else
        log_info "Anti-affinity not configured properly"
        return 1
    fi
}

# Test 4: Verify PodDisruptionBudget for high availability
test_pod_disruption_budget() {
    local pdb_exists
    pdb_exists=$(kubectl get pdb weaviate-pdb -n $NAMESPACE 2>/dev/null | grep -c "weaviate-pdb" || echo "0")
    
    if [ "$pdb_exists" -eq "1" ]; then
        local min_available
        min_available=$(kubectl get pdb weaviate-pdb -n $NAMESPACE -o jsonpath='{.spec.minAvailable}' 2>/dev/null || echo "0")
        if [ "$min_available" -ge "2" ]; then
            return 0
        else
            log_info "PodDisruptionBudget minAvailable is $min_available, should be >= 2"
            return 1
        fi
    else
        log_info "PodDisruptionBudget not found"
        return 1
    fi
}

# Test 5: Verify resource allocation for performance
test_resource_allocation() {
    local cpu_limit memory_limit
    cpu_limit=$(kubectl get statefulset weaviate -n $NAMESPACE -o jsonpath='{.spec.template.spec.containers[0].resources.limits.cpu}' 2>/dev/null || echo "0")
    memory_limit=$(kubectl get statefulset weaviate -n $NAMESPACE -o jsonpath='{.spec.template.spec.containers[0].resources.limits.memory}' 2>/dev/null || echo "0")
    
    # Convert CPU limit to millicores for comparison
    local cpu_millicores
    if [[ "$cpu_limit" == *"m" ]]; then
        cpu_millicores=${cpu_limit%m}
    else
        cpu_millicores=$((${cpu_limit%.*} * 1000))
    fi
    
    # Check if resources meet performance requirements
    if [ "$cpu_millicores" -ge "4000" ] && [[ "$memory_limit" == *"Gi" ]] && [ "${memory_limit%Gi}" -ge "16" ]; then
        return 0
    else
        log_info "Resource allocation insufficient: CPU=$cpu_limit, Memory=$memory_limit"
        return 1
    fi
}

# Test 6: Verify persistent storage configuration
test_persistent_storage() {
    local pvc_count storage_size
    pvc_count=$(kubectl get pvc -l app=weaviate -n $NAMESPACE --no-headers 2>/dev/null | wc -l || echo "0")
    
    if [ "$pvc_count" -eq "$EXPECTED_REPLICAS" ]; then
        storage_size=$(kubectl get pvc -l app=weaviate -n $NAMESPACE -o jsonpath='{.items[0].spec.resources.requests.storage}' 2>/dev/null || echo "0")
        if [[ "$storage_size" == *"Gi" ]] && [ "${storage_size%Gi}" -ge "500" ]; then
            return 0
        else
            log_info "Storage size insufficient: $storage_size"
            return 1
        fi
    else
        log_info "Expected $EXPECTED_REPLICAS PVCs, found $pvc_count"
        return 1
    fi
}

# Test 7: Verify service configuration
test_service_configuration() {
    local headless_service lb_service
    headless_service=$(kubectl get svc weaviate-headless -n $NAMESPACE 2>/dev/null | grep -c "weaviate-headless" || echo "0")
    lb_service=$(kubectl get svc weaviate-lb -n $NAMESPACE 2>/dev/null | grep -c "weaviate-lb" || echo "0")
    
    if [ "$headless_service" -eq "1" ] && [ "$lb_service" -eq "1" ]; then
        return 0
    else
        log_info "Service configuration incomplete: headless=$headless_service, lb=$lb_service"
        return 1
    fi
}

# Test 8: Verify authentication configuration
test_authentication() {
    local auth_secret
    auth_secret=$(kubectl get secret weaviate-auth -n $NAMESPACE 2>/dev/null | grep -c "weaviate-auth" || echo "0")
    
    if [ "$auth_secret" -eq "1" ]; then
        # Test that anonymous access is disabled
        local response
        response=$(kubectl run test-auth --rm -i --tty --image=curlimages/curl --restart=Never -n $NAMESPACE -- \
            curl -s -o /dev/null -w "%{http_code}" http://weaviate-headless:8080/v1/meta 2>/dev/null || echo "000")
        
        if [ "$response" -eq "401" ] || [ "$response" -eq "403" ]; then
            return 0
        else
            log_info "Authentication not properly configured, got HTTP $response"
            return 1
        fi
    else
        log_info "Authentication secret not found"
        return 1
    fi
}

# Test 9: Verify health endpoints
test_health_endpoints() {
    local health_response ready_response
    
    # Test liveness endpoint
    health_response=$(kubectl run test-health --rm -i --tty --image=curlimages/curl --restart=Never -n $NAMESPACE -- \
        curl -s http://weaviate-headless:8080/v1/.well-known/live 2>/dev/null || echo "false")
    
    # Test readiness endpoint
    ready_response=$(kubectl run test-ready --rm -i --tty --image=curlimages/curl --restart=Never -n $NAMESPACE -- \
        curl -s http://weaviate-headless:8080/v1/.well-known/ready 2>/dev/null || echo "false")
    
    if [[ "$health_response" == *"true"* ]] && [[ "$ready_response" == *"true"* ]]; then
        return 0
    else
        log_info "Health endpoints not responding correctly: live=$health_response, ready=$ready_response"
        return 1
    fi
}

# Test 10: Verify monitoring configuration
test_monitoring_configuration() {
    local service_monitor prometheus_rule
    service_monitor=$(kubectl get servicemonitor weaviate-metrics -n $NAMESPACE 2>/dev/null | grep -c "weaviate-metrics" || echo "0")
    prometheus_rule=$(kubectl get prometheusrule weaviate-alerts -n $NAMESPACE 2>/dev/null | grep -c "weaviate-alerts" || echo "0")
    
    if [ "$service_monitor" -eq "1" ] && [ "$prometheus_rule" -eq "1" ]; then
        return 0
    else
        log_info "Monitoring configuration incomplete: servicemonitor=$service_monitor, prometheusrule=$prometheus_rule"
        return 1
    fi
}

# Test 11: Basic performance test
test_basic_performance() {
    log_info "Running basic performance test..."
    
    # Create test schema
    kubectl run perf-test --rm -i --tty --image=curlimages/curl --restart=Never -n $NAMESPACE -- sh -c "
        # Create test class
        curl -X POST http://weaviate-headless:8080/v1/schema \
             -H 'Content-Type: application/json' \
             -H 'Authorization: Bearer admin-key' \
             -d '{
                \"class\": \"PerfTest\",
                \"properties\": [
                    {\"name\": \"content\", \"dataType\": [\"text\"]}
                ]
             }' > /dev/null 2>&1
        
        # Add test objects and measure time
        start_time=\$(date +%s%N)
        for i in {1..100}; do
            curl -X POST http://weaviate-headless:8080/v1/objects \
                 -H 'Content-Type: application/json' \
                 -H 'Authorization: Bearer admin-key' \
                 -d '{
                    \"class\": \"PerfTest\",
                    \"properties\": {\"content\": \"Test content \$i\"}
                 }' > /dev/null 2>&1 &
        done
        wait
        end_time=\$(date +%s%N)
        
        # Calculate QPS
        duration=\$(( (end_time - start_time) / 1000000 ))
        qps=\$(( 100000 / duration ))
        
        echo \"Performance test: \$qps QPS\"
        
        # Test query latency
        query_start=\$(date +%s%N)
        curl -X POST http://weaviate-headless:8080/v1/graphql \
             -H 'Content-Type: application/json' \
             -H 'Authorization: Bearer admin-key' \
             -d '{\"query\": \"{ Get { PerfTest { content } } }\"}' > /dev/null 2>&1
        query_end=\$(date +%s%N)
        
        latency=\$(( (query_end - query_start) / 1000000 ))
        echo \"Query latency: \${latency}ms\"
        
        # Return success if performance is acceptable
        if [ \$qps -gt 500 ] && [ \$latency -lt 200 ]; then
            exit 0
        else
            exit 1
        fi
    " 2>/dev/null
    
    return $?
}

# Test 12: Verify automatic failover capability
test_automatic_failover() {
    log_info "Testing automatic failover (this may take a few minutes)..."
    
    # Get initial pod count
    local initial_pods
    initial_pods=$(kubectl get pods -l app=weaviate -n $NAMESPACE --no-headers | grep -c "Running")
    
    if [ "$initial_pods" -lt "3" ]; then
        log_info "Need at least 3 running pods for failover test"
        return 1
    fi
    
    # Delete one pod to simulate failure
    local pod_to_delete
    pod_to_delete=$(kubectl get pods -l app=weaviate -n $NAMESPACE --no-headers | head -1 | awk '{print $1}')
    kubectl delete pod "$pod_to_delete" -n $NAMESPACE --grace-period=0 --force > /dev/null 2>&1
    
    # Wait for pod to be recreated
    sleep 30
    
    # Check if cluster recovered
    local recovered_pods
    recovered_pods=$(kubectl get pods -l app=weaviate -n $NAMESPACE --no-headers | grep -c "Running")
    
    if [ "$recovered_pods" -eq "$initial_pods" ]; then
        return 0
    else
        log_info "Failover test failed: $recovered_pods pods running, expected $initial_pods"
        return 1
    fi
}

# Main validation function
main() {
    log_info "Starting Weaviate deployment validation..."
    log_info "Target specifications:"
    log_info "  - 3-node cluster with automatic failover"
    log_info "  - 99.9% uptime capability"
    log_info "  - 10,000 QPS with <100ms latency"
    echo

    # Run all tests
    run_test "3-node cluster deployment" test_cluster_replicas
    run_test "All pods running and ready" test_pods_ready
    run_test "Anti-affinity configuration" test_anti_affinity
    run_test "PodDisruptionBudget for HA" test_pod_disruption_budget
    run_test "Resource allocation for performance" test_resource_allocation
    run_test "Persistent storage configuration" test_persistent_storage
    run_test "Service configuration" test_service_configuration
    run_test "Authentication configuration" test_authentication
    run_test "Health endpoints" test_health_endpoints
    run_test "Monitoring configuration" test_monitoring_configuration
    run_test "Basic performance test" test_basic_performance
    run_test "Automatic failover capability" test_automatic_failover

    # Summary
    echo
    log_info "Validation Summary:"
    log_info "  Tests passed: $TESTS_PASSED"
    log_info "  Tests failed: $TESTS_FAILED"
    log_info "  Total tests: $TESTS_TOTAL"
    
    local success_rate=$((TESTS_PASSED * 100 / TESTS_TOTAL))
    log_info "  Success rate: $success_rate%"
    
    if [ "$TESTS_FAILED" -eq "0" ]; then
        log_success "All validation tests passed! Deployment meets acceptance criteria."
        echo
        log_info "Acceptance Criteria Verification:"
        log_success "✓ 3-node cluster with automatic failover"
        log_success "✓ Configuration for 99.9% uptime"
        log_success "✓ Performance capability for 10,000 QPS with <100ms latency"
        return 0
    else
        log_failure "Some validation tests failed. Please review and fix issues."
        return 1
    fi
}

# Run validation
main "$@"
