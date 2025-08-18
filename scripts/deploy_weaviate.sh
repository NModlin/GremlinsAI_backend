#!/bin/bash

# GremlinsAI Weaviate Production Deployment Script
# Phase 2, Task 2.1: Weaviate Deployment & Schema Activation
#
# This script deploys a production-ready Weaviate cluster using the existing
# Kubernetes configurations and prepares it for the SQLite to Weaviate migration.

set -euo pipefail

# Configuration
NAMESPACE="gremlinsai"
DEPLOYMENT_NAME="weaviate"
REPLICAS=3
STORAGE_SIZE="500Gi"
MONITORING_ENABLED=true
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
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

log_step() {
    echo -e "${PURPLE}[STEP]${NC} $1"
}

# Print banner
print_banner() {
    echo -e "${BLUE}"
    echo "=================================================================="
    echo "  GremlinsAI Weaviate Production Deployment"
    echo "  Phase 2, Task 2.1: Weaviate Deployment & Schema Activation"
    echo "=================================================================="
    echo -e "${NC}"
}

# Check prerequisites
check_prerequisites() {
    log_step "Checking deployment prerequisites..."
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        log_info "Please install kubectl: https://kubernetes.io/docs/tasks/tools/"
        exit 1
    fi
    
    # Check kubectl version
    KUBECTL_VERSION=$(kubectl version --client --short 2>/dev/null | cut -d' ' -f3 | sed 's/v//')
    log_info "kubectl version: $KUBECTL_VERSION"
    
    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        log_info "Please ensure kubectl is configured and cluster is accessible"
        exit 1
    fi
    
    # Get cluster information
    CURRENT_CONTEXT=$(kubectl config current-context)
    CLUSTER_VERSION=$(kubectl version --short 2>/dev/null | grep "Server Version" | cut -d' ' -f3 | sed 's/v//' || echo "unknown")
    
    log_info "Current Kubernetes context: $CURRENT_CONTEXT"
    log_info "Cluster version: $CLUSTER_VERSION"
    
    # Check if deployment files exist
    if [[ ! -f "$PROJECT_ROOT/kubernetes/weaviate-deployment.yaml" ]]; then
        log_error "Weaviate deployment file not found: $PROJECT_ROOT/kubernetes/weaviate-deployment.yaml"
        exit 1
    fi
    
    if [[ ! -f "$PROJECT_ROOT/kubernetes/weaviate-monitoring.yaml" ]]; then
        log_warning "Monitoring configuration not found: $PROJECT_ROOT/kubernetes/weaviate-monitoring.yaml"
        MONITORING_ENABLED=false
    fi
    
    # Warn if not production context
    if [[ ! "$CURRENT_CONTEXT" =~ prod|production ]]; then
        log_warning "Current context doesn't appear to be production"
        log_warning "Deploying to: $CURRENT_CONTEXT"
        echo -n "Continue with deployment? (y/N): "
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            log_info "Deployment cancelled by user"
            exit 0
        fi
    fi
    
    log_success "Prerequisites check completed"
}

