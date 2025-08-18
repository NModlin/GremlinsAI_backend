#!/bin/bash
# Full System Restoration Script for GremlinsAI Disaster Recovery
# Phase 4, Task 4.3: Disaster Recovery & Backup
#
# This script automates the complete restoration of GremlinsAI from backups
# stored in S3-compatible storage. It handles both Weaviate and Redis restoration
# with comprehensive validation and rollback capabilities.
#
# Usage: ./full_restore.sh [options]
# Options:
#   -e, --environment    Environment (dev/staging/prod) [default: prod]
#   -b, --bucket         S3 bucket name [required]
#   -r, --region         AWS region [default: us-east-1]
#   -d, --backup-date    Specific backup date (YYYYMMDD_HHMMSS) [default: latest]
#   -t, --test-mode      Test mode (no actual restoration) [default: false]
#   -v, --verbose        Verbose output
#   -h, --help           Show this help message

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOG_DIR="${PROJECT_ROOT}/logs/restore"
RESTORE_DIR="${PROJECT_ROOT}/restore"

# Default configuration
ENVIRONMENT="prod"
S3_BUCKET=""
S3_REGION="us-east-1"
BACKUP_DATE="latest"
TEST_MODE="false"
VERBOSE="false"

# Service endpoints
WEAVIATE_URL="${WEAVIATE_URL:-http://localhost:8080}"
REDIS_URL="${REDIS_URL:-redis://localhost:6379}"
APP_URL="${APP_URL:-http://localhost:8000}"

# Restoration metadata
RESTORE_ID="restore_$(date +%Y%m%d_%H%M%S)_${ENVIRONMENT}"
RESTORE_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RESTORE_PATH="${RESTORE_DIR}/${RESTORE_ID}"

# Logging setup
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/full_restore_$(date +%Y%m%d).log"

# Logging functions
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "[${timestamp}] [${level}] ${message}" | tee -a "${LOG_FILE}"
}

log_info() { log "INFO" "$@"; }
log_warn() { log "WARN" "$@"; }
log_error() { log "ERROR" "$@"; }
log_debug() { [[ "${VERBOSE}" == "true" ]] && log "DEBUG" "$@" || true; }
log_success() { log "SUCCESS" "$@"; }

# Progress tracking
TOTAL_STEPS=12
CURRENT_STEP=0

progress() {
    CURRENT_STEP=$((CURRENT_STEP + 1))
    local message="$1"
    log_info "Step ${CURRENT_STEP}/${TOTAL_STEPS}: ${message}"
}

# Error handling
cleanup() {
    local exit_code=$?
    if [[ ${exit_code} -ne 0 ]]; then
        log_error "Restoration failed with exit code ${exit_code}"
        log_error "Check logs for details: ${LOG_FILE}"
        
        # Cleanup partial restoration
        if [[ -d "${RESTORE_PATH}" ]]; then
            log_info "Cleaning up partial restoration: ${RESTORE_PATH}"
            rm -rf "${RESTORE_PATH}"
        fi
        
        # Send failure notification
        send_notification "FAILURE" "Restoration failed at step ${CURRENT_STEP}/${TOTAL_STEPS}"
    else
        log_success "Restoration completed successfully!"
        send_notification "SUCCESS" "Full system restoration completed"
    fi
    exit ${exit_code}
}

trap cleanup EXIT

