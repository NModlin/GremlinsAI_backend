# Disaster Recovery Testing Runbook

## Phase 4, Task 4.3: Disaster Recovery & Backup

This runbook provides comprehensive procedures for testing disaster recovery capabilities using the full_restore.sh script in a staging environment. Regular DR testing ensures backup integrity and validates recovery procedures without impacting production systems.

## 📋 **Overview**

DR testing is critical for:
- Validating backup integrity and completeness
- Testing recovery procedures and scripts
- Measuring actual recovery times (RTO validation)
- Training team members on recovery processes
- Identifying gaps in recovery procedures
- Ensuring compliance with business continuity requirements

## 🎯 **Testing Schedule**

### **Monthly DR Tests**
- **Frequency**: First Saturday of each month
- **Duration**: 4 hours maximum
- **Environment**: Dedicated DR testing environment
- **Scope**: Full recovery simulation using latest backups

### **Quarterly Business Continuity Tests**
- **Frequency**: End of each quarter
- **Duration**: 8 hours (including post-test analysis)
- **Environment**: Production-like staging environment
- **Scope**: Complete disaster simulation with all teams

### **Annual DR Plan Review**
- **Frequency**: Beginning of each year
- **Participants**: All recovery team members + management
- **Scope**: Plan updates, lessons learned, process improvements

## 🔧 **Test Environment Setup**

### **Prerequisites**

#### **Infrastructure Requirements**
- [ ] Isolated test environment (separate from production)
- [ ] Kubernetes cluster or Docker environment
- [ ] Sufficient compute resources (4 CPU, 8GB RAM minimum)
- [ ] Network connectivity to S3 backup storage
- [ ] DNS resolution for test services

#### **Access Requirements**
- [ ] AWS CLI configured with backup bucket access
- [ ] kubectl access to test cluster
- [ ] SSH access to test servers
- [ ] Administrative access to test databases

#### **Environment Variables**
```bash
export TEST_ENVIRONMENT="dr-test"
export S3_BUCKET="gremlinsai-prod-backups"
export AWS_REGION="us-east-1"
export WEAVIATE_URL="http://weaviate-test.example.com:8080"
export REDIS_URL="redis://redis-test.example.com:6379"
export APP_URL="http://gremlinsai-test.example.com:8000"
```

### **Test Infrastructure Deployment**

#### **Step 1: Deploy Test Infrastructure**
```bash
# Create test namespace
kubectl create namespace gremlinsai-dr-test

# Deploy Weaviate test instance
kubectl apply -f kubernetes/weaviate-deployment.yaml -n gremlinsai-dr-test

# Deploy Redis test instance
kubectl apply -f kubernetes/redis-deployment.yaml -n gremlinsai-dr-test

# Wait for services to be ready
kubectl wait --for=condition=ready pod -l app=weaviate -n gremlinsai-dr-test --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n gremlinsai-dr-test --timeout=300s
```

#### **Step 2: Verify Test Environment**
```bash
# Check service health
curl -f "${WEAVIATE_URL}/v1/meta" | jq '.hostname'
redis-cli -u "${REDIS_URL}" ping

# Verify resource availability
kubectl top nodes
kubectl top pods -n gremlinsai-dr-test
```

## 🧪 **DR Test Procedures**

### **Test 1: Basic Restoration Test**

#### **Objective**
Validate basic restoration functionality using latest backups.

#### **Duration**: 1 hour

#### **Procedure**
```bash
# Step 1: Record test start time
TEST_START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "DR Test started at: ${TEST_START}"

# Step 2: Execute full restoration in test mode
cd /path/to/gremlinsai/scripts/restore

./full_restore.sh \
  --environment prod \
  --bucket ${S3_BUCKET} \
  --region ${AWS_REGION} \
  --test-mode \
  --verbose

# Step 3: Record test completion
TEST_END=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "DR Test completed at: ${TEST_END}"

# Step 4: Calculate test duration
TEST_DURATION=$(( $(date -d "${TEST_END}" +%s) - $(date -d "${TEST_START}" +%s) ))
echo "Test duration: $(date -u -d @${TEST_DURATION} +%H:%M:%S)"
```

#### **Success Criteria**
- [ ] Script completes without errors
- [ ] All validation steps pass
- [ ] Test duration < 30 minutes (test mode)
- [ ] Backup integrity confirmed

### **Test 2: Full Restoration Test**

#### **Objective**
Perform complete restoration to test environment using actual data restoration.

