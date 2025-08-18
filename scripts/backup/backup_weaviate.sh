#!/bin/bash
# Weaviate Backup Script for GremlinsAI Disaster Recovery
# Phase 4, Task 4.3: Disaster Recovery & Backup
#
# This script creates comprehensive backups of Weaviate vector database
# and uploads them to S3-compatible storage for disaster recovery.
#
# Usage: ./backup_weaviate.sh [options]
# Options:
#   -e, --environment    Environment (dev/staging/prod) [default: prod]
#   -b, --bucket         S3 bucket name [required]
#   -r, --region         AWS region [default: us-east-1]
#   -c, --compress       Enable compression [default: true]
#   -v, --verbose        Verbose output
#   -h, --help           Show this help message

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOG_DIR="${PROJECT_ROOT}/logs/backup"
BACKUP_DIR="${PROJECT_ROOT}/backups/weaviate"

# Default configuration
ENVIRONMENT="prod"
WEAVIATE_URL="${WEAVIATE_URL:-http://localhost:8080}"
WEAVIATE_API_KEY="${WEAVIATE_API_KEY:-}"
S3_BUCKET=""
S3_REGION="us-east-1"
COMPRESS="true"
VERBOSE="false"
RETENTION_DAYS="30"

# Backup metadata
BACKUP_ID="weaviate_$(date +%Y%m%d_%H%M%S)_${ENVIRONMENT}"
BACKUP_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_ID}"

# Logging setup
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/backup_weaviate_$(date +%Y%m%d).log"

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

# Error handling
cleanup() {
    local exit_code=$?
    if [[ ${exit_code} -ne 0 ]]; then
        log_error "Backup failed with exit code ${exit_code}"
        # Clean up partial backup
        if [[ -d "${BACKUP_PATH}" ]]; then
            log_info "Cleaning up partial backup: ${BACKUP_PATH}"
            rm -rf "${BACKUP_PATH}"
        fi
    fi
    exit ${exit_code}
}

trap cleanup EXIT

# Help function
show_help() {
    cat << EOF
Weaviate Backup Script for GremlinsAI Disaster Recovery

USAGE:
    $0 [OPTIONS]

OPTIONS:
    -e, --environment ENV    Environment (dev/staging/prod) [default: prod]
    -b, --bucket BUCKET      S3 bucket name [required]
    -r, --region REGION      AWS region [default: us-east-1]
    -c, --compress BOOL      Enable compression [default: true]
    -v, --verbose            Enable verbose output
    -h, --help               Show this help message

ENVIRONMENT VARIABLES:
    WEAVIATE_URL            Weaviate server URL [default: http://localhost:8080]
    WEAVIATE_API_KEY        Weaviate API key for authentication
    AWS_ACCESS_KEY_ID       AWS access key for S3 upload
    AWS_SECRET_ACCESS_KEY   AWS secret key for S3 upload
    AWS_SESSION_TOKEN       AWS session token (if using temporary credentials)

EXAMPLES:
    # Basic backup to S3
    $0 --bucket gremlinsai-backups

    # Production backup with compression
    $0 --environment prod --bucket gremlinsai-prod-backups --compress true

    # Verbose backup for debugging
    $0 --bucket gremlinsai-dev-backups --verbose

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
            -c|--compress)
                COMPRESS="$2"
                shift 2
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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check required tools
    local required_tools=("curl" "jq" "aws")
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

    # Check Weaviate connectivity
    local health_url="${WEAVIATE_URL}/v1/meta"
    local auth_header=""
    if [[ -n "${WEAVIATE_API_KEY}" ]]; then
        auth_header="-H Authorization: Bearer ${WEAVIATE_API_KEY}"
    fi

    if ! curl -s ${auth_header} "${health_url}" | jq -e '.hostname' &> /dev/null; then
        log_error "Cannot connect to Weaviate at ${WEAVIATE_URL}"
        exit 1
    fi

    log_info "Prerequisites check passed"
}

# Get Weaviate collections
get_collections() {
    log_info "Discovering Weaviate collections..."

    local schema_url="${WEAVIATE_URL}/v1/schema"
    local auth_header=""
    if [[ -n "${WEAVIATE_API_KEY}" ]]; then
        auth_header="-H Authorization: Bearer ${WEAVIATE_API_KEY}"
    fi

    local collections
    collections=$(curl -s ${auth_header} "${schema_url}" | jq -r '.classes[].class' 2>/dev/null || echo "")

    if [[ -z "${collections}" ]]; then
        log_warn "No collections found in Weaviate"
        return 1
    fi

    echo "${collections}"
}