# Help function
show_help() {
    cat << EOF
Full System Restoration Script for GremlinsAI Disaster Recovery

USAGE:
    $0 [OPTIONS]

OPTIONS:
    -e, --environment ENV    Environment (dev/staging/prod) [default: prod]
    -b, --bucket BUCKET      S3 bucket name [required]
    -r, --region REGION      AWS region [default: us-east-1]
    -d, --backup-date DATE   Specific backup date (YYYYMMDD_HHMMSS) [default: latest]
    -t, --test-mode          Test mode (no actual restoration) [default: false]
    -v, --verbose            Enable verbose output
    -h, --help               Show this help message

ENVIRONMENT VARIABLES:
    WEAVIATE_URL            Weaviate server URL [default: http://localhost:8080]
    REDIS_URL               Redis connection URL [default: redis://localhost:6379]
    APP_URL                 Application URL [default: http://localhost:8000]
    AWS_ACCESS_KEY_ID       AWS access key for S3 access
    AWS_SECRET_ACCESS_KEY   AWS secret key for S3 access
    SLACK_WEBHOOK_URL       Slack webhook for notifications

EXAMPLES:
    # Restore latest production backup
    $0 --bucket gremlinsai-prod-backups --environment prod

    # Restore specific backup in test mode
    $0 --bucket gremlinsai-backups --backup-date 20241201_143000 --test-mode

    # Verbose restoration for debugging
    $0 --bucket gremlinsai-dev-backups --environment dev --verbose

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -b|--bucket)
                S3_BUCKET="$2"
                shift 2
                ;;
            -r|--region)
                S3_REGION="$2"
                shift 2
                ;;
            -d|--backup-date)
                BACKUP_DATE="$2"
                shift 2
                ;;
            -t|--test-mode)
                TEST_MODE="true"
                shift
                ;;
            -v|--verbose)
                VERBOSE="true"
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # Validate required parameters
    if [[ -z "${S3_BUCKET}" ]]; then
        log_error "S3 bucket name is required. Use --bucket option."
        exit 1
    fi
}

# Send notification
send_notification() {
    local status="$1"
    local message="$2"
    
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        local color="good"
        local icon=":white_check_mark:"
        
        if [[ "${status}" == "FAILURE" ]]; then
            color="danger"
            icon=":x:"
        elif [[ "${status}" == "WARNING" ]]; then
            color="warning"
            icon=":warning:"
        fi
        
        curl -X POST "${SLACK_WEBHOOK_URL}" \
            -H 'Content-type: application/json' \
            --data "{
                \"attachments\": [{
                    \"color\": \"${color}\",
                    \"title\": \"${icon} GremlinsAI Disaster Recovery\",
                    \"text\": \"${message}\",
                    \"fields\": [
                        {\"title\": \"Environment\", \"value\": \"${ENVIRONMENT}\", \"short\": true},
                        {\"title\": \"Restore ID\", \"value\": \"${RESTORE_ID}\", \"short\": true},
                        {\"title\": \"Timestamp\", \"value\": \"${RESTORE_DATE}\", \"short\": true}
                    ]
                }]
            }" 2>/dev/null || true
    fi
}

# Check prerequisites
check_prerequisites() {
    progress "Checking prerequisites and connectivity"

    # Check required tools
    local required_tools=("curl" "jq" "aws" "kubectl")
    for tool in "${required_tools[@]}"; do
        if ! command -v "${tool}" &> /dev/null; then
            log_error "Required tool not found: ${tool}"
            exit 1
        fi
    done

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured or invalid"
        exit 1
    fi

    # Check S3 bucket access
    if ! aws s3 ls "s3://${S3_BUCKET}" &> /dev/null; then
        log_error "Cannot access S3 bucket: ${S3_BUCKET}"
        exit 1
    fi

    # Check service connectivity (if not in test mode)
    if [[ "${TEST_MODE}" != "true" ]]; then
        # Check Weaviate
        if ! curl -s "${WEAVIATE_URL}/v1/meta" | jq -e '.hostname' &> /dev/null; then
            log_error "Cannot connect to Weaviate at ${WEAVIATE_URL}"
            exit 1
        fi

        # Check Redis
        local redis_host=$(echo "${REDIS_URL}" | sed 's|redis://||' | cut -d: -f1)
        local redis_port=$(echo "${REDIS_URL}" | sed 's|redis://||' | cut -d: -f2)
        redis_port=${redis_port:-6379}
        
        if ! redis-cli -h "${redis_host}" -p "${redis_port}" ping | grep -q "PONG"; then
            log_error "Cannot connect to Redis at ${redis_host}:${redis_port}"
            exit 1
        fi
    fi

    log_success "Prerequisites check passed"
}

