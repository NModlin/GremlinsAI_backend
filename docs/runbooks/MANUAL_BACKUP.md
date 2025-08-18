# Manual Backup Runbook

## Phase 4, Task 4.3: Disaster Recovery & Backup

This runbook provides step-by-step procedures for manually triggering backup operations for GremlinsAI components. Use these procedures for ad-hoc backups, pre-maintenance backups, or when automated backups need to be supplemented.

## 📋 **Overview**

Manual backups are essential for:
- Pre-maintenance or pre-deployment backups
- Ad-hoc backups before risky operations
- Backup validation and testing
- Emergency backup creation
- Troubleshooting automated backup issues

## 🎯 **Prerequisites**

### **Required Access**
- [ ] SSH access to production servers
- [ ] AWS CLI configured with appropriate permissions
- [ ] Access to S3 backup bucket
- [ ] Kubernetes cluster access (if applicable)
- [ ] Redis and Weaviate administrative access

### **Required Tools**
- [ ] AWS CLI v2.x
- [ ] kubectl (for Kubernetes deployments)
- [ ] redis-cli
- [ ] curl and jq
- [ ] Bash shell environment

### **Environment Variables**
```bash
export ENVIRONMENT="prod"  # or dev/staging
export S3_BUCKET="gremlinsai-prod-backups"
export AWS_REGION="us-east-1"
export WEAVIATE_URL="http://localhost:8080"
export REDIS_URL="redis://localhost:6379"
```

## 🔧 **Manual Weaviate Backup**

### **Step 1: Pre-Backup Checks**

#### **1.1 Verify Weaviate Health**
```bash
# Check Weaviate connectivity
curl -f "${WEAVIATE_URL}/v1/meta" | jq '.hostname'

# Check available collections
curl -s "${WEAVIATE_URL}/v1/schema" | jq '.classes[].class'

# Check cluster status (if clustered)
curl -s "${WEAVIATE_URL}/v1/nodes" | jq '.'
```

#### **1.2 Check System Resources**
```bash
# Check disk space (need at least 10GB free)
df -h /var/lib/weaviate

# Check memory usage
free -h

# Check CPU load
uptime
```

#### **1.3 Verify S3 Access**
```bash
# Test S3 bucket access
aws s3 ls s3://${S3_BUCKET}/weaviate/${ENVIRONMENT}/

# Check AWS credentials
aws sts get-caller-identity
```

### **Step 2: Execute Weaviate Backup**

#### **2.1 Run Backup Script**
```bash
# Navigate to scripts directory
cd /path/to/gremlinsai/scripts/backup

# Make script executable
chmod +x backup_weaviate.sh

# Execute backup with verbose output
./backup_weaviate.sh \
  --environment ${ENVIRONMENT} \
  --bucket ${S3_BUCKET} \
  --region ${AWS_REGION} \
  --verbose
```

#### **2.2 Monitor Backup Progress**
```bash
# Monitor backup logs
tail -f ../../logs/backup/backup_weaviate_$(date +%Y%m%d).log

# Check Weaviate backup status (if using backup API)
curl -s "${WEAVIATE_URL}/v1/backups" | jq '.'
```

#### **2.3 Verify Backup Completion**
```bash
# Check S3 for new backup
aws s3 ls s3://${S3_BUCKET}/weaviate/${ENVIRONMENT}/ --recursive | tail -5

# Verify backup metadata
aws s3 cp s3://${S3_BUCKET}/weaviate/${ENVIRONMENT}/latest.tar.gz - | \
  tar -xzO */backup_metadata.json | jq '.'
```

### **Step 3: Post-Backup Validation**

#### **3.1 Backup Integrity Check**
```bash
# Download and verify backup
mkdir -p /tmp/backup_validation
cd /tmp/backup_validation

aws s3 cp s3://${S3_BUCKET}/weaviate/${ENVIRONMENT}/latest.tar.gz ./
tar -xzf latest.tar.gz

# Check backup contents
ls -la weaviate_*/
cat weaviate_*/backup_metadata.json | jq '.'
```

#### **3.2 Log Backup Details**
```bash
# Record backup information
echo "Manual Weaviate backup completed at $(date)" >> /var/log/manual_backups.log
echo "Backup ID: $(cat weaviate_*/backup_metadata.json | jq -r '.backup_id')" >> /var/log/manual_backups.log
echo "S3 Location: s3://${S3_BUCKET}/weaviate/${ENVIRONMENT}/latest.tar.gz" >> /var/log/manual_backups.log
```

## 🔧 **Manual Redis Backup**

### **Step 1: Pre-Backup Checks**

#### **1.1 Verify Redis Health**
```bash
# Check Redis connectivity
redis-cli -h ${REDIS_HOST} -p ${REDIS_PORT} ping

# Check Redis info
redis-cli -h ${REDIS_HOST} -p ${REDIS_PORT} INFO server

# Check memory usage
redis-cli -h ${REDIS_HOST} -p ${REDIS_PORT} INFO memory
```