# Generate secure API keys
generate_api_keys() {
    log_step "Generating secure API keys for Weaviate authentication..."
    
    # Check if openssl is available
    if ! command -v openssl &> /dev/null; then
        log_error "openssl is required for API key generation"
        exit 1
    fi
    
    # Generate random API keys
    ADMIN_KEY=$(openssl rand -hex 32)
    APP_KEY=$(openssl rand -hex 32)
    DEV_KEY=$(openssl rand -hex 32)
    
    # Create base64 encoded values for Kubernetes secret
    API_KEYS_B64=$(echo -n "$ADMIN_KEY,$APP_KEY,$DEV_KEY" | base64 -w 0 2>/dev/null || echo -n "$ADMIN_KEY,$APP_KEY,$DEV_KEY" | base64)
    API_USERS_B64=$(echo -n "admin:$ADMIN_KEY,app:$APP_KEY,dev:$DEV_KEY" | base64 -w 0 2>/dev/null || echo -n "admin:$ADMIN_KEY,app:$APP_KEY,dev:$DEV_KEY" | base64)
    
    # Create temporary deployment file with updated keys
    TEMP_DEPLOYMENT_FILE="/tmp/weaviate-deployment-$(date +%s).yaml"
    cp "$PROJECT_ROOT/kubernetes/weaviate-deployment.yaml" "$TEMP_DEPLOYMENT_FILE"
    
    # Update the secret in the deployment file
    sed -i.bak "s/api-keys: .*/api-keys: $API_KEYS_B64/" "$TEMP_DEPLOYMENT_FILE"
    sed -i.bak "s/api-users: .*/api-users: $API_USERS_B64/" "$TEMP_DEPLOYMENT_FILE"
    
    # Save keys to secure file
    KEYS_FILE="$PROJECT_ROOT/weaviate-api-keys-$(date +%Y%m%d-%H%M%S).txt"
    cat > "$KEYS_FILE" << EOF
# GremlinsAI Weaviate API Keys - Generated $(date)
# Store these keys securely and delete this file after use
# 
# IMPORTANT: These keys provide full access to your Weaviate cluster

ADMIN_KEY=$ADMIN_KEY
APP_KEY=$APP_KEY
DEV_KEY=$DEV_KEY

# Connection Examples:
# Admin access:
#   curl -H "Authorization: Bearer $ADMIN_KEY" http://weaviate-lb:8080/v1/meta
# 
# Application access:
#   curl -H "Authorization: Bearer $APP_KEY" http://weaviate-lb:8080/v1/objects
#
# Development access:
#   curl -H "Authorization: Bearer $DEV_KEY" http://weaviate-lb:8080/v1/schema

# Environment Variables for GremlinsAI:
export WEAVIATE_API_KEY="$APP_KEY"
export WEAVIATE_URL="http://weaviate-lb:8080"

# Python Client Configuration:
# import weaviate
# client = weaviate.Client(
#     url="http://weaviate-lb:8080",
#     auth_client_secret=weaviate.AuthApiKey(api_key="$APP_KEY")
# )
EOF
    
    chmod 600 "$KEYS_FILE"
    log_success "API keys generated and saved to: $KEYS_FILE"
    log_warning "Please store these keys securely and delete the file after use"
    
    # Export for use in this script
    export WEAVIATE_API_KEY="$APP_KEY"
    export TEMP_DEPLOYMENT_FILE
}

# Create namespace and deploy Weaviate
deploy_weaviate() {
    log_step "Deploying Weaviate cluster to Kubernetes..."
    
    # Create namespace if it doesn't exist
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_info "Creating namespace: $NAMESPACE"
        kubectl create namespace "$NAMESPACE"
        kubectl label namespace "$NAMESPACE" tier=production
    else
        log_info "Namespace $NAMESPACE already exists"
    fi
    
    # Apply the main deployment with updated API keys
    log_info "Applying Weaviate deployment configuration..."
    kubectl apply -f "$TEMP_DEPLOYMENT_FILE"
    
    # Apply monitoring configuration if enabled
    if [ "$MONITORING_ENABLED" = true ]; then
        log_info "Applying monitoring configuration..."
        kubectl apply -f "$PROJECT_ROOT/kubernetes/weaviate-monitoring.yaml"
    fi
    
    log_success "Weaviate deployment configuration applied"
}

# Wait for deployment to be ready
wait_for_deployment() {
    log_step "Waiting for Weaviate cluster to be ready..."
    
    # Wait for StatefulSet to be ready
    log_info "Waiting for StatefulSet rollout (timeout: 10 minutes)..."
    if ! kubectl rollout status statefulset/$DEPLOYMENT_NAME -n "$NAMESPACE" --timeout=600s; then
        log_error "StatefulSet rollout failed or timed out"
        return 1
    fi
    
    # Wait for all pods to be ready
    log_info "Waiting for all pods to be ready (timeout: 5 minutes)..."
    if ! kubectl wait --for=condition=ready pod -l app=weaviate -n "$NAMESPACE" --timeout=300s; then
        log_error "Pods failed to become ready"
        return 1
    fi
    
    # Check cluster health
    log_info "Verifying cluster health..."
    READY_PODS=$(kubectl get pods -l app=weaviate -n "$NAMESPACE" --no-headers | grep -c "Running" || echo "0")
    
    if [ "$READY_PODS" -eq "$REPLICAS" ]; then
        log_success "All $REPLICAS Weaviate pods are running and ready"
    else
        log_error "Only $READY_PODS out of $REPLICAS pods are ready"
        kubectl get pods -l app=weaviate -n "$NAMESPACE"
        return 1
    fi
}