# Discover available backups
discover_backups() {
    progress "Discovering available backups"

    # Create restore directory
    mkdir -p "${RESTORE_PATH}"

    # List available backups
    log_info "Scanning for Weaviate backups..."
    local weaviate_backups
    weaviate_backups=$(aws s3 ls "s3://${S3_BUCKET}/weaviate/${ENVIRONMENT}/" --region "${S3_REGION}" | grep -v "latest" | awk '{print $4}' | sort -r)

    log_info "Scanning for Redis backups..."
    local redis_backups
    redis_backups=$(aws s3 ls "s3://${S3_BUCKET}/redis/${ENVIRONMENT}/" --region "${S3_REGION}" | grep -v "latest" | awk '{print $4}' | sort -r)

    log_debug "Available Weaviate backups: $(echo ${weaviate_backups} | tr '\n' ' ')"
    log_debug "Available Redis backups: $(echo ${redis_backups} | tr '\n' ' ')"

    # Determine backup files to restore
    if [[ "${BACKUP_DATE}" == "latest" ]]; then
        WEAVIATE_BACKUP_FILE="latest.tar.gz"
        REDIS_BACKUP_FILE="latest.tar.gz"
    else
        WEAVIATE_BACKUP_FILE="weaviate_${BACKUP_DATE}_${ENVIRONMENT}.tar.gz"
        REDIS_BACKUP_FILE="redis_${BACKUP_DATE}_${ENVIRONMENT}.tar.gz"
    fi

    log_info "Selected Weaviate backup: ${WEAVIATE_BACKUP_FILE}"
    log_info "Selected Redis backup: ${REDIS_BACKUP_FILE}"
}

# Download backups from S3
download_backups() {
    progress "Downloading backups from S3"

    # Download Weaviate backup
    log_info "Downloading Weaviate backup..."
    local weaviate_s3_path="s3://${S3_BUCKET}/weaviate/${ENVIRONMENT}/${WEAVIATE_BACKUP_FILE}"
    local weaviate_local_path="${RESTORE_PATH}/weaviate-backup.tar.gz"

    aws s3 cp "${weaviate_s3_path}" "${weaviate_local_path}" --region "${S3_REGION}"
    
    if [[ $? -ne 0 ]]; then
        log_error "Failed to download Weaviate backup from ${weaviate_s3_path}"
        exit 1
    fi

    # Download Redis backup
    log_info "Downloading Redis backup..."
    local redis_s3_path="s3://${S3_BUCKET}/redis/${ENVIRONMENT}/${REDIS_BACKUP_FILE}"
    local redis_local_path="${RESTORE_PATH}/redis-backup.tar.gz"

    aws s3 cp "${redis_s3_path}" "${redis_local_path}" --region "${S3_REGION}"
    
    if [[ $? -ne 0 ]]; then
        log_error "Failed to download Redis backup from ${redis_s3_path}"
        exit 1
    fi

    log_success "Backups downloaded successfully"
}

# Extract backups
extract_backups() {
    progress "Extracting backup archives"

    # Extract Weaviate backup
    log_info "Extracting Weaviate backup..."
    tar -xzf "${RESTORE_PATH}/weaviate-backup.tar.gz" -C "${RESTORE_PATH}"
    
    if [[ $? -ne 0 ]]; then
        log_error "Failed to extract Weaviate backup"
        exit 1
    fi

    # Extract Redis backup
    log_info "Extracting Redis backup..."
    tar -xzf "${RESTORE_PATH}/redis-backup.tar.gz" -C "${RESTORE_PATH}"
    
    if [[ $? -ne 0 ]]; then
        log_error "Failed to extract Redis backup"
        exit 1
    fi

    # Verify extracted contents
    local weaviate_backup_dir=$(find "${RESTORE_PATH}" -name "weaviate_*" -type d | head -1)
    local redis_backup_dir=$(find "${RESTORE_PATH}" -name "redis_*" -type d | head -1)

    if [[ ! -d "${weaviate_backup_dir}" ]]; then
        log_error "Weaviate backup directory not found after extraction"
        exit 1
    fi

    if [[ ! -d "${redis_backup_dir}" ]]; then
        log_error "Redis backup directory not found after extraction"
        exit 1
    fi

    log_success "Backups extracted successfully"
    log_info "Weaviate backup: ${weaviate_backup_dir}"
    log_info "Redis backup: ${redis_backup_dir}"
}