# Create Weaviate backup
create_weaviate_backup() {
    log_info "Creating Weaviate backup: ${BACKUP_ID}"

    # Create backup directory
    mkdir -p "${BACKUP_PATH}"

    # Get collections
    local collections
    collections=$(get_collections)
    if [[ $? -ne 0 ]]; then
        log_error "Failed to get Weaviate collections"
        return 1
    fi

    log_info "Found collections: $(echo ${collections} | tr '\n' ' ')"

    # Create backup using Weaviate backup API
    local backup_url="${WEAVIATE_URL}/v1/backups"
    local auth_header=""
    if [[ -n "${WEAVIATE_API_KEY}" ]]; then
        auth_header="-H Authorization: Bearer ${WEAVIATE_API_KEY}"
    fi

    # Prepare backup request
    local backup_request=$(cat << EOF
{
    "id": "${BACKUP_ID}",
    "include": [$(echo "${collections}" | sed 's/^/"/;s/$/"/;s/\n/", "/g' | tr -d '\n')],
    "exclude": [],
    "config": {
        "CPUPercentage": 80,
        "ChunkSize": 128
    }
}
EOF
)

    log_debug "Backup request: ${backup_request}"

    # Initiate backup
    local backup_response
    backup_response=$(curl -s -X POST ${auth_header} \
        -H "Content-Type: application/json" \
        -d "${backup_request}" \
        "${backup_url}")

    log_debug "Backup response: ${backup_response}"

    # Check if backup was initiated successfully
    local backup_status
    backup_status=$(echo "${backup_response}" | jq -r '.status // "FAILED"')

    if [[ "${backup_status}" != "STARTED" ]]; then
        log_error "Failed to initiate backup. Response: ${backup_response}"
        return 1
    fi

    log_info "Backup initiated successfully"

    # Wait for backup completion
    wait_for_backup_completion "${BACKUP_ID}"
}

# Wait for backup completion
wait_for_backup_completion() {
    local backup_id="$1"
    local status_url="${WEAVIATE_URL}/v1/backups/${backup_id}"
    local auth_header=""
    if [[ -n "${WEAVIATE_API_KEY}" ]]; then
        auth_header="-H Authorization: Bearer ${WEAVIATE_API_KEY}"
    fi

    log_info "Waiting for backup completion..."

    local max_wait=3600  # 1 hour timeout
    local wait_time=0
    local check_interval=30

    while [[ ${wait_time} -lt ${max_wait} ]]; do
        local status_response
        status_response=$(curl -s ${auth_header} "${status_url}")
        
        local status
        status=$(echo "${status_response}" | jq -r '.status // "UNKNOWN"')

        log_debug "Backup status: ${status}"

        case "${status}" in
            "SUCCESS")
                log_info "Backup completed successfully"
                return 0
                ;;
            "FAILED")
                local error
                error=$(echo "${status_response}" | jq -r '.error // "Unknown error"')
                log_error "Backup failed: ${error}"
                return 1
                ;;
            "STARTED"|"TRANSFERRING")
                log_info "Backup in progress... (${status})"
                ;;
            *)
                log_warn "Unknown backup status: ${status}"
                ;;
        esac

        sleep ${check_interval}
        wait_time=$((wait_time + check_interval))
    done

    log_error "Backup timeout after ${max_wait} seconds"
    return 1
}

# Download backup files
download_backup_files() {
    log_info "Downloading backup files..."

    # Weaviate stores backups in its data directory
    # For containerized deployments, we need to copy from the container
    # This is a simplified approach - in production, use Weaviate's backup storage configuration

    local backup_files_url="${WEAVIATE_URL}/v1/backups/${BACKUP_ID}/files"
    local auth_header=""
    if [[ -n "${WEAVIATE_API_KEY}" ]]; then
        auth_header="-H Authorization: Bearer ${WEAVIATE_API_KEY}"
    fi

    # Get backup file list
    local files_response
    files_response=$(curl -s ${auth_header} "${backup_files_url}")
    
    local files
    files=$(echo "${files_response}" | jq -r '.files[]? // empty')

    if [[ -z "${files}" ]]; then
        log_error "No backup files found"
        return 1
    fi

    # Download each file
    echo "${files}" | while read -r file; do
        if [[ -n "${file}" ]]; then
            log_info "Downloading backup file: ${file}"
            curl -s ${auth_header} "${WEAVIATE_URL}/v1/backups/${BACKUP_ID}/files/${file}" \
                -o "${BACKUP_PATH}/${file}"
        fi
    done

    log_info "Backup files downloaded to: ${BACKUP_PATH}"
}

# Create backup metadata
create_backup_metadata() {
    log_info "Creating backup metadata..."

    local metadata_file="${BACKUP_PATH}/backup_metadata.json"
    
    # Get Weaviate version and stats
    local meta_url="${WEAVIATE_URL}/v1/meta"
    local auth_header=""
    if [[ -n "${WEAVIATE_API_KEY}" ]]; then
        auth_header="-H Authorization: Bearer ${WEAVIATE_API_KEY}"
    fi

    local weaviate_meta
    weaviate_meta=$(curl -s ${auth_header} "${meta_url}")

    # Create comprehensive metadata
    cat > "${metadata_file}" << EOF
{
    "backup_id": "${BACKUP_ID}",
    "backup_date": "${BACKUP_DATE}",
    "environment": "${ENVIRONMENT}",
    "weaviate_url": "${WEAVIATE_URL}",
    "weaviate_version": $(echo "${weaviate_meta}" | jq '.version // "unknown"'),
    "hostname": $(echo "${weaviate_meta}" | jq '.hostname // "unknown"'),
    "collections": $(get_collections | jq -R . | jq -s .),
    "backup_size_bytes": $(du -sb "${BACKUP_PATH}" | cut -f1),
    "compression_enabled": ${COMPRESS},
    "retention_days": ${RETENTION_DAYS},
    "created_by": "$(whoami)@$(hostname)",
    "script_version": "1.0.0"
}
EOF

    log_info "Backup metadata created: ${metadata_file}"
}