# Verify deployment and get connection information
verify_deployment() {
    log_step "Verifying Weaviate deployment and gathering connection information..."
    
    # Get service endpoints
    CLUSTER_IP=$(kubectl get svc weaviate-headless -n "$NAMESPACE" -o jsonpath='{.spec.clusterIP}' 2>/dev/null || echo "N/A")
    EXTERNAL_IP=$(kubectl get svc weaviate-lb -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "Pending")
    
    log_info "Connection Information:"
    log_info "  Internal Cluster IP: $CLUSTER_IP:8080"
    log_info "  External Load Balancer IP: $EXTERNAL_IP:8080 (may take a few minutes to provision)"
    log_info "  gRPC Port: 50051"
    
    # Test internal connectivity
    log_info "Testing internal connectivity..."
    if kubectl run connectivity-test --rm -i --tty --image=curlimages/curl --restart=Never -n "$NAMESPACE" -- \
        curl -s --max-time 10 "http://weaviate-headless:8080/v1/.well-known/ready" | grep -q "true"; then
        log_success "Internal connectivity test passed"
    else
        log_warning "Internal connectivity test failed - cluster may still be initializing"
    fi
    
    # Display cluster resources
    log_info "Cluster Resources:"
    kubectl get pods,svc,pvc -l app=weaviate -n "$NAMESPACE" -o wide
    
    # Display storage information
    log_info "Storage Information:"
    kubectl get pvc -l app=weaviate -n "$NAMESPACE"
    
    log_success "Weaviate cluster verification completed"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up temporary files..."
    if [[ -n "${TEMP_DEPLOYMENT_FILE:-}" && -f "$TEMP_DEPLOYMENT_FILE" ]]; then
        rm -f "$TEMP_DEPLOYMENT_FILE" "$TEMP_DEPLOYMENT_FILE.bak"
    fi
    rm -f /tmp/connectivity-test.yaml
}

# Main deployment function
main() {
    print_banner
    
    log_info "Starting Weaviate production deployment..."
    log_info "Target Configuration:"
    log_info "  - Namespace: $NAMESPACE"
    log_info "  - Replicas: $REPLICAS"
    log_info "  - Storage per node: $STORAGE_SIZE"
    log_info "  - Monitoring: $MONITORING_ENABLED"
    log_info "  - Project root: $PROJECT_ROOT"
    
    # Set trap for cleanup
    trap cleanup EXIT
    
    # Execute deployment steps
    check_prerequisites
    generate_api_keys
    deploy_weaviate
    wait_for_deployment
    verify_deployment
    
    log_success "Weaviate production deployment completed successfully!"
    echo
    log_info "Next Steps:"
    log_info "  1. Run the schema activation script:"
    log_info "     python scripts/activate_weaviate_schema.py"
    log_info "  2. Run the deployment validation script:"
    log_info "     python scripts/validate_weaviate_deployment.py"
    log_info "  3. Configure your application to use the Weaviate endpoints"
    log_info "  4. Securely store the API keys and delete the keys file"
    log_info "  5. Set up monitoring dashboards if monitoring is enabled"
    echo
    log_warning "IMPORTANT: Secure your API keys file and delete it after storing the keys safely!"
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "status")
        kubectl get pods,svc,pvc -l app=weaviate -n "$NAMESPACE" -o wide
        ;;
    "logs")
        kubectl logs -l app=weaviate -n "$NAMESPACE" --tail=100 -f
        ;;
    "cleanup")
        log_warning "This will delete the entire Weaviate deployment. Are you sure? (y/N)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            kubectl delete -f "$PROJECT_ROOT/kubernetes/weaviate-deployment.yaml"
            log_success "Weaviate deployment cleaned up"
        fi
        ;;
    *)
        echo "Usage: $0 [deploy|status|logs|cleanup]"
        echo "  deploy  - Deploy Weaviate cluster (default)"
        echo "  status  - Show deployment status"
        echo "  logs    - Show cluster logs"
        echo "  cleanup - Remove deployment"
        exit 1
        ;;
esac