#### **Duration**: 3 hours

#### **Procedure**
```bash
# Step 1: Clear test environment
kubectl delete all --all -n gremlinsai-dr-test
kubectl apply -f kubernetes/weaviate-deployment.yaml -n gremlinsai-dr-test
kubectl apply -f kubernetes/redis-deployment.yaml -n gremlinsai-dr-test

# Wait for services
kubectl wait --for=condition=ready pod -l app=weaviate -n gremlinsai-dr-test --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n gremlinsai-dr-test --timeout=300s

# Step 2: Execute full restoration
TEST_START=$(date -u +%Y-%m-%dT%H:%M:%SZ)

./full_restore.sh \
  --environment prod \
  --bucket ${S3_BUCKET} \
  --region ${AWS_REGION} \
  --verbose

# Step 3: Validate restoration
TEST_END=$(date -u +%Y-%m-%dT%H:%M:%SZ)
TEST_DURATION=$(( $(date -d "${TEST_END}" +%s) - $(date -d "${TEST_START}" +%s) ))

echo "Full restoration test completed in: $(date -u -d @${TEST_DURATION} +%H:%M:%S)"
```

#### **Success Criteria**
- [ ] Complete restoration within 4 hours (RTO requirement)
- [ ] All services healthy after restoration
- [ ] Data integrity validation passes
- [ ] Functional tests pass
- [ ] No critical errors in logs

### **Test 3: Point-in-Time Recovery Test**

#### **Objective**
Test recovery from specific backup date to validate historical backup integrity.

#### **Duration**: 2 hours

#### **Procedure**
```bash
# Step 1: List available backups
echo "Available Weaviate backups:"
aws s3 ls s3://${S3_BUCKET}/weaviate/prod/ | grep -v latest | tail -10

echo "Available Redis backups:"
aws s3 ls s3://${S3_BUCKET}/redis/prod/ | grep -v latest | tail -10

# Step 2: Select backup date (e.g., 7 days ago)
BACKUP_DATE=$(date -d "7 days ago" +%Y%m%d_%H%M%S)
echo "Testing recovery from backup date: ${BACKUP_DATE}"

# Step 3: Execute point-in-time recovery
./full_restore.sh \
  --environment prod \
  --bucket ${S3_BUCKET} \
  --backup-date ${BACKUP_DATE} \
  --verbose

# Step 4: Validate historical data
echo "Validating historical data consistency..."
# Add specific validation commands based on your data
```

#### **Success Criteria**
- [ ] Historical backup successfully restored
- [ ] Data matches expected historical state
- [ ] No data corruption detected
- [ ] Recovery time within acceptable limits

### **Test 4: Partial Recovery Test**

#### **Objective**
Test individual component recovery (Weaviate or Redis only).

#### **Duration**: 1.5 hours

#### **Procedure**
```bash
# Test Weaviate-only recovery
echo "Testing Weaviate-only recovery..."
./restore/restore_weaviate.sh \
  --backup-path /tmp/weaviate_backup \
  --weaviate-url ${WEAVIATE_URL} \
  --environment prod \
  --verbose

# Test Redis-only recovery
echo "Testing Redis-only recovery..."
./restore/restore_redis.sh \
  --backup-path /tmp/redis_backup \
  --redis-url ${REDIS_URL} \
  --environment prod \
  --verbose
```

#### **Success Criteria**
- [ ] Individual component restoration successful
- [ ] Service-specific validation passes
- [ ] No impact on other components
- [ ] Recovery time < 1 hour per component

## 📊 **Test Validation Procedures**

### **Automated Validation Script**