#### **1.2 Check Redis Configuration**
```bash
# Check persistence settings
redis-cli -h ${REDIS_HOST} -p ${REDIS_PORT} CONFIG GET save
redis-cli -h ${REDIS_HOST} -p ${REDIS_PORT} CONFIG GET appendonly

# Check data directory
redis-cli -h ${REDIS_HOST} -p ${REDIS_PORT} CONFIG GET dir
```

### **Step 2: Execute Redis Backup**

#### **2.1 Run Backup Script**
```bash
# Navigate to scripts directory
cd /path/to/gremlinsai/scripts/backup

# Make script executable
chmod +x backup_redis.sh

# Execute backup with verbose output
./backup_redis.sh \
  --environment ${ENVIRONMENT} \
  --bucket ${S3_BUCKET} \
  --region ${AWS_REGION} \
  --type both \
  --verbose
```

#### **2.2 Monitor Backup Progress**
```bash
# Monitor backup logs
tail -f ../../logs/backup/backup_redis_$(date +%Y%m%d).log

# Check Redis backup operations
redis-cli -h ${REDIS_HOST} -p ${REDIS_PORT} INFO persistence
```

#### **2.3 Verify Backup Completion**
```bash
# Check S3 for new backup
aws s3 ls s3://${S3_BUCKET}/redis/${ENVIRONMENT}/ --recursive | tail -5

# Verify backup metadata
aws s3 cp s3://${S3_BUCKET}/redis/${ENVIRONMENT}/latest.tar.gz - | \
  tar -xzO */backup_metadata.json | jq '.'
```

### **Step 3: Post-Backup Validation**

#### **3.1 Backup Integrity Check**
```bash
# Download and verify backup
mkdir -p /tmp/redis_backup_validation
cd /tmp/redis_backup_validation

aws s3 cp s3://${S3_BUCKET}/redis/${ENVIRONMENT}/latest.tar.gz ./
tar -xzf latest.tar.gz

# Check backup contents
ls -la redis_*/
cat redis_*/backup_metadata.json | jq '.'

# Verify RDB file (if present)
if [[ -f redis_*/dump.rdb ]]; then
  file redis_*/dump.rdb
  ls -lh redis_*/dump.rdb
fi

# Verify AOF file (if present)
if [[ -f redis_*/appendonly.aof ]]; then
  file redis_*/appendonly.aof
  ls -lh redis_*/appendonly.aof
fi
```

## 🚨 **Emergency Backup Procedures**

### **Critical System Backup (All Components)**

When immediate backup of all components is required:

#### **Step 1: Parallel Backup Execution**
```bash
# Create emergency backup directory
mkdir -p /tmp/emergency_backup_$(date +%Y%m%d_%H%M%S)
cd /tmp/emergency_backup_*

# Start Weaviate backup in background
nohup /path/to/scripts/backup/backup_weaviate.sh \
  --environment ${ENVIRONMENT} \
  --bucket ${S3_BUCKET} \
  --verbose > weaviate_backup.log 2>&1 &

# Start Redis backup in background
nohup /path/to/scripts/backup/backup_redis.sh \
  --environment ${ENVIRONMENT} \
  --bucket ${S3_BUCKET} \
  --verbose > redis_backup.log 2>&1 &

# Monitor both processes
echo "Monitoring backup processes..."
while pgrep -f "backup_weaviate.sh\|backup_redis.sh" > /dev/null; do
  echo "Backups in progress... $(date)"
  sleep 30
done

echo "Emergency backups completed at $(date)"
```

#### **Step 2: Verify Emergency Backups**
```bash
# Check both backup logs
echo "=== Weaviate Backup Log ==="
tail -20 weaviate_backup.log

echo "=== Redis Backup Log ==="
tail -20 redis_backup.log

# Verify S3 uploads
aws s3 ls s3://${S3_BUCKET}/weaviate/${ENVIRONMENT}/ | tail -2
aws s3 ls s3://${S3_BUCKET}/redis/${ENVIRONMENT}/ | tail -2
```

## 📊 **Backup Validation Procedures**

### **Daily Backup Validation**

#### **Step 1: Automated Validation Script**
```bash
#!/bin/bash
# Daily backup validation script

VALIDATION_DATE=$(date +%Y%m%d)
VALIDATION_LOG="/var/log/backup_validation_${VALIDATION_DATE}.log"

echo "Starting daily backup validation at $(date)" >> ${VALIDATION_LOG}

# Check Weaviate backup
WEAVIATE_BACKUP=$(aws s3 ls s3://${S3_BUCKET}/weaviate/${ENVIRONMENT}/ | tail -1 | awk '{print $4}')
if [[ -n "${WEAVIATE_BACKUP}" ]]; then
  echo "✅ Weaviate backup found: ${WEAVIATE_BACKUP}" >> ${VALIDATION_LOG}
else
  echo "❌ No Weaviate backup found" >> ${VALIDATION_LOG}
fi

# Check Redis backup
REDIS_BACKUP=$(aws s3 ls s3://${S3_BUCKET}/redis/${ENVIRONMENT}/ | tail -1 | awk '{print $4}')
if [[ -n "${REDIS_BACKUP}" ]]; then
  echo "✅ Redis backup found: ${REDIS_BACKUP}" >> ${VALIDATION_LOG}
else
  echo "❌ No Redis backup found" >> ${VALIDATION_LOG}
fi

echo "Backup validation completed at $(date)" >> ${VALIDATION_LOG}
```

