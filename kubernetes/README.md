# Weaviate Production Deployment

This directory contains the Kubernetes configuration files for deploying a high-availability Weaviate cluster designed to meet production requirements including 99.9% uptime and 10,000 QPS performance.

## Architecture Overview

### High Availability Design
- **3-node StatefulSet** with anti-affinity rules ensuring pods are distributed across different nodes
- **Automatic failover** through Kubernetes health checks and pod restart policies
- **PodDisruptionBudget** ensuring minimum 2 pods remain available during maintenance
- **HorizontalPodAutoscaler** for dynamic scaling based on CPU/memory utilization

### Performance Specifications
- **Target QPS**: 10,000 queries per second
- **Target Latency**: <100ms for 95th percentile
- **Target Uptime**: 99.9% availability
- **Storage**: 500GB high-performance SSD per node
- **Resources**: 4 CPU cores and 16GB RAM per pod

### Security Features
- **API Key Authentication** with role-based access control
- **Network Policies** restricting traffic to authorized sources
- **Encrypted storage** with AWS EBS encryption
- **Non-root container** execution for enhanced security

## Files Description

### Core Deployment Files
- `weaviate-deployment.yaml` - Main deployment configuration including StatefulSet, Services, and supporting resources
- `weaviate-monitoring.yaml` - Monitoring configuration with Prometheus metrics and Grafana dashboards
- `deploy-weaviate.sh` - Automated deployment script with validation and testing

### Configuration Components

#### weaviate-deployment.yaml
```yaml
# Contains:
- StatefulSet (3 replicas with anti-affinity)
- Headless Service (for StatefulSet networking)
- LoadBalancer Service (for external access)
- ConfigMap (Weaviate configuration)
- Secret (API keys and authentication)
- Namespace (gremlinsai)
- StorageClass (high-performance SSD)
- PodDisruptionBudget (minimum availability)
- HorizontalPodAutoscaler (dynamic scaling)
```

#### weaviate-monitoring.yaml
```yaml
# Contains:
- ServiceMonitor (Prometheus scraping)
- PrometheusRule (alerting rules)
- ConfigMap (Grafana dashboard)
- NetworkPolicy (security restrictions)
```

## Deployment Instructions

### Prerequisites
1. **Kubernetes Cluster** (v1.20+) with at least 3 worker nodes
2. **kubectl** configured with cluster admin access
3. **Persistent Volume** support (AWS EBS, GCE PD, or equivalent)
4. **LoadBalancer** support (cloud provider or MetalLB)
5. **Monitoring Stack** (Prometheus/Grafana) for observability

### Quick Deployment
```bash
# Make deployment script executable
chmod +x kubernetes/deploy-weaviate.sh

# Run automated deployment
./kubernetes/deploy-weaviate.sh
```

### Manual Deployment
```bash
# Create namespace
kubectl create namespace gremlinsai

# Apply main deployment
kubectl apply -f kubernetes/weaviate-deployment.yaml

# Apply monitoring (optional)
kubectl apply -f kubernetes/weaviate-monitoring.yaml

# Verify deployment
kubectl get pods -n gremlinsai -l app=weaviate
```

### Verification Commands
```bash
# Check pod status
kubectl get pods -n gremlinsai -l app=weaviate

# Check service endpoints
kubectl get svc -n gremlinsai

# Check persistent volumes
kubectl get pvc -n gremlinsai

# Test connectivity
kubectl run test-pod --rm -i --tty --image=curlimages/curl --restart=Never -n gremlinsai -- \
  curl -s http://weaviate-headless:8080/v1/.well-known/ready
```

## Configuration Details

### Resource Allocation
Each Weaviate pod is configured with:
- **CPU Request**: 2 cores (guaranteed)
- **CPU Limit**: 4 cores (maximum)
- **Memory Request**: 8GB (guaranteed)
- **Memory Limit**: 16GB (maximum)
- **Storage**: 500GB high-performance SSD

### Environment Variables
Key configuration parameters:
```yaml
AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: "false"
AUTHENTICATION_APIKEY_ENABLED: "true"
PERSISTENCE_DATA_PATH: "/var/lib/weaviate"
CLUSTER_JOIN: "weaviate-0.weaviate-headless...:7100,..."
QUERY_MAXIMUM_RESULTS: "10000"
PROMETHEUS_MONITORING_ENABLED: "true"
```

### Health Checks
- **Liveness Probe**: `/v1/.well-known/live` (120s initial delay)
- **Readiness Probe**: `/v1/.well-known/ready` (30s initial delay)
- **Failure Threshold**: 3 consecutive failures trigger restart

