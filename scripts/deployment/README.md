# Blue-Green Production Deployment - Task T3.7

## Overview

This directory contains the complete blue-green deployment solution for GremlinsAI Backend production deployment with zero-downtime and automatic rollback capabilities.

## Acceptance Criteria

✅ **Zero-downtime deployment with automatic rollback**
✅ **Production deployment must complete successfully**
✅ **Blue-green deployment strategy implementation**

## Files Overview

### Core Deployment Scripts

- **`blue-green-deploy.sh`** - Main blue-green deployment script with automatic rollback
- **`deploy-config.sh`** - Production environment setup and configuration
- **`validate-deployment.sh`** - Comprehensive deployment validation
- **`production-service.yaml`** - Production Kubernetes service configurations

### Key Features

- **Zero-Downtime Deployment**: Traffic switching without service interruption
- **Automatic Rollback**: Immediate rollback on health check failures
- **Health Validation**: Comprehensive health checks before traffic switch
- **Resource Management**: Automatic cleanup of old deployments
- **Monitoring Integration**: Prometheus metrics and monitoring support

## Quick Start

### 1. Prerequisites

```bash
# Ensure kubectl is configured for your production cluster
kubectl cluster-info

# Ensure you have the required environment variables
export DOCKER_IMAGE="gremlinsai/backend:v1.0.0"
export NAMESPACE="gremlinsai"
```

### 2. Setup Production Environment

```bash
# Make scripts executable
chmod +x scripts/deployment/*.sh

# Setup production environment (first time only)
./scripts/deployment/deploy-config.sh
```

### 3. Deploy to Production

```bash
# Run blue-green deployment
DOCKER_IMAGE="gremlinsai/backend:v1.0.0" ./scripts/deployment/blue-green-deploy.sh
```

### 4. Validate Deployment

```bash
# Validate production deployment
./scripts/deployment/validate-deployment.sh
```

## Detailed Usage

### Environment Setup

The `deploy-config.sh` script sets up the production environment:

```bash
# Basic setup
./deploy-config.sh

# With custom namespace
NAMESPACE=production ./deploy-config.sh

# With custom environment variables
DB_HOST=prod-db.example.com \
REDIS_HOST=prod-redis.example.com \
./deploy-config.sh
```

**What it creates:**
- Kubernetes namespace with labels
- Service account and RBAC permissions
- Configuration secrets for database, Redis, Weaviate, Ollama
- Application configuration maps
- Production services (LoadBalancer, Ingress, NetworkPolicy)
- Pod Disruption Budget and HPA

### Blue-Green Deployment

The `blue-green-deploy.sh` script performs the deployment:

```bash
# Basic deployment
DOCKER_IMAGE="gremlinsai/backend:v1.0.0" ./blue-green-deploy.sh

# With custom configuration
DOCKER_IMAGE="gremlinsai/backend:v1.0.0" \
NAMESPACE="production" \
HEALTH_CHECK_TIMEOUT=600 \
./blue-green-deploy.sh
```

**Deployment Process:**
1. **Identify Current Environment** - Determines active blue/green version
2. **Deploy New Version** - Creates new deployment in inactive environment
3. **Health Check** - Validates new deployment health
4. **Switch Traffic** - Updates service selector to new version
5. **Verify Production** - Confirms production deployment success
6. **Cleanup** - Removes old deployment resources

### Configuration Options

#### Environment Variables

**Required:**
- `DOCKER_IMAGE` - Docker image to deploy (e.g., `gremlinsai/backend:v1.0.0`)

**Optional:**
- `NAMESPACE` - Kubernetes namespace (default: `gremlinsai`)
- `APP_NAME` - Application name (default: `gremlinsai-backend`)
- `SERVICE_NAME` - Service name (default: `gremlinsai-service`)
- `HEALTH_CHECK_URL` - Health check endpoint (default: `http://localhost:8080/api/v1/health/health`)
- `HEALTH_CHECK_TIMEOUT` - Health check timeout in seconds (default: `300`)
- `HEALTH_CHECK_INTERVAL` - Health check interval in seconds (default: `10`)
- `ROLLBACK_TIMEOUT` - Rollback timeout in seconds (default: `60`)

#### Database Configuration

```bash
# Database settings
export DB_HOST="prod-postgres.example.com"
export DB_PORT="5432"
export DB_NAME="gremlinsai"
export DB_USER="gremlinsai"
export DB_PASSWORD="secure-password"

# Redis settings
export REDIS_HOST="prod-redis.example.com"
export REDIS_PORT="6379"
export REDIS_PASSWORD="redis-password"

# Weaviate settings
export WEAVIATE_URL="http://weaviate.example.com:8080"
export WEAVIATE_API_KEY="weaviate-api-key"

# Ollama settings
export OLLAMA_BASE_URL="http://ollama.example.com:11434"
export OLLAMA_MODEL="llama3.2:3b"
```

## Deployment Validation

### Automatic Validation

The deployment script includes automatic validation:

- **Pod Readiness**: Ensures all pods are ready and healthy
- **Health Endpoints**: Validates `/health`, `/ready`, `/live` endpoints
- **Service Connectivity**: Confirms service routing works correctly
- **Resource Allocation**: Verifies resource requests and limits

### Manual Validation

Use the validation script for comprehensive checks:

```bash
# Full validation suite
./validate-deployment.sh

# With custom timeout
VALIDATION_TIMEOUT=600 ./validate-deployment.sh

# With extended load test
LOAD_TEST_DURATION=300 ./validate-deployment.sh
```

