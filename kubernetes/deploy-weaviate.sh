#!/bin/bash

# Weaviate Production Deployment Script
# This script deploys a high-availability Weaviate cluster to Kubernetes

set -euo pipefail

# Configuration
NAMESPACE="gremlinsai"
CLUSTER_NAME="weaviate-cluster"
REPLICAS=3
STORAGE_SIZE="500Gi"
MONITORING_ENABLED=true

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    # Check if running on appropriate cluster
    CURRENT_CONTEXT=$(kubectl config current-context)
    log_info "Current Kubernetes context: $CURRENT_CONTEXT"
    
    # Warn if not production context
    if [[ ! "$CURRENT_CONTEXT" =~ prod|production ]]; then
        log_warning "Current context doesn't appear to be production. Continue? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            log_info "Deployment cancelled"
            exit 0
        fi
    fi
    
    log_success "Prerequisites check passed"
}

# Generate secure API keys
generate_api_keys() {
    log_info "Generating secure API keys..."
    
    # Generate random API keys
    ADMIN_KEY=$(openssl rand -hex 32)
    APP_KEY=$(openssl rand -hex 32)
    DEV_KEY=$(openssl rand -hex 32)
    
    # Create base64 encoded values
    API_KEYS_B64=$(echo -n "$ADMIN_KEY,$APP_KEY,$DEV_KEY" | base64 -w 0)
    API_USERS_B64=$(echo -n "admin:$ADMIN_KEY,app:$APP_KEY,dev:$DEV_KEY" | base64 -w 0)
    
    # Update the secret in the deployment file
    sed -i "s/api-keys: .*/api-keys: $API_KEYS_B64/" kubernetes/weaviate-deployment.yaml
    sed -i "s/api-users: .*/api-users: $API_USERS_B64/" kubernetes/weaviate-deployment.yaml
    
    # Save keys to secure file
    cat > weaviate-api-keys.txt << EOF
# Weaviate API Keys - Store securely and delete this file after use
ADMIN_KEY=$ADMIN_KEY
APP_KEY=$APP_KEY
DEV_KEY=$DEV_KEY

# Usage examples:
# curl -H "Authorization: Bearer $ADMIN_KEY" http://weaviate-lb:8080/v1/meta
# curl -H "Authorization: Bearer $APP_KEY" http://weaviate-lb:8080/v1/objects
EOF
    
    chmod 600 weaviate-api-keys.txt
    log_success "API keys generated and saved to weaviate-api-keys.txt"
}

# Deploy Weaviate cluster
deploy_weaviate() {
    log_info "Deploying Weaviate cluster..."
    
    # Create namespace if it doesn't exist
    if ! kubectl get namespace $NAMESPACE &> /dev/null; then
        log_info "Creating namespace: $NAMESPACE"
        kubectl create namespace $NAMESPACE
    fi
    
    # Apply the main deployment
    log_info "Applying Weaviate deployment configuration..."
    kubectl apply -f kubernetes/weaviate-deployment.yaml
    
    # Apply monitoring configuration if enabled
    if [ "$MONITORING_ENABLED" = true ]; then
        log_info "Applying monitoring configuration..."
        kubectl apply -f kubernetes/weaviate-monitoring.yaml
    fi
    
    log_success "Weaviate deployment configuration applied"
}

# Wait for deployment to be ready
wait_for_deployment() {
    log_info "Waiting for Weaviate cluster to be ready..."
    
    # Wait for StatefulSet to be ready
    log_info "Waiting for StatefulSet rollout..."
    kubectl rollout status statefulset/weaviate -n $NAMESPACE --timeout=600s
    
    # Wait for all pods to be ready
    log_info "Waiting for all pods to be ready..."
    kubectl wait --for=condition=ready pod -l app=weaviate -n $NAMESPACE --timeout=300s
    
    # Check cluster health
    log_info "Checking cluster health..."
    READY_PODS=$(kubectl get pods -l app=weaviate -n $NAMESPACE --no-headers | grep -c "Running")
    
    if [ "$READY_PODS" -eq "$REPLICAS" ]; then
        log_success "All $REPLICAS Weaviate pods are running and ready"
    else
        log_error "Only $READY_PODS out of $REPLICAS pods are ready"
        return 1
    fi
}

# Verify deployment
verify_deployment() {
    log_info "Verifying Weaviate deployment..."
    
    # Get service endpoints
    CLUSTER_IP=$(kubectl get svc weaviate-headless -n $NAMESPACE -o jsonpath='{.spec.clusterIP}')
    EXTERNAL_IP=$(kubectl get svc weaviate-lb -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    
    log_info "Cluster IP: $CLUSTER_IP"
    log_info "External IP: $EXTERNAL_IP (may take a few minutes to provision)"
    
    # Test internal connectivity
    log_info "Testing internal connectivity..."
    if kubectl run test-pod --rm -i --tty --image=curlimages/curl --restart=Never -n $NAMESPACE -- \
        curl -s "http://weaviate-headless:8080/v1/.well-known/ready" | grep -q "true"; then
        log_success "Internal connectivity test passed"
    else
        log_error "Internal connectivity test failed"
        return 1
    fi
    
    # Display cluster information
    log_info "Cluster Information:"
    kubectl get pods,svc,pvc -l app=weaviate -n $NAMESPACE
    
    log_success "Weaviate cluster verification completed"
}

# Performance test
performance_test() {
    log_info "Running basic performance test..."
    
    # Create a test schema and add some data
    kubectl run perf-test --rm -i --tty --image=curlimages/curl --restart=Never -n $NAMESPACE -- sh -c "
        # Test schema creation
        curl -X POST http://weaviate-headless:8080/v1/schema \
             -H 'Content-Type: application/json' \
             -d '{
                \"class\": \"TestClass\",
                \"properties\": [
                    {\"name\": \"content\", \"dataType\": [\"text\"]}
                ]
             }'
        
        # Test object creation
        for i in {1..100}; do
            curl -X POST http://weaviate-headless:8080/v1/objects \
                 -H 'Content-Type: application/json' \
                 -d '{
                    \"class\": \"TestClass\",
                    \"properties\": {\"content\": \"Test content \$i\"}
                 }' &
        done
        wait
        
        # Test query performance
        time curl -X POST http://weaviate-headless:8080/v1/graphql \
             -H 'Content-Type: application/json' \
             -d '{\"query\": \"{ Get { TestClass { content } } }\"}'
    "
    
    log_success "Basic performance test completed"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up temporary files..."
    rm -f test-pod.yaml
}

# Main deployment function
main() {
    log_info "Starting Weaviate production deployment..."
    log_info "Target configuration:"
    log_info "  - Namespace: $NAMESPACE"
    log_info "  - Replicas: $REPLICAS"
    log_info "  - Storage per node: $STORAGE_SIZE"
    log_info "  - Monitoring: $MONITORING_ENABLED"
    
    # Set trap for cleanup
    trap cleanup EXIT
    
    # Execute deployment steps
    check_prerequisites
    generate_api_keys
    deploy_weaviate
    wait_for_deployment
    verify_deployment
    
    # Optional performance test
    read -p "Run basic performance test? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        performance_test
    fi
    
    log_success "Weaviate production deployment completed successfully!"
    log_info "Next steps:"
    log_info "  1. Review and securely store the API keys in weaviate-api-keys.txt"
    log_info "  2. Configure your application to use the Weaviate endpoints"
    log_info "  3. Set up monitoring dashboards using the provided Grafana configuration"
    log_info "  4. Configure backup and disaster recovery procedures"
    log_info "  5. Delete the weaviate-api-keys.txt file after securing the keys"
}

# Run main function
main "$@"