### Networking
- **HTTP Port**: 8080 (REST API)
- **gRPC Port**: 50051 (gRPC API)
- **Gossip Port**: 7100 (cluster communication)
- **Data Port**: 7101 (data replication)

## Monitoring and Alerting

### Prometheus Metrics
The deployment exposes comprehensive metrics including:
- Request rate and latency percentiles
- Error rates and status codes
- Resource utilization (CPU, memory, disk)
- Cluster health and node status

### Alert Rules
Critical alerts configured:
- **WeaviateInstanceDown**: Pod unavailable for >1 minute
- **WeaviateClusterUnhealthy**: <2 pods running for >2 minutes
- **WeaviateHighLatency**: 95th percentile >100ms for >5 minutes
- **WeaviateHighErrorRate**: Error rate >5% for >3 minutes

### Grafana Dashboard
Pre-configured dashboard includes:
- Cluster health overview
- Request rate and latency trends
- Error rate monitoring
- Resource utilization graphs
- Performance metrics

## Security Configuration

### Authentication
- **API Key Authentication** enabled by default
- **Anonymous access** disabled
- **Role-based access** with admin/app/dev keys

### Network Security
- **NetworkPolicy** restricts ingress to authorized sources
- **Pod-to-pod** communication allowed within cluster
- **External access** only through LoadBalancer service

### Storage Security
- **Encryption at rest** enabled for persistent volumes
- **Secure key management** through Kubernetes secrets
- **Non-root execution** for container security

## Scaling and Performance

### Horizontal Scaling
- **Minimum replicas**: 3 (high availability)
- **Maximum replicas**: 9 (performance scaling)
- **Scale-up trigger**: CPU >70% or Memory >80%
- **Scale-down trigger**: Resource usage <50%

### Performance Tuning
- **LSM access strategy**: mmap for optimal performance
- **Flush interval**: 60s for balanced durability/performance
- **Query limits**: 10,000 maximum results per query
- **Connection pooling**: Enabled for efficient resource usage

### Storage Performance
- **Storage class**: gp3 with 16,000 IOPS and 1,000 MB/s throughput
- **Volume expansion**: Enabled for future growth
- **Reclaim policy**: Retain for data protection

## Maintenance and Operations

### Backup Strategy
```bash
# Create backup of persistent volumes
kubectl create -f backup-job.yaml

# Export schema and data
kubectl exec -n gremlinsai weaviate-0 -- weaviate-tool export-schema
kubectl exec -n gremlinsai weaviate-0 -- weaviate-tool export-data
```

### Rolling Updates
```bash
# Update Weaviate version
kubectl patch statefulset weaviate -n gremlinsai -p '{"spec":{"template":{"spec":{"containers":[{"name":"weaviate","image":"semitechnologies/weaviate:1.23.0"}]}}}}'

# Monitor rollout
kubectl rollout status statefulset/weaviate -n gremlinsai
```

### Troubleshooting
```bash
# Check pod logs
kubectl logs -n gremlinsai weaviate-0 -f

# Check events
kubectl get events -n gremlinsai --sort-by='.lastTimestamp'

# Debug networking
kubectl exec -n gremlinsai weaviate-0 -- netstat -tlnp

# Check cluster status
kubectl exec -n gremlinsai weaviate-0 -- curl localhost:8080/v1/nodes
```

## Cost Optimization

### Resource Efficiency
- **Right-sizing**: Resources allocated based on actual usage patterns
- **Auto-scaling**: Dynamic scaling reduces costs during low usage
- **Storage optimization**: Efficient data structures and compression

### Monitoring Costs
- Track resource utilization through Grafana dashboards
- Set up alerts for unusual resource consumption
- Regular review of scaling policies and resource requests

## Disaster Recovery

### Backup Procedures
1. **Automated backups** of persistent volumes
2. **Schema exports** for configuration recovery
3. **Cross-region replication** for geographic redundancy

### Recovery Procedures
1. **Pod failure**: Automatic restart by Kubernetes
2. **Node failure**: Pod rescheduling to healthy nodes
3. **Cluster failure**: Restore from backups to new cluster

## Support and Troubleshooting

### Common Issues
- **Pod startup failures**: Check resource availability and storage
- **Network connectivity**: Verify NetworkPolicy and service configuration
- **Performance issues**: Monitor resource utilization and scaling policies

### Getting Help
- Check Weaviate documentation: https://weaviate.io/developers/weaviate
- Review Kubernetes logs and events
- Monitor Prometheus metrics and Grafana dashboards
- Contact support with deployment configuration and logs
