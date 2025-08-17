#!/bin/bash

# Deployment Configuration Script for GremlinsAI Backend
# 
# This script sets up the production environment and configuration
# required for blue-green deployments.

set -euo pipefail

# Configuration
NAMESPACE="${NAMESPACE:-gremlinsai}"
ENVIRONMENT="${ENVIRONMENT:-production}"

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
    echo "🔧 GremlinsAI Production Environment Setup"
    echo "================================================================================"
    echo "Namespace: $NAMESPACE"
    echo "Environment: $ENVIRONMENT"
    echo "================================================================================"
}

# Create namespace if it doesn't exist
create_namespace() {
    log_info "Creating namespace '$NAMESPACE' if it doesn't exist..."
    
    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_info "Namespace '$NAMESPACE' already exists"
    else
        kubectl create namespace "$NAMESPACE"
        log_success "Namespace '$NAMESPACE' created"
    fi
    
    # Label namespace for monitoring and network policies
    kubectl label namespace "$NAMESPACE" name="$NAMESPACE" --overwrite
    kubectl label namespace "$NAMESPACE" environment="$ENVIRONMENT" --overwrite
    kubectl label namespace "$NAMESPACE" tier="production" --overwrite
}

# Create service account and RBAC
create_service_account() {
    log_info "Creating service account and RBAC..."
    
    cat <<EOF | kubectl apply -f -
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: gremlinsai-backend
  namespace: $NAMESPACE
  labels:
    app: gremlinsai-backend
    tier: production

---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: gremlinsai-backend
  namespace: $NAMESPACE
  labels:
    app: gremlinsai-backend
    tier: production
rules:
  - apiGroups: [""]
    resources: ["pods", "services", "endpoints", "configmaps", "secrets"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["apps"]
    resources: ["deployments", "replicasets"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["metrics.k8s.io"]
    resources: ["pods", "nodes"]
    verbs: ["get", "list"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: gremlinsai-backend
  namespace: $NAMESPACE
  labels:
    app: gremlinsai-backend
    tier: production
subjects:
  - kind: ServiceAccount
    name: gremlinsai-backend
    namespace: $NAMESPACE
roleRef:
  kind: Role
  name: gremlinsai-backend
  apiGroup: rbac.authorization.k8s.io
EOF

    log_success "Service account and RBAC created"
}

# Create configuration secrets
create_secrets() {
    log_info "Creating configuration secrets..."
    
    # Database configuration
    kubectl create secret generic gremlinsai-db-config \
        --namespace="$NAMESPACE" \
        --from-literal=host="${DB_HOST:-localhost}" \
        --from-literal=port="${DB_PORT:-5432}" \
        --from-literal=database="${DB_NAME:-gremlinsai}" \
        --from-literal=username="${DB_USER:-gremlinsai}" \
        --from-literal=password="${DB_PASSWORD:-changeme}" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Redis configuration
    kubectl create secret generic gremlinsai-redis-config \
        --namespace="$NAMESPACE" \
        --from-literal=host="${REDIS_HOST:-localhost}" \
        --from-literal=port="${REDIS_PORT:-6379}" \
        --from-literal=password="${REDIS_PASSWORD:-}" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Weaviate configuration
    kubectl create secret generic gremlinsai-weaviate-config \
        --namespace="$NAMESPACE" \
        --from-literal=url="${WEAVIATE_URL:-http://weaviate:8080}" \
        --from-literal=api-key="${WEAVIATE_API_KEY:-}" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Ollama configuration
    kubectl create secret generic gremlinsai-ollama-config \
        --namespace="$NAMESPACE" \
        --from-literal=base-url="${OLLAMA_BASE_URL:-http://ollama:11434}" \
        --from-literal=model="${OLLAMA_MODEL:-llama3.2:3b}" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Application secrets
    kubectl create secret generic gremlinsai-app-secrets \
        --namespace="$NAMESPACE" \
        --from-literal=secret-key="${SECRET_KEY:-$(openssl rand -hex 32)}" \
        --from-literal=jwt-secret="${JWT_SECRET:-$(openssl rand -hex 32)}" \
        --from-literal=encryption-key="${ENCRYPTION_KEY:-$(openssl rand -hex 32)}" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    log_success "Configuration secrets created"
}

# Create config maps
create_config_maps() {
    log_info "Creating configuration maps..."
    
    cat <<EOF | kubectl apply -f -
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: gremlinsai-app-config
  namespace: $NAMESPACE
  labels:
    app: gremlinsai-backend
    tier: production
data:
  ENVIRONMENT: "$ENVIRONMENT"
  LOG_LEVEL: "info"
  DEBUG: "false"
  
  # API Configuration
  API_HOST: "0.0.0.0"
  API_PORT: "8080"
  API_WORKERS: "4"
  
  # Performance Configuration
  MAX_CONCURRENT_REQUESTS: "100"
  REQUEST_TIMEOUT: "30"
  KEEP_ALIVE_TIMEOUT: "65"
  
  # LLM Configuration
  LLM_POOL_SIZE: "5"
  LLM_TIMEOUT: "30"
  LLM_MAX_TOKENS: "2048"
  LLM_TEMPERATURE: "0.1"
  
  # RAG Configuration
  RAG_ENABLE_CACHING: "true"
  RAG_CACHE_SIZE: "1000"
  RAG_CACHE_TTL: "300"
  RAG_MAX_RESULTS: "10"
  
  # Monitoring Configuration
  METRICS_ENABLED: "true"
  METRICS_PORT: "8080"
  METRICS_PATH: "/api/v1/metrics"
  
  # Health Check Configuration
  HEALTH_CHECK_INTERVAL: "30"
  STARTUP_TIMEOUT: "60"
  SHUTDOWN_TIMEOUT: "30"

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: gremlinsai-deployment-config
  namespace: $NAMESPACE
  labels:
    app: gremlinsai-backend
    tier: production
data:
  # Blue-Green Deployment Configuration
  DEPLOYMENT_STRATEGY: "blue-green"
  HEALTH_CHECK_URL: "http://localhost:8080/api/v1/health/health"
  HEALTH_CHECK_TIMEOUT: "300"
  HEALTH_CHECK_INTERVAL: "10"
  ROLLBACK_TIMEOUT: "60"
  
  # Scaling Configuration
  MIN_REPLICAS: "3"
  MAX_REPLICAS: "20"
  TARGET_CPU_UTILIZATION: "70"
  TARGET_MEMORY_UTILIZATION: "80"
  
  # Resource Configuration
  MEMORY_REQUEST: "512Mi"
  MEMORY_LIMIT: "1Gi"
  CPU_REQUEST: "500m"
  CPU_LIMIT: "1000m"
EOF

    log_success "Configuration maps created"
}

# Apply production services
apply_production_services() {
    log_info "Applying production services..."
    
    # Apply the production service configuration
    kubectl apply -f "$(dirname "$0")/production-service.yaml"
    
    log_success "Production services applied"
}

# Verify setup
verify_setup() {
    log_info "Verifying production environment setup..."
    
    # Check namespace
    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_success "Namespace '$NAMESPACE' exists"
    else
        log_error "Namespace '$NAMESPACE' not found"
        return 1
    fi
    
    # Check service account
    if kubectl get serviceaccount gremlinsai-backend -n "$NAMESPACE" &> /dev/null; then
        log_success "Service account exists"
    else
        log_error "Service account not found"
        return 1
    fi
    
    # Check secrets
    local secrets=("gremlinsai-db-config" "gremlinsai-redis-config" "gremlinsai-weaviate-config" "gremlinsai-ollama-config" "gremlinsai-app-secrets")
    for secret in "${secrets[@]}"; do
        if kubectl get secret "$secret" -n "$NAMESPACE" &> /dev/null; then
            log_success "Secret '$secret' exists"
        else
            log_error "Secret '$secret' not found"
            return 1
        fi
    done
    
    # Check config maps
    local configmaps=("gremlinsai-app-config" "gremlinsai-deployment-config")
    for configmap in "${configmaps[@]}"; do
        if kubectl get configmap "$configmap" -n "$NAMESPACE" &> /dev/null; then
            log_success "ConfigMap '$configmap' exists"
        else
            log_error "ConfigMap '$configmap' not found"
            return 1
        fi
    done
    
    # Check service
    if kubectl get service gremlinsai-service -n "$NAMESPACE" &> /dev/null; then
        log_success "Production service exists"
    else
        log_error "Production service not found"
        return 1
    fi
    
    log_success "Production environment setup verification passed"
    return 0
}

# Main function
main() {
    print_header
    
    log_info "Setting up production environment for GremlinsAI Backend..."
    
    # Step 1: Create namespace
    create_namespace
    
    # Step 2: Create service account and RBAC
    create_service_account
    
    # Step 3: Create secrets
    create_secrets
    
    # Step 4: Create config maps
    create_config_maps
    
    # Step 5: Apply production services
    apply_production_services
    
    # Step 6: Verify setup
    if verify_setup; then
        log_success "🎉 Production environment setup completed successfully!"
        
        echo ""
        echo "================================================================================"
        echo "📊 Setup Summary"
        echo "================================================================================"
        echo "Namespace: $NAMESPACE"
        echo "Environment: $ENVIRONMENT"
        echo "Service Account: gremlinsai-backend"
        echo "Secrets: 5 created"
        echo "ConfigMaps: 2 created"
        echo "Services: Production services applied"
        echo "Status: ✅ READY FOR DEPLOYMENT"
        echo "================================================================================"
        echo ""
        echo "Next steps:"
        echo "1. Set DOCKER_IMAGE environment variable"
        echo "2. Run: ./blue-green-deploy.sh"
        echo "================================================================================"
    else
        log_error "Production environment setup failed"
        exit 1
    fi
}

# Run main function
main "$@"
