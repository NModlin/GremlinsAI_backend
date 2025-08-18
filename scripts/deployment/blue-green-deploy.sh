#!/bin/bash

# Blue-Green Deployment Script for GremlinsAI Backend - Task T3.7
# 
# This script implements a zero-downtime blue-green deployment strategy
# with automatic rollback capabilities for production deployment.
#
# Features:
# - Identifies current production environment (blue/green)
# - Deploys new version to inactive environment
# - Performs health checks and validation
# - Switches traffic with zero downtime
# - Automatic rollback on failure
# - Resource cleanup after successful deployment

set -euo pipefail

# Configuration
NAMESPACE="${NAMESPACE:-gremlinsai}"
APP_NAME="${APP_NAME:-gremlinsai-backend}"
SERVICE_NAME="${SERVICE_NAME:-gremlinsai-service}"
HEALTH_CHECK_URL="${HEALTH_CHECK_URL:-http://localhost:8080/api/v1/health/health}"
HEALTH_CHECK_TIMEOUT="${HEALTH_CHECK_TIMEOUT:-300}"
HEALTH_CHECK_INTERVAL="${HEALTH_CHECK_INTERVAL:-10}"
ROLLBACK_TIMEOUT="${ROLLBACK_TIMEOUT:-60}"

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

# Print header
print_header() {
    echo "================================================================================"
    echo "🚀 GremlinsAI Blue-Green Deployment - Task T3.7"
    echo "================================================================================"
    echo "Namespace: $NAMESPACE"
    echo "Application: $APP_NAME"
    echo "Service: $SERVICE_NAME"
    echo "Health Check URL: $HEALTH_CHECK_URL"
    echo "================================================================================"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if kubectl is available
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    # Check if we can connect to Kubernetes cluster
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    # Check if namespace exists
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_error "Namespace '$NAMESPACE' does not exist"
        exit 1
    fi
    
    # Check if curl is available for health checks
    if ! command -v curl &> /dev/null; then
        log_error "curl is not installed or not in PATH"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Identify current production environment
identify_current_environment() {
    log_info "Identifying current production environment..."
    
    # Get current service selector
    CURRENT_VERSION=$(kubectl get service "$SERVICE_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.selector.version}' 2>/dev/null || echo "")
    
    if [[ -z "$CURRENT_VERSION" ]]; then
        log_warning "No version selector found on service. Assuming initial deployment."
        CURRENT_VERSION="none"
        NEW_VERSION="blue"
    elif [[ "$CURRENT_VERSION" == "blue" ]]; then
        NEW_VERSION="green"
    elif [[ "$CURRENT_VERSION" == "green" ]]; then
        NEW_VERSION="blue"
    else
        log_error "Unknown current version: $CURRENT_VERSION"
        exit 1
    fi
    
    log_info "Current environment: $CURRENT_VERSION"
    log_info "New deployment target: $NEW_VERSION"
    
    export CURRENT_VERSION NEW_VERSION
}

# Wait for deployment to be ready
wait_for_deployment() {
    local deployment_name="$1"
    local timeout="$2"
    
    log_info "Waiting for deployment '$deployment_name' to be ready (timeout: ${timeout}s)..."
    
    if kubectl wait --for=condition=available --timeout="${timeout}s" deployment/"$deployment_name" -n "$NAMESPACE"; then
        log_success "Deployment '$deployment_name' is ready"
        return 0
    else
        log_error "Deployment '$deployment_name' failed to become ready within ${timeout}s"
        return 1
    fi
}

# Deploy new version
deploy_new_version() {
    log_info "Deploying new version to $NEW_VERSION environment..."
    
    # Create deployment manifest with new version
    local deployment_name="${APP_NAME}-${NEW_VERSION}"
    
    # Apply the deployment
    cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $deployment_name
  namespace: $NAMESPACE
  labels:
    app: $APP_NAME
    version: $NEW_VERSION
    deployment-strategy: blue-green
spec:
  replicas: 3
  selector:
    matchLabels:
      app: $APP_NAME
      version: $NEW_VERSION
  template:
    metadata:
      labels:
        app: $APP_NAME
        version: $NEW_VERSION
      annotations:
        deployment.kubernetes.io/revision: "$(date +%s)"
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: gremlinsai-backend
      containers:
      - name: gremlinsai-backend
        image: ${DOCKER_IMAGE:-gremlinsai/backend:latest}
        imagePullPolicy: Always
        ports:
        - containerPort: 8080
          name: http
          protocol: TCP
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: VERSION
          value: "$NEW_VERSION"
        - name: LOG_LEVEL
          value: "info"
        - name: DEPLOYMENT_TIMESTAMP
          value: "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /api/v1/health/live
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 30
          timeoutSeconds: 10
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /api/v1/health/ready
            port: 8080
          initialDelaySeconds: 15
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        startupProbe:
          httpGet:
            path: /api/v1/health/startup
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 30
EOF

    # Wait for deployment to be ready
    if ! wait_for_deployment "$deployment_name" 300; then
        log_error "Failed to deploy new version to $NEW_VERSION environment"
        cleanup_failed_deployment "$deployment_name"
        exit 1
    fi
    
    log_success "New version deployed successfully to $NEW_VERSION environment"
}

# Perform health check
perform_health_check() {
    local target_version="$1"
    local max_attempts=$((HEALTH_CHECK_TIMEOUT / HEALTH_CHECK_INTERVAL))
    local attempt=1
    
    log_info "Performing health check for $target_version environment..."
    log_info "Health check URL: $HEALTH_CHECK_URL"
    log_info "Max attempts: $max_attempts (${HEALTH_CHECK_TIMEOUT}s timeout)"
    
    # Get a pod from the target deployment for direct health check
    local pod_name
    pod_name=$(kubectl get pods -n "$NAMESPACE" -l "app=$APP_NAME,version=$target_version" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    
    if [[ -z "$pod_name" ]]; then
        log_error "No pods found for $target_version deployment"
        return 1
    fi
    
    # Perform health check via port-forward
    while [[ $attempt -le $max_attempts ]]; do
        log_info "Health check attempt $attempt/$max_attempts..."
        
        # Start port-forward in background
        kubectl port-forward -n "$NAMESPACE" pod/"$pod_name" 8080:8080 &
        local port_forward_pid=$!
        
        # Wait a moment for port-forward to establish
        sleep 2
        
        # Perform health check
        if curl -f -s --max-time 10 "$HEALTH_CHECK_URL" > /dev/null 2>&1; then
            # Kill port-forward
            kill $port_forward_pid 2>/dev/null || true
            log_success "Health check passed for $target_version environment"
            return 0
        fi
        
        # Kill port-forward
        kill $port_forward_pid 2>/dev/null || true
        
        if [[ $attempt -lt $max_attempts ]]; then
            log_warning "Health check failed, retrying in ${HEALTH_CHECK_INTERVAL}s..."
            sleep $HEALTH_CHECK_INTERVAL
        fi
        
        ((attempt++))
    done
    
    log_error "Health check failed for $target_version environment after $max_attempts attempts"
    return 1
}

# Switch traffic to new version
switch_traffic() {
    log_info "Switching traffic from $CURRENT_VERSION to $NEW_VERSION..."
    
    # Update service selector
    kubectl patch service "$SERVICE_NAME" -n "$NAMESPACE" -p '{"spec":{"selector":{"version":"'$NEW_VERSION'"}}}'
    
    # Wait a moment for the change to propagate
    sleep 5
    
    # Verify the service selector was updated
    local updated_version
    updated_version=$(kubectl get service "$SERVICE_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.selector.version}')
    
    if [[ "$updated_version" == "$NEW_VERSION" ]]; then
        log_success "Traffic successfully switched to $NEW_VERSION environment"
        return 0
    else
        log_error "Failed to switch traffic. Service selector is: $updated_version"
        return 1
    fi
}

# Rollback to previous version
rollback() {
    log_warning "Initiating rollback to $CURRENT_VERSION environment..."
    
    if [[ "$CURRENT_VERSION" == "none" ]]; then
        log_error "Cannot rollback - no previous version available"
        return 1
    fi
    
    # Switch service back to previous version
    kubectl patch service "$SERVICE_NAME" -n "$NAMESPACE" -p '{"spec":{"selector":{"version":"'$CURRENT_VERSION'"}}}'
    
    # Wait for rollback to complete
    sleep 5
    
    # Verify rollback
    local rolled_back_version
    rolled_back_version=$(kubectl get service "$SERVICE_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.selector.version}')
    
    if [[ "$rolled_back_version" == "$CURRENT_VERSION" ]]; then
        log_success "Successfully rolled back to $CURRENT_VERSION environment"
        return 0
    else
        log_error "Rollback failed. Current service selector: $rolled_back_version"
        return 1
    fi
}

# Cleanup failed deployment
cleanup_failed_deployment() {
    local deployment_name="$1"
    log_info "Cleaning up failed deployment: $deployment_name"
    
    kubectl delete deployment "$deployment_name" -n "$NAMESPACE" --ignore-not-found=true
    log_info "Cleanup completed"
}

# Cleanup old version
cleanup_old_version() {
    if [[ "$CURRENT_VERSION" == "none" ]]; then
        log_info "No old version to cleanup (initial deployment)"
        return 0
    fi
    
    log_info "Cleaning up old $CURRENT_VERSION environment..."
    
    local old_deployment="${APP_NAME}-${CURRENT_VERSION}"
    
    # Scale down old deployment
    kubectl scale deployment "$old_deployment" -n "$NAMESPACE" --replicas=0
    
    # Wait for pods to terminate
    kubectl wait --for=delete pods -l "app=$APP_NAME,version=$CURRENT_VERSION" -n "$NAMESPACE" --timeout=60s || true
    
    # Delete old deployment
    kubectl delete deployment "$old_deployment" -n "$NAMESPACE" --ignore-not-found=true
    
    log_success "Old $CURRENT_VERSION environment cleaned up"
}

# Verify production deployment
verify_production() {
    log_info "Verifying production deployment..."
    
    # Check service endpoints
    local endpoints
    endpoints=$(kubectl get endpoints "$SERVICE_NAME" -n "$NAMESPACE" -o jsonpath='{.subsets[*].addresses[*].ip}' | wc -w)
    
    if [[ $endpoints -gt 0 ]]; then
        log_success "Service has $endpoints healthy endpoints"
    else
        log_error "Service has no healthy endpoints"
        return 1
    fi
    
    # Perform final health check through service
    if perform_health_check "$NEW_VERSION"; then
        log_success "Production deployment verification passed"
        return 0
    else
        log_error "Production deployment verification failed"
        return 1
    fi
}

# Main deployment function
main() {
    print_header
    
    # Check if required environment variables are set
    if [[ -z "${DOCKER_IMAGE:-}" ]]; then
        log_error "DOCKER_IMAGE environment variable is required"
        exit 1
    fi
    
    log_info "Starting blue-green deployment process..."
    log_info "Docker image: ${DOCKER_IMAGE}"
    
    # Step 1: Check prerequisites
    check_prerequisites
    
    # Step 2: Identify current environment
    identify_current_environment
    
    # Step 3: Deploy new version
    deploy_new_version
    
    # Step 4: Health check new version
    if ! perform_health_check "$NEW_VERSION"; then
        log_error "Health check failed for new version"
        cleanup_failed_deployment "${APP_NAME}-${NEW_VERSION}"
        exit 1
    fi
    
    # Step 5: Switch traffic
    if ! switch_traffic; then
        log_error "Failed to switch traffic"
        cleanup_failed_deployment "${APP_NAME}-${NEW_VERSION}"
        exit 1
    fi
    
    # Step 6: Verify production deployment
    if ! verify_production; then
        log_error "Production verification failed, initiating rollback..."
        if rollback; then
            cleanup_failed_deployment "${APP_NAME}-${NEW_VERSION}"
            log_error "Deployment failed but rollback successful"
            exit 1
        else
            log_error "Deployment failed and rollback failed - manual intervention required"
            exit 2
        fi
    fi
    
    # Step 7: Cleanup old version
    cleanup_old_version
    
    log_success "🎉 Blue-green deployment completed successfully!"
    log_success "Production is now running $NEW_VERSION version"
    log_success "Zero-downtime deployment achieved with automatic rollback capability"
    
    # Final status
    echo ""
    echo "================================================================================"
    echo "📊 Deployment Summary"
    echo "================================================================================"
    echo "Previous Version: $CURRENT_VERSION"
    echo "New Version: $NEW_VERSION"
    echo "Docker Image: $DOCKER_IMAGE"
    echo "Namespace: $NAMESPACE"
    echo "Service: $SERVICE_NAME"
    echo "Status: ✅ SUCCESS"
    echo "================================================================================"
}

# Trap to handle script interruption
trap 'log_error "Deployment interrupted. Manual cleanup may be required."; exit 130' INT TERM

# Run main function
main "$@"