# Validate backup integrity
validate_backups() {
    progress "Validating backup integrity"

    # Find backup directories
    local weaviate_backup_dir=$(find "${RESTORE_PATH}" -name "weaviate_*" -type d | head -1)
    local redis_backup_dir=$(find "${RESTORE_PATH}" -name "redis_*" -type d | head -1)

    # Validate Weaviate backup
    log_info "Validating Weaviate backup integrity..."
    local weaviate_metadata="${weaviate_backup_dir}/backup_metadata.json"
    
    if [[ ! -f "${weaviate_metadata}" ]]; then
        log_error "Weaviate backup metadata not found: ${weaviate_metadata}"
        exit 1
    fi

    local weaviate_backup_id=$(jq -r '.backup_id' "${weaviate_metadata}")
    local weaviate_collections=$(jq -r '.collections[]' "${weaviate_metadata}" 2>/dev/null | wc -l)
    
    log_info "Weaviate backup ID: ${weaviate_backup_id}"
    log_info "Weaviate collections: ${weaviate_collections}"

    # Validate Redis backup
    log_info "Validating Redis backup integrity..."
    local redis_metadata="${redis_backup_dir}/backup_metadata.json"
    
    if [[ ! -f "${redis_metadata}" ]]; then
        log_error "Redis backup metadata not found: ${redis_metadata}"
        exit 1
    fi

    local redis_backup_id=$(jq -r '.backup_id' "${redis_metadata}")
    local redis_backup_type=$(jq -r '.backup_type' "${redis_metadata}")
    
    log_info "Redis backup ID: ${redis_backup_id}"
    log_info "Redis backup type: ${redis_backup_type}"

    # Check for required backup files
    case "${redis_backup_type}" in
        "rdb"|"both")
            if [[ ! -f "${redis_backup_dir}/dump.rdb" ]]; then
                log_error "Redis RDB file not found in backup"
                exit 1
            fi
            ;;
    esac

    case "${redis_backup_type}" in
        "aof"|"both")
            if [[ ! -f "${redis_backup_dir}/appendonly.aof" ]]; then
                log_error "Redis AOF file not found in backup"
                exit 1
            fi
            ;;
    esac

    log_success "Backup integrity validation passed"
}

# Pre-restoration system check
pre_restoration_check() {
    progress "Performing pre-restoration system check"

    if [[ "${TEST_MODE}" == "true" ]]; then
        log_info "Test mode enabled - skipping actual system checks"
        return 0
    fi

    # Check system resources
    log_info "Checking system resources..."
    
    # Check disk space
    local available_space=$(df "${RESTORE_PATH}" | awk 'NR==2 {print $4}')
    local required_space=10485760  # 10GB in KB
    
    if [[ ${available_space} -lt ${required_space} ]]; then
        log_error "Insufficient disk space. Required: 10GB, Available: $((available_space/1024/1024))GB"
        exit 1
    fi

    # Check memory
    local available_memory=$(free -m | awk 'NR==2{print $7}')
    local required_memory=2048  # 2GB in MB
    
    if [[ ${available_memory} -lt ${required_memory} ]]; then
        log_warn "Low available memory. Required: 2GB, Available: ${available_memory}MB"
    fi

    # Check service status
    log_info "Checking service status..."
    
    # Stop application services to prevent conflicts
    if command -v kubectl &> /dev/null; then
        log_info "Scaling down application services..."
        kubectl scale deployment gremlinsai-app --replicas=0 -n gremlinsai 2>/dev/null || true
        sleep 10
    fi

    log_success "Pre-restoration check completed"
}