**Validation Checks:**
- ✅ Kubernetes resources (deployments, services, pods)
- ✅ Health endpoints (`/health`, `/ready`, `/live`)
- ✅ API functionality (root, capabilities, metrics endpoints)
- ✅ Monitoring integration (Prometheus scraping)
- ✅ Network connectivity (DNS, service mesh)
- ✅ Resource utilization (CPU, memory usage)
- ✅ Basic load testing (95% success rate required)

## Rollback Process

### Automatic Rollback

The deployment script automatically rolls back if:
- Health checks fail after traffic switch
- Production verification fails
- Service endpoints become unavailable

### Manual Rollback

If manual rollback is needed:

```bash
# Identify current version
kubectl get service gremlinsai-service -n gremlinsai -o jsonpath='{.spec.selector.version}'

# Switch back to previous version (blue/green)
kubectl patch service gremlinsai-service -n gremlinsai -p '{"spec":{"selector":{"version":"blue"}}}'

# Verify rollback
./validate-deployment.sh
```

## Monitoring and Observability

### Prometheus Integration

The deployment includes Prometheus monitoring:

```yaml
# Pod annotations for scraping
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8080"
  prometheus.io/path: "/metrics"
```

### Key Metrics

Monitor these metrics during deployment:

- `gremlinsai_api_requests_total` - API request count
- `gremlinsai_api_request_duration_seconds` - Response times
- `gremlinsai_api_errors_total` - Error rates
- `gremlinsai_active_conversations` - Active user sessions

### Grafana Dashboards

Use the GremlinsAI monitoring dashboard to track:
- Deployment progress and health
- Traffic switching success
- Performance metrics comparison
- Error rates and response times

## Troubleshooting

### Common Issues

#### Deployment Fails to Start

```bash
# Check pod status
kubectl get pods -n gremlinsai -l app=gremlinsai-backend

# Check pod logs
kubectl logs -n gremlinsai deployment/gremlinsai-backend-green

# Check events
kubectl get events -n gremlinsai --sort-by='.lastTimestamp'
```

#### Health Checks Fail

```bash
# Test health endpoint directly
kubectl exec -n gremlinsai deployment/gremlinsai-backend-green -- curl http://localhost:8080/api/v1/health/health

# Check application logs
kubectl logs -n gremlinsai deployment/gremlinsai-backend-green -f
```

#### Traffic Switch Issues

```bash
# Verify service selector
kubectl get service gremlinsai-service -n gremlinsai -o yaml

# Check endpoints
kubectl get endpoints gremlinsai-service -n gremlinsai

# Test service connectivity
kubectl run test-pod --rm -i --tty --image=curlimages/curl -- curl http://gremlinsai-service.gremlinsai.svc.cluster.local/api/v1/health/health
```

### Recovery Procedures

#### Failed Deployment Recovery

```bash
# 1. Check current state
kubectl get deployments -n gremlinsai
kubectl get services -n gremlinsai

# 2. Manual rollback if needed
kubectl patch service gremlinsai-service -n gremlinsai -p '{"spec":{"selector":{"version":"blue"}}}'

# 3. Clean up failed deployment
kubectl delete deployment gremlinsai-backend-green -n gremlinsai

# 4. Validate rollback
./validate-deployment.sh
```

#### Complete Environment Reset

```bash
# WARNING: This will delete all deployments
kubectl delete namespace gremlinsai

# Recreate environment
./deploy-config.sh

# Redeploy application
DOCKER_IMAGE="gremlinsai/backend:v1.0.0" ./blue-green-deploy.sh
```

## Security Considerations

### Network Policies

The deployment includes network policies that:
- Allow ingress from ingress controller
- Allow monitoring traffic from Prometheus
- Restrict egress to required services only
- Enable internal pod-to-pod communication

### RBAC Permissions

Service account permissions are minimal:
- Read access to pods, services, endpoints
- Read access to deployments and replica sets
- Read access to metrics for monitoring

### Secrets Management

Sensitive configuration is stored in Kubernetes secrets:
- Database credentials
- Redis authentication
- API keys and tokens
- Encryption keys

## Performance Considerations

### Resource Allocation

Default resource allocation:
```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "1Gi"
    cpu: "1000m"
```

### Scaling Configuration

Horizontal Pod Autoscaler settings:
- Min replicas: 3
- Max replicas: 20
- CPU target: 70%
- Memory target: 80%

### Load Balancing

Service configuration:
- LoadBalancer type for external access
- Session affinity: None (stateless)
- Multiple ports (HTTP, HTTPS, metrics)

## Best Practices

### Pre-Deployment Checklist

- [ ] Docker image built and pushed to registry
- [ ] Environment variables configured
- [ ] Database migrations completed
- [ ] Monitoring dashboards ready
- [ ] Rollback plan documented

### During Deployment

- [ ] Monitor deployment progress
- [ ] Watch health check status
- [ ] Verify traffic switching
- [ ] Check error rates and response times
- [ ] Validate all endpoints

### Post-Deployment

- [ ] Run full validation suite
- [ ] Monitor for 15-30 minutes
- [ ] Check application logs
- [ ] Verify monitoring integration
- [ ] Document deployment notes

## Support

For deployment issues:

1. **Check Logs**: Application and Kubernetes event logs
2. **Validate Configuration**: Ensure all environment variables are set
3. **Test Connectivity**: Verify network and service connectivity
4. **Monitor Metrics**: Use Grafana dashboards for insights
5. **Manual Verification**: Run validation scripts

## Summary

This blue-green deployment solution provides:

- ✅ **Zero-downtime deployments** with traffic switching
- ✅ **Automatic rollback** on failure detection
- ✅ **Comprehensive validation** of deployment health
- ✅ **Production-ready configuration** with monitoring
- ✅ **Security best practices** with RBAC and network policies
- ✅ **Scalability support** with HPA and load balancing

The deployment process ensures safe, reliable production deployments with minimal risk and maximum observability.