### **Weekly Backup Integrity Test**

#### **Step 1: Download and Test Backups**
```bash
#!/bin/bash
# Weekly backup integrity test

TEST_DIR="/tmp/backup_integrity_test_$(date +%Y%m%d)"
mkdir -p ${TEST_DIR}
cd ${TEST_DIR}

# Test Weaviate backup
echo "Testing Weaviate backup integrity..."
aws s3 cp s3://${S3_BUCKET}/weaviate/${ENVIRONMENT}/latest.tar.gz ./
if tar -tzf latest.tar.gz > /dev/null 2>&1; then
  echo "✅ Weaviate backup archive is valid"
else
  echo "❌ Weaviate backup archive is corrupted"
fi

# Test Redis backup
echo "Testing Redis backup integrity..."
aws s3 cp s3://${S3_BUCKET}/redis/${ENVIRONMENT}/latest.tar.gz ./redis-latest.tar.gz
if tar -tzf redis-latest.tar.gz > /dev/null 2>&1; then
  echo "✅ Redis backup archive is valid"
else
  echo "❌ Redis backup archive is corrupted"
fi

# Cleanup
cd /
rm -rf ${TEST_DIR}
```

## 🔍 **Troubleshooting**

### **Common Issues and Solutions**

#### **Issue: Backup Script Fails with Permission Error**
```bash
# Solution: Check file permissions
ls -la /path/to/scripts/backup/
chmod +x /path/to/scripts/backup/*.sh

# Check AWS permissions
aws iam get-user
aws s3 ls s3://${S3_BUCKET} --region ${AWS_REGION}
```

#### **Issue: Weaviate Backup Timeout**
```bash
# Solution: Check Weaviate status and resources
curl -s "${WEAVIATE_URL}/v1/meta" | jq '.'
curl -s "${WEAVIATE_URL}/v1/nodes" | jq '.'

# Check system resources
df -h
free -h
iostat 1 5
```

#### **Issue: Redis Backup Fails**
```bash
# Solution: Check Redis status
redis-cli -h ${REDIS_HOST} -p ${REDIS_PORT} INFO replication
redis-cli -h ${REDIS_HOST} -p ${REDIS_PORT} CONFIG GET save

# Check Redis logs
tail -f /var/log/redis/redis-server.log
```

#### **Issue: S3 Upload Fails**
```bash
# Solution: Check network and AWS credentials
aws sts get-caller-identity
aws s3 ls s3://${S3_BUCKET} --region ${AWS_REGION}

# Test network connectivity
ping s3.${AWS_REGION}.amazonaws.com
curl -I https://s3.${AWS_REGION}.amazonaws.com
```

## 📞 **Escalation Procedures**

### **When to Escalate**
- Backup fails multiple times consecutively
- S3 bucket becomes inaccessible
- Critical system resources are exhausted
- Data corruption is detected in backups

### **Escalation Contacts**
| Issue Type | Primary Contact | Secondary Contact |
|------------|----------------|-------------------|
| Backup Script Issues | DevOps Engineer | Senior Backend Developer |
| S3/AWS Issues | Cloud Infrastructure Team | DevOps Lead |
| Database Issues | Database Administrator | Senior Backend Developer |
| System Resources | System Administrator | DevOps Engineer |

### **Emergency Escalation**
For critical production issues:
1. Create incident in monitoring system
2. Notify on-call engineer via PagerDuty
3. Post in #critical-incidents Slack channel
4. Follow incident response procedures

## 📚 **Additional Resources**

### **Related Documentation**
- [Disaster Recovery Plan](../Disaster_Recovery_Plan.md)
- [DR Testing Runbook](./DR_TESTING.md)
- [Monitoring Setup Guide](../../MONITORING_SETUP_GUIDE.md)

### **Useful Commands Reference**
```bash
# Quick backup status check
aws s3 ls s3://${S3_BUCKET}/ --recursive | grep $(date +%Y%m%d)

# Backup size summary
aws s3api list-objects-v2 --bucket ${S3_BUCKET} --prefix "weaviate/${ENVIRONMENT}/" \
  --query 'sum(Contents[].Size)' --output text | awk '{print $1/1024/1024/1024 " GB"}'

# Latest backup information
aws s3api head-object --bucket ${S3_BUCKET} \
  --key "weaviate/${ENVIRONMENT}/latest.tar.gz" --query 'LastModified'
```

---

**Document Version**: 1.0
**Last Updated**: 2024-12-17
**Next Review**: 2025-01-17
**Approved By**: DevOps Lead

**Classification**: INTERNAL USE ONLY
