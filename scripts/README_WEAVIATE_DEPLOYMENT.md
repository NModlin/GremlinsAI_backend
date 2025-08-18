# GremlinsAI Weaviate Deployment Guide
## Phase 2, Task 2.1: Weaviate Deployment & Schema Activation

This directory contains scripts for deploying and validating a production-ready Weaviate cluster for GremlinsAI, implementing the specifications from prometheus.md and meeting the acceptance criteria from divineKatalyst.md.

## 📁 Files Overview

### 🚀 Deployment Scripts

#### `deploy_weaviate.sh`
Production-ready Kubernetes deployment script that:
- Validates prerequisites (kubectl, cluster connectivity)
- Generates secure API keys for authentication
- Deploys Weaviate using existing Kubernetes configurations
- Waits for cluster readiness with health checks
- Provides connection information and next steps

#### `activate_weaviate_schema.py`
Schema activation script that:
- Connects to the deployed Weaviate cluster
- Creates all required collections from prometheus.md schema
- Implements idempotent schema creation (safe to run multiple times)
- Validates schema activation with comprehensive logging

#### `validate_weaviate_deployment.py`
Comprehensive validation script that:
- Tests cluster health and availability
- Validates schema configuration
- Performs CRUD operations testing
- Conducts performance testing with 10,000+ documents
- Tests connection pooling and concurrent access
- Generates detailed validation reports

## 🎯 Acceptance Criteria Validation

The scripts validate all acceptance criteria from divineKatalyst.md:

✅ **Weaviate cluster successfully deployed using Kubernetes configurations**
- Uses existing `kubernetes/weaviate-deployment.yaml`
- Deploys 3-node high-availability cluster
- Implements proper security with API key authentication

✅ **Cluster can handle 10,000+ documents with query time < 100ms**
- Performance testing with configurable document counts
- Query time validation against 100ms target
- Concurrent query testing for load validation

✅ **Schema activated with all necessary data types and vectors**
- Implements exact WEAVIATE_SCHEMA from prometheus.md
- Creates Conversation, Message, and DocumentChunk collections
- Configures text2vec-transformers vectorizer

✅ **Client connection wrapper provides consistent API with connection pooling**
- Tests multiple concurrent connections
- Validates connection pooling functionality
- Ensures 90%+ success rate for concurrent queries

## 🚀 Quick Start Guide

### Prerequisites

1. **Kubernetes Cluster Access**
   ```bash
   kubectl cluster-info  # Verify cluster connectivity
   ```

2. **Required Python Packages**
   ```bash
   pip install weaviate-client requests
   ```

3. **Environment Variables** (Optional)
   ```bash
   export WEAVIATE_URL="http://your-weaviate-cluster:8080"
   export WEAVIATE_API_KEY="your-api-key"
   ```

### Deployment Process

#### Step 1: Deploy Weaviate Cluster
```bash
# Make script executable (Linux/Mac)
chmod +x scripts/deploy_weaviate.sh

# Deploy the cluster
./scripts/deploy_weaviate.sh

# Or on Windows with Git Bash
bash scripts/deploy_weaviate.sh
```

**Expected Output:**
- Kubernetes deployment status
- Generated API keys (store securely!)
- Cluster health verification
- Connection endpoints

#### Step 2: Activate Schema
```bash
# Activate the Weaviate schema
python scripts/activate_weaviate_schema.py
```

**Expected Output:**
- Schema creation progress
- Collection validation
- Cluster health summary

#### Step 3: Validate Deployment
```bash
# Run comprehensive validation
python scripts/validate_weaviate_deployment.py
```

**Expected Output:**
- Cluster health tests
- Schema validation
- Performance benchmarks
- Validation report (JSON)

## 📊 Performance Targets

The validation ensures the following performance criteria:

| Metric | Target | Validation Method |
|--------|--------|-------------------|
| Query Response Time | < 100ms | Average of 10 test queries |
| Document Capacity | 10,000+ docs | Load testing with real data |
| Concurrent Queries | 90% success rate | 20 concurrent connections |
| Cluster Availability | 99.9% uptime | Health check validation |

## 🔧 Configuration Options

### Deployment Script Configuration
Edit variables in `deploy_weaviate.sh`:
```bash
NAMESPACE="gremlinsai"          # Kubernetes namespace
REPLICAS=3                      # Number of Weaviate nodes
STORAGE_SIZE="500Gi"           # Storage per node
MONITORING_ENABLED=true        # Enable Prometheus monitoring
```