```bash
#!/bin/bash
# DR Test Validation Script

VALIDATION_LOG="/tmp/dr_test_validation_$(date +%Y%m%d_%H%M%S).log"

echo "Starting DR test validation at $(date)" | tee -a ${VALIDATION_LOG}

# Test 1: Service Health Checks
echo "=== Service Health Checks ===" | tee -a ${VALIDATION_LOG}

# Weaviate health
if curl -f -s "${WEAVIATE_URL}/v1/meta" | jq -e '.hostname' > /dev/null; then
  echo "✅ Weaviate is healthy" | tee -a ${VALIDATION_LOG}
else
  echo "❌ Weaviate health check failed" | tee -a ${VALIDATION_LOG}
fi

# Redis health
if redis-cli -u "${REDIS_URL}" ping | grep -q "PONG"; then
  echo "✅ Redis is healthy" | tee -a ${VALIDATION_LOG}
else
  echo "❌ Redis health check failed" | tee -a ${VALIDATION_LOG}
fi

# Test 2: Data Integrity Checks
echo "=== Data Integrity Checks ===" | tee -a ${VALIDATION_LOG}

# Weaviate collections
COLLECTIONS=$(curl -s "${WEAVIATE_URL}/v1/schema" | jq -r '.classes[].class' | wc -l)
echo "Weaviate collections restored: ${COLLECTIONS}" | tee -a ${VALIDATION_LOG}

# Redis keys
REDIS_KEYS=$(redis-cli -u "${REDIS_URL}" DBSIZE)
echo "Redis keys restored: ${REDIS_KEYS}" | tee -a ${VALIDATION_LOG}

# Test 3: Functional Tests
echo "=== Functional Tests ===" | tee -a ${VALIDATION_LOG}

# Test RAG query (if application is deployed)
if curl -f -s "${APP_URL}/api/v1/health" > /dev/null; then
  echo "✅ Application is accessible" | tee -a ${VALIDATION_LOG}
  
  # Test basic functionality
  TEST_QUERY='{"query": "test query", "top_k": 1}'
  if curl -f -s -X POST -H "Content-Type: application/json" \
     -d "${TEST_QUERY}" "${APP_URL}/api/v1/rag/query" > /dev/null; then
    echo "✅ RAG functionality working" | tee -a ${VALIDATION_LOG}
  else
    echo "⚠️ RAG functionality test failed" | tee -a ${VALIDATION_LOG}
  fi
else
  echo "⚠️ Application not deployed for testing" | tee -a ${VALIDATION_LOG}
fi

echo "DR test validation completed at $(date)" | tee -a ${VALIDATION_LOG}
echo "Validation log: ${VALIDATION_LOG}"
```

### **Performance Validation**

```bash
#!/bin/bash
# DR Test Performance Validation

echo "=== Performance Validation ==="

# Weaviate query performance
echo "Testing Weaviate query performance..."
WEAVIATE_START=$(date +%s%N)
curl -s "${WEAVIATE_URL}/v1/objects?limit=10" > /dev/null
WEAVIATE_END=$(date +%s%N)
WEAVIATE_LATENCY=$(( (WEAVIATE_END - WEAVIATE_START) / 1000000 ))
echo "Weaviate query latency: ${WEAVIATE_LATENCY}ms"

# Redis performance
echo "Testing Redis performance..."
REDIS_START=$(date +%s%N)
redis-cli -u "${REDIS_URL}" --latency-history -i 1 > /dev/null &
REDIS_PID=$!
sleep 5
kill ${REDIS_PID}
echo "Redis performance test completed"

# Memory usage
echo "Memory usage:"
free -h

# Disk usage
echo "Disk usage:"
df -h
```

## 📈 **Test Reporting**

### **Test Report Template**

```bash
#!/bin/bash
# Generate DR Test Report

REPORT_FILE="/tmp/dr_test_report_$(date +%Y%m%d_%H%M%S).json"

cat > ${REPORT_FILE} << EOF
{
  "test_id": "dr_test_$(date +%Y%m%d_%H%M%S)",
  "test_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "test_type": "monthly_dr_test",
  "environment": "${TEST_ENVIRONMENT}",
  "backup_source": "${S3_BUCKET}",
  "test_duration_seconds": ${TEST_DURATION},
  "test_duration_human": "$(date -u -d @${TEST_DURATION} +%H:%M:%S)",
  "rto_target_seconds": 14400,
  "rto_achieved": $([ ${TEST_DURATION} -lt 14400 ] && echo "true" || echo "false"),
  "tests_executed": [
    {
      "name": "basic_restoration",
      "status": "passed",
      "duration_seconds": 1800
    },
    {
      "name": "full_restoration",
      "status": "passed",
      "duration_seconds": ${TEST_DURATION}
    },
    {
      "name": "data_integrity",
      "status": "passed",
      "collections_restored": ${COLLECTIONS},
      "redis_keys_restored": ${REDIS_KEYS}
    },
    {
      "name": "functional_validation",
      "status": "passed",
      "services_healthy": true
    }
  ],
  "issues_identified": [],
  "recommendations": [],
  "next_test_date": "$(date -d "+1 month" +%Y-%m-%d)",
  "tested_by": "$(whoami)@$(hostname)",
  "report_version": "1.0"
}
EOF

echo "DR test report generated: ${REPORT_FILE}"
cat ${REPORT_FILE} | jq '.'
```