# Restore Weaviate data
restore_weaviate() {
    progress "Restoring Weaviate data"

    if [[ "${TEST_MODE}" == "true" ]]; then
        log_info "Test mode - simulating Weaviate restoration"
        sleep 2
        return 0
    fi

    local weaviate_backup_dir=$(find "${RESTORE_PATH}" -name "weaviate_*" -type d | head -1)
    
    # Execute Weaviate restoration script
    log_info "Executing Weaviate restoration..."
    
    "${SCRIPT_DIR}/restore_weaviate.sh" \
        --backup-path "${weaviate_backup_dir}" \
        --weaviate-url "${WEAVIATE_URL}" \
        --environment "${ENVIRONMENT}" \
        $([ "${VERBOSE}" == "true" ] && echo "--verbose")

    if [[ $? -ne 0 ]]; then
        log_error "Weaviate restoration failed"
        exit 1
    fi

    log_success "Weaviate data restored successfully"
}

# Restore Redis data
restore_redis() {
    progress "Restoring Redis data"

    if [[ "${TEST_MODE}" == "true" ]]; then
        log_info "Test mode - simulating Redis restoration"
        sleep 2
        return 0
    fi

    local redis_backup_dir=$(find "${RESTORE_PATH}" -name "redis_*" -type d | head -1)
    
    # Execute Redis restoration script
    log_info "Executing Redis restoration..."
    
    "${SCRIPT_DIR}/restore_redis.sh" \
        --backup-path "${redis_backup_dir}" \
        --redis-url "${REDIS_URL}" \
        --environment "${ENVIRONMENT}" \
        $([ "${VERBOSE}" == "true" ] && echo "--verbose")

    if [[ $? -ne 0 ]]; then
        log_error "Redis restoration failed"
        exit 1
    fi

    log_success "Redis data restored successfully"
}

# Restart application services
restart_services() {
    progress "Restarting application services"

    if [[ "${TEST_MODE}" == "true" ]]; then
        log_info "Test mode - simulating service restart"
        sleep 2
        return 0
    fi

    # Restart application services
    if command -v kubectl &> /dev/null; then
        log_info "Scaling up application services..."
        kubectl scale deployment gremlinsai-app --replicas=3 -n gremlinsai
        
        # Wait for deployment to be ready
        log_info "Waiting for services to be ready..."
        kubectl rollout status deployment/gremlinsai-app -n gremlinsai --timeout=300s
        
        if [[ $? -ne 0 ]]; then
            log_error "Application services failed to start"
            exit 1
        fi
    else
        log_info "Kubernetes not available - manual service restart required"
    fi

    log_success "Application services restarted successfully"
}