### Validation Script Configuration
Edit `TEST_CONFIG` in `validate_weaviate_deployment.py`:
```python
TEST_CONFIG = {
    "performance_test_docs": 1000,    # Initial performance test size
    "load_test_docs": 10000,          # Full load test size
    "query_timeout_ms": 100,          # Maximum acceptable query time
    "concurrent_queries": 50,         # Concurrent query test size
    "test_collections": ["Conversation", "Message", "DocumentChunk"]
}
```

## 🔐 Security Configuration

### API Key Management
The deployment script generates secure API keys:
- **Admin Key**: Full cluster administration
- **App Key**: Application-level access (recommended for GremlinsAI)
- **Dev Key**: Development and testing access

**Important**: Store these keys securely and delete the generated file after use!

### Authentication Setup
```python
# Python client configuration
import weaviate
from weaviate.classes.init import Auth

client = weaviate.Client(
    url="http://weaviate-lb:8080",
    auth_client_secret=Auth.api_key("your-app-key")
)
```

## 🐛 Troubleshooting

### Common Issues

#### 1. Deployment Script Fails
```bash
# Check kubectl configuration
kubectl config current-context
kubectl cluster-info

# Verify Kubernetes files exist
ls -la kubernetes/weaviate-deployment.yaml
```

#### 2. Schema Activation Fails
```bash
# Check Weaviate connectivity
curl http://weaviate-lb:8080/v1/.well-known/ready

# Verify API key
export WEAVIATE_API_KEY="your-key"
python -c "import os; print('API Key:', os.getenv('WEAVIATE_API_KEY'))"
```

#### 3. Performance Tests Fail
```bash
# Check cluster resources
kubectl get pods -n gremlinsai -l app=weaviate
kubectl top pods -n gremlinsai

# Monitor cluster during tests
kubectl logs -f -l app=weaviate -n gremlinsai
```

### Log Files
All scripts generate detailed logs:
- `weaviate_schema_activation.log` - Schema activation logs
- `weaviate_validation.log` - Validation test logs
- `weaviate_validation_report_*.json` - Detailed validation reports

## 🔄 Script Usage Examples

### Deployment Script Options
```bash
# Deploy cluster (default)
./scripts/deploy_weaviate.sh

# Check deployment status
./scripts/deploy_weaviate.sh status

# View cluster logs
./scripts/deploy_weaviate.sh logs

# Clean up deployment
./scripts/deploy_weaviate.sh cleanup
```

### Schema Activation with Custom URL
```bash
# Use custom Weaviate URL
WEAVIATE_URL="http://custom-weaviate:8080" python scripts/activate_weaviate_schema.py
```

### Validation with Custom Configuration
```bash
# Run validation with environment variables
export WEAVIATE_URL="http://weaviate-lb:8080"
export WEAVIATE_API_KEY="your-app-key"
python scripts/validate_weaviate_deployment.py
```

## 📈 Monitoring and Maintenance

### Cluster Monitoring
If monitoring is enabled during deployment:
```bash
# Access Grafana dashboard
kubectl port-forward svc/grafana 3000:3000 -n gremlinsai

# View Prometheus metrics
kubectl port-forward svc/prometheus 9090:9090 -n gremlinsai
```

### Regular Health Checks
```bash
# Quick health check
kubectl get pods -n gremlinsai -l app=weaviate

# Detailed cluster status
python scripts/validate_weaviate_deployment.py
```

### Backup and Recovery
```bash
# Backup Weaviate data (if using persistent volumes)
kubectl get pvc -n gremlinsai

# Scale cluster for maintenance
kubectl scale statefulset weaviate --replicas=1 -n gremlinsai
```

## 🔗 Integration with GremlinsAI

After successful deployment and validation:

1. **Update Configuration**: Set Weaviate endpoints in GremlinsAI configuration
2. **Begin Migration**: Use migration tools to transfer data from SQLite
3. **Update Services**: Configure services to use Weaviate for vector operations
4. **Monitor Performance**: Use validation scripts for ongoing health checks

## 📚 Additional Resources

- [Weaviate Documentation](https://weaviate.io/developers/weaviate)
- [Kubernetes StatefulSets](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)
- [GremlinsAI prometheus.md](../prometheus.md) - Technical specifications
- [GremlinsAI divineKatalyst.md](../divineKatalyst.md) - Acceptance criteria

## 🆘 Support

For issues with the deployment scripts:
1. Check the troubleshooting section above
2. Review log files for detailed error information
3. Verify all prerequisites are met
4. Ensure Kubernetes cluster has sufficient resources

The scripts are designed to be robust and provide detailed feedback for any issues encountered during deployment or validation.