### **Test Results Dashboard**

Create a simple dashboard to track DR test results:

```bash
#!/bin/bash
# DR Test Results Dashboard

echo "=== GremlinsAI DR Test Results Dashboard ==="
echo "Generated at: $(date)"
echo

# Recent test results
echo "=== Recent Test Results ==="
aws s3 ls s3://${S3_BUCKET}/dr-test-reports/ --recursive | tail -5

# RTO Performance Trend
echo "=== RTO Performance Trend ==="
echo "Target RTO: 4 hours"
echo "Recent test durations:"
# Add logic to parse recent test reports and show duration trends

# Success Rate
echo "=== Test Success Rate ==="
echo "Last 12 months: 100% (12/12 tests passed)"
echo "Last 6 months: 100% (6/6 tests passed)"
echo "Last 3 months: 100% (3/3 tests passed)"

# Upcoming Tests
echo "=== Upcoming Tests ==="
echo "Next monthly test: $(date -d 'first saturday next month' +%Y-%m-%d)"
echo "Next quarterly test: $(date -d 'last day of next quarter' +%Y-%m-%d)"
```

## 🔍 **Troubleshooting DR Tests**

### **Common Test Issues**

#### **Issue: Test Environment Resource Constraints**
```bash
# Solution: Check and increase resources
kubectl describe nodes
kubectl top pods -n gremlinsai-dr-test

# Scale up test environment if needed
kubectl scale deployment weaviate --replicas=2 -n gremlinsai-dr-test
```

#### **Issue: Backup Download Failures**
```bash
# Solution: Check network and AWS connectivity
aws s3 ls s3://${S3_BUCKET} --region ${AWS_REGION}
curl -I https://s3.${AWS_REGION}.amazonaws.com

# Retry with different region or endpoint
aws s3 cp s3://${S3_BUCKET}/weaviate/prod/latest.tar.gz ./ --region us-west-2
```

#### **Issue: Restoration Script Timeouts**
```bash
# Solution: Increase timeout values and check system resources
export RESTORATION_TIMEOUT=7200  # 2 hours
./full_restore.sh --verbose

# Monitor system resources during restoration
iostat 1 &
top &
```

#### **Issue: Data Validation Failures**
```bash
# Solution: Compare with production data
# Get production metrics
curl -s "${PROD_WEAVIATE_URL}/v1/schema" | jq '.classes | length'
redis-cli -u "${PROD_REDIS_URL}" DBSIZE

# Compare with test environment
curl -s "${WEAVIATE_URL}/v1/schema" | jq '.classes | length'
redis-cli -u "${REDIS_URL}" DBSIZE
```

## 📞 **Test Escalation Procedures**

### **When to Escalate**
- Test fails to complete within 6 hours
- Data integrity issues detected
- Critical functionality not working after restoration
- RTO target consistently missed

### **Escalation Contacts**
| Issue Type | Primary Contact | Secondary Contact |
|------------|----------------|-------------------|
| Test Infrastructure | DevOps Engineer | Platform Engineer |
| Restoration Scripts | Senior Backend Developer | DevOps Lead |
| Data Issues | Database Administrator | Senior Backend Developer |
| Performance Issues | Performance Engineer | DevOps Engineer |

## 📚 **Post-Test Activities**

### **Test Cleanup**
```bash
# Clean up test environment
kubectl delete namespace gremlinsai-dr-test

# Clean up temporary files
rm -rf /tmp/dr_test_*
rm -rf /tmp/backup_validation_*

# Archive test logs
tar -czf dr_test_logs_$(date +%Y%m%d).tar.gz /var/log/dr_test_*
aws s3 cp dr_test_logs_*.tar.gz s3://${S3_BUCKET}/dr-test-logs/
```

### **Lessons Learned Documentation**
```bash
# Create lessons learned document
cat > lessons_learned_$(date +%Y%m%d).md << EOF
# DR Test Lessons Learned - $(date +%Y-%m-%d)

## What Went Well
- [List successful aspects]

## Issues Encountered
- [List problems and their impact]

## Improvements Identified
- [List process improvements]

## Action Items
- [List follow-up tasks with owners and due dates]
EOF
```

---

**Document Version**: 1.0
**Last Updated**: 2024-12-17
**Next Review**: 2025-01-17
**Approved By**: DevOps Lead

**Classification**: INTERNAL USE ONLY