# Validate restoration
validate_restoration() {
    progress "Validating system restoration"

    if [[ "${TEST_MODE}" == "true" ]]; then
        log_info "Test mode - simulating validation"
        sleep 2
        return 0
    fi

    # Wait for services to be fully ready
    log_info "Waiting for services to be fully operational..."
    sleep 30

    # Health check
    log_info "Performing health checks..."
    
    local health_check_url="${APP_URL}/api/v1/health"
    local max_attempts=10
    local attempt=1

    while [[ ${attempt} -le ${max_attempts} ]]; do
        if curl -f -s "${health_check_url}" | jq -e '.status == "healthy"' &> /dev/null; then
            log_success "Health check passed"
            break
        fi
        
        log_info "Health check attempt ${attempt}/${max_attempts} failed, retrying..."
        sleep 30
        attempt=$((attempt + 1))
    done

    if [[ ${attempt} -gt ${max_attempts} ]]; then
        log_error "Health check failed after ${max_attempts} attempts"
        exit 1
    fi

    # Database connectivity check
    log_info "Checking database connectivity..."
    
    local db_check_url="${APP_URL}/api/v1/health/database"
    if ! curl -f -s "${db_check_url}" | jq -e '.weaviate.status == "connected"' &> /dev/null; then
        log_error "Weaviate connectivity check failed"
        exit 1
    fi

    if ! curl -f -s "${db_check_url}" | jq -e '.redis.status == "connected"' &> /dev/null; then
        log_error "Redis connectivity check failed"
        exit 1
    fi

    # Functional validation
    log_info "Performing functional validation..."
    
    # Test RAG query
    local rag_test_url="${APP_URL}/api/v1/rag/query"
    local test_query='{"query": "test query", "top_k": 1}'
    
    if ! curl -f -s -X POST -H "Content-Type: application/json" -d "${test_query}" "${rag_test_url}" &> /dev/null; then
        log_warn "RAG functionality test failed - may need data reindexing"
    else
        log_success "RAG functionality validated"
    fi

    log_success "System restoration validation completed"
}

# Generate restoration report
generate_report() {
    progress "Generating restoration report"

    local report_file="${RESTORE_PATH}/restoration_report.json"
    local end_time="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    
    # Calculate restoration duration
    local start_timestamp=$(date -d "${RESTORE_DATE}" +%s)
    local end_timestamp=$(date -d "${end_time}" +%s)
    local duration=$((end_timestamp - start_timestamp))

    # Create restoration report
    cat > "${report_file}" << EOF
{
    "restore_id": "${RESTORE_ID}",
    "environment": "${ENVIRONMENT}",
    "start_time": "${RESTORE_DATE}",
    "end_time": "${end_time}",
    "duration_seconds": ${duration},
    "duration_human": "$(date -u -d @${duration} +%H:%M:%S)",
    "backup_date": "${BACKUP_DATE}",
    "s3_bucket": "${S3_BUCKET}",
    "test_mode": ${TEST_MODE},
    "weaviate_backup": "${WEAVIATE_BACKUP_FILE}",
    "redis_backup": "${REDIS_BACKUP_FILE}",
    "status": "SUCCESS",
    "steps_completed": ${CURRENT_STEP},
    "total_steps": ${TOTAL_STEPS},
    "restored_by": "$(whoami)@$(hostname)",
    "script_version": "1.0.0"
}
EOF

    log_info "Restoration report generated: ${report_file}"
    
    # Display summary
    log_success "=== RESTORATION SUMMARY ==="
    log_success "Restore ID: ${RESTORE_ID}"
    log_success "Environment: ${ENVIRONMENT}"
    log_success "Duration: $(date -u -d @${duration} +%H:%M:%S)"
    log_success "Status: SUCCESS"
    log_success "=========================="
}

# Main execution
main() {
    log_info "Starting GremlinsAI full system restoration..."
    log_info "Restore ID: ${RESTORE_ID}"
    
    # Send start notification
    send_notification "INFO" "Full system restoration started"

    parse_args "$@"
    check_prerequisites
    discover_backups
    download_backups
    extract_backups
    validate_backups
    pre_restoration_check
    restore_weaviate
    restore_redis
    restart_services
    validate_restoration
    generate_report

    log_success "GremlinsAI full system restoration completed successfully!"
    log_info "Total restoration time: $(date -u -d @$(($(date +%s) - $(date -d "${RESTORE_DATE}" +%s))) +%H:%M:%S)"
    log_info "Restoration report: ${RESTORE_PATH}/restoration_report.json"
    
    # Cleanup temporary files
    if [[ "${TEST_MODE}" != "true" ]]; then
        log_info "Cleaning up temporary files..."
        rm -f "${RESTORE_PATH}"/*.tar.gz
    fi
}

# Execute main function
main "$@"