# Compress backup
compress_backup() {
    if [[ "${COMPRESS}" != "true" ]]; then
        log_info "Compression disabled, skipping..."
        return 0
    fi

    log_info "Compressing backup..."

    local compressed_file="${BACKUP_PATH}.tar.gz"
    
    # Create compressed archive
    tar -czf "${compressed_file}" -C "${BACKUP_DIR}" "${BACKUP_ID}"
    
    if [[ $? -eq 0 ]]; then
        # Remove uncompressed directory
        rm -rf "${BACKUP_PATH}"
        BACKUP_PATH="${compressed_file}"
        log_info "Backup compressed: ${compressed_file}"
    else
        log_error "Compression failed"
        return 1
    fi
}

# Upload to S3
upload_to_s3() {
    log_info "Uploading backup to S3..."

    local s3_key="weaviate/${ENVIRONMENT}/${BACKUP_ID}"
    if [[ "${COMPRESS}" == "true" ]]; then
        s3_key="${s3_key}.tar.gz"
    fi

    local s3_uri="s3://${S3_BUCKET}/${s3_key}"

    # Upload with metadata
    aws s3 cp "${BACKUP_PATH}" "${s3_uri}" \
        --region "${S3_REGION}" \
        --metadata "backup-id=${BACKUP_ID},environment=${ENVIRONMENT},backup-date=${BACKUP_DATE}" \
        --storage-class STANDARD_IA

    if [[ $? -eq 0 ]]; then
        log_info "Backup uploaded successfully: ${s3_uri}"
        
        # Create latest symlink
        local latest_key="weaviate/${ENVIRONMENT}/latest"
        if [[ "${COMPRESS}" == "true" ]]; then
            latest_key="${latest_key}.tar.gz"
        fi
        
        aws s3 cp "${s3_uri}" "s3://${S3_BUCKET}/${latest_key}" \
            --region "${S3_REGION}" \
            --metadata-directive COPY
        
        log_info "Latest backup link updated"
    else
        log_error "Failed to upload backup to S3"
        return 1
    fi
}

# Cleanup old backups
cleanup_old_backups() {
    log_info "Cleaning up old backups..."

    # Clean up local backups older than 7 days
    find "${BACKUP_DIR}" -name "weaviate_*" -type f -mtime +7 -delete 2>/dev/null || true
    find "${BACKUP_DIR}" -name "weaviate_*" -type d -mtime +7 -exec rm -rf {} + 2>/dev/null || true

    # Clean up S3 backups older than retention period
    local cutoff_date
    cutoff_date=$(date -u -d "${RETENTION_DAYS} days ago" +%Y-%m-%d)

    aws s3api list-objects-v2 \
        --bucket "${S3_BUCKET}" \
        --prefix "weaviate/${ENVIRONMENT}/" \
        --query "Contents[?LastModified<='${cutoff_date}'].Key" \
        --output text | \
    while read -r key; do
        if [[ -n "${key}" && "${key}" != "None" ]]; then
            log_info "Deleting old backup: s3://${S3_BUCKET}/${key}"
            aws s3 rm "s3://${S3_BUCKET}/${key}" --region "${S3_REGION}"
        fi
    done

    log_info "Cleanup completed"
}

# Main execution
main() {
    log_info "Starting Weaviate backup process..."
    log_info "Backup ID: ${BACKUP_ID}"

    parse_args "$@"
    check_prerequisites
    create_weaviate_backup
    download_backup_files
    create_backup_metadata
    compress_backup
    upload_to_s3
    cleanup_old_backups

    local backup_size
    if [[ -f "${BACKUP_PATH}" ]]; then
        backup_size=$(du -sh "${BACKUP_PATH}" | cut -f1)
    else
        backup_size="unknown"
    fi

    log_info "Weaviate backup completed successfully!"
    log_info "Backup ID: ${BACKUP_ID}"
    log_info "Backup Size: ${backup_size}"
    log_info "S3 Location: s3://${S3_BUCKET}/weaviate/${ENVIRONMENT}/${BACKUP_ID}"
    
    # Clean up local backup file
    if [[ -f "${BACKUP_PATH}" ]]; then
        rm -f "${BACKUP_PATH}"
        log_info "Local backup file cleaned up"
    fi
}

# Execute main function
main "$@"
