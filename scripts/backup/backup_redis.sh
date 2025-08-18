#!/bin/bash
# Redis Backup Script for GremlinsAI Disaster Recovery
# Phase 4, Task 4.3: Disaster Recovery & Backup
#
# This script creates comprehensive backups of Redis cache and session data
# and uploads them to S3-compatible storage for disaster recovery.
#
# Usage: ./backup_redis.sh [options]
# Options:
#   -e, --environment    Environment (dev/staging/prod) [default: prod]
#   -b, --bucket         S3 bucket name [required]
#   -r, --region         AWS region [default: us-east-1]
#   -t, --type           Backup type (rdb/aof/both) [default: both]
#   -c, --compress       Enable compression [default: true]
#   -v, --verbose        Verbose output
#   -h, --help           Show this help message

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOG_DIR="${PROJECT_ROOT}/logs/backup"
BACKUP_DIR="${PROJECT_ROOT}/backups/redis"

# Default configuration
ENVIRONMENT="prod"
REDIS_URL="${REDIS_URL:-redis://localhost:6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"
S3_BUCKET=""
S3_REGION="us-east-1"
BACKUP_TYPE="both"  # rdb, aof, or both
COMPRESS="true"
VERBOSE="false"
RETENTION_DAYS="30"

# Parse Redis URL
REDIS_HOST="localhost"
REDIS_PORT="6379"
REDIS_DB="0"

# Backup metadata
BACKUP_ID="redis_$(date +%Y%m%d_%H%M%S)_${ENVIRONMENT}"
BACKUP_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_ID}"

# Logging setup
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/backup_redis_$(date +%Y%m%d).log"

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
Redis Backup Script for GremlinsAI Disaster Recovery

USAGE:
    $0 [OPTIONS]

OPTIONS:
    -e, --environment ENV    Environment (dev/staging/prod) [default: prod]
    -b, --bucket BUCKET      S3 bucket name [required]
    -r, --region REGION      AWS region [default: us-east-1]
    -t, --type TYPE          Backup type (rdb/aof/both) [default: both]
    -c, --compress BOOL      Enable compression [default: true]
    -v, --verbose            Enable verbose output
    -h, --help               Show this help message

ENVIRONMENT VARIABLES:
    REDIS_URL               Redis connection URL [default: redis://localhost:6379]
    REDIS_PASSWORD          Redis password for authentication
    AWS_ACCESS_KEY_ID       AWS access key for S3 upload
    AWS_SECRET_ACCESS_KEY   AWS secret key for S3 upload
    AWS_SESSION_TOKEN       AWS session token (if using temporary credentials)

BACKUP TYPES:
    rdb     - Redis Database file (point-in-time snapshot)
    aof     - Append Only File (transaction log)
    both    - Both RDB and AOF files [default]

EXAMPLES:
    # Basic backup to S3
    $0 --bucket gremlinsai-backups

    # Production RDB backup only
    $0 --environment prod --bucket gremlinsai-prod-backups --type rdb

    # Verbose backup with AOF
    $0 --bucket gremlinsai-dev-backups --type aof --verbose

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
            -t|--type)
                BACKUP_TYPE="$2"
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

    # Validate backup type
    if [[ ! "${BACKUP_TYPE}" =~ ^(rdb|aof|both)$ ]]; then
        log_error "Invalid backup type: ${BACKUP_TYPE}. Must be rdb, aof, or both."
        exit 1
    fi
}

# Parse Redis URL
parse_redis_url() {
    log_debug "Parsing Redis URL: ${REDIS_URL}"

    # Extract components from Redis URL
    if [[ "${REDIS_URL}" =~ redis://([^:@]*:?[^@]*@)?([^:]+):?([0-9]+)?/?([0-9]+)? ]]; then
        local auth="${BASH_REMATCH[1]}"
        REDIS_HOST="${BASH_REMATCH[2]}"
        REDIS_PORT="${BASH_REMATCH[3]:-6379}"
        REDIS_DB="${BASH_REMATCH[4]:-0}"

        # Extract password from auth if present
        if [[ -n "${auth}" && "${auth}" != *"@" ]]; then
            REDIS_PASSWORD="${auth%@*}"
            if [[ "${REDIS_PASSWORD}" == *":"* ]]; then
                REDIS_PASSWORD="${REDIS_PASSWORD#*:}"
            fi
        fi
    fi

    log_debug "Redis connection: ${REDIS_HOST}:${REDIS_PORT} DB:${REDIS_DB}"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check required tools
    local required_tools=("redis-cli" "aws")
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

    # Check Redis connectivity
    local redis_cmd="redis-cli -h ${REDIS_HOST} -p ${REDIS_PORT}"
    if [[ -n "${REDIS_PASSWORD}" ]]; then
        redis_cmd="${redis_cmd} -a ${REDIS_PASSWORD}"
    fi

    if ! ${redis_cmd} ping | grep -q "PONG"; then
        log_error "Cannot connect to Redis at ${REDIS_HOST}:${REDIS_PORT}"
        exit 1
    fi

    log_info "Prerequisites check passed"
}

# Get Redis info
get_redis_info() {
    local redis_cmd="redis-cli -h ${REDIS_HOST} -p ${REDIS_PORT}"
    if [[ -n "${REDIS_PASSWORD}" ]]; then
        redis_cmd="${redis_cmd} -a ${REDIS_PASSWORD}"
    fi

    ${redis_cmd} INFO
}

# Create RDB backup
create_rdb_backup() {
    log_info "Creating RDB backup..."

    local redis_cmd="redis-cli -h ${REDIS_HOST} -p ${REDIS_PORT}"
    if [[ -n "${REDIS_PASSWORD}" ]]; then
        redis_cmd="${redis_cmd} -a ${REDIS_PASSWORD}"
    fi

    # Trigger BGSAVE for non-blocking backup
    local save_result
    save_result=$(${redis_cmd} BGSAVE)

    if [[ "${save_result}" != "Background saving started" ]]; then
        log_error "Failed to start RDB backup: ${save_result}"
        return 1
    fi

    log_info "RDB background save started"

    # Wait for backup completion
    local max_wait=1800  # 30 minutes timeout
    local wait_time=0
    local check_interval=5

    while [[ ${wait_time} -lt ${max_wait} ]]; do
        local last_save
        last_save=$(${redis_cmd} LASTSAVE)
        
        local current_save
        current_save=$(${redis_cmd} LASTSAVE)

        # Check if BGSAVE is still running
        local bgsave_status
        bgsave_status=$(${redis_cmd} INFO persistence | grep "rdb_bgsave_in_progress:0" || echo "")

        if [[ -n "${bgsave_status}" ]]; then
            log_info "RDB backup completed"
            break
        fi

        log_debug "RDB backup in progress..."
        sleep ${check_interval}
        wait_time=$((wait_time + check_interval))
    done

    if [[ ${wait_time} -ge ${max_wait} ]]; then
        log_error "RDB backup timeout after ${max_wait} seconds"
        return 1
    fi

    # Get RDB file location
    local rdb_dir
    rdb_dir=$(${redis_cmd} CONFIG GET dir | tail -n 1)
    
    local rdb_filename
    rdb_filename=$(${redis_cmd} CONFIG GET dbfilename | tail -n 1)

    local rdb_path="${rdb_dir}/${rdb_filename}"
    
    log_debug "RDB file location: ${rdb_path}"

    # Copy RDB file to backup directory
    if [[ -f "${rdb_path}" ]]; then
        cp "${rdb_path}" "${BACKUP_PATH}/dump.rdb"
        log_info "RDB file copied to backup directory"
    else
        log_error "RDB file not found: ${rdb_path}"
        return 1
    fi
}

# Create AOF backup
create_aof_backup() {
    log_info "Creating AOF backup..."

    local redis_cmd="redis-cli -h ${REDIS_HOST} -p ${REDIS_PORT}"
    if [[ -n "${REDIS_PASSWORD}" ]]; then
        redis_cmd="${redis_cmd} -a ${REDIS_PASSWORD}"
    fi

    # Check if AOF is enabled
    local aof_enabled
    aof_enabled=$(${redis_cmd} CONFIG GET appendonly | tail -n 1)

    if [[ "${aof_enabled}" != "yes" ]]; then
        log_warn "AOF is not enabled, enabling temporarily for backup"
        ${redis_cmd} CONFIG SET appendonly yes
        sleep 2  # Allow AOF to initialize
    fi

    # Trigger AOF rewrite for clean backup
    local rewrite_result
    rewrite_result=$(${redis_cmd} BGREWRITEAOF)

    if [[ "${rewrite_result}" != "Background append only file rewriting started" ]]; then
        log_error "Failed to start AOF rewrite: ${rewrite_result}"
        return 1
    fi

    log_info "AOF background rewrite started"

    # Wait for rewrite completion
    local max_wait=1800  # 30 minutes timeout
    local wait_time=0
    local check_interval=5

    while [[ ${wait_time} -lt ${max_wait} ]]; do
        # Check if AOF rewrite is still running
        local aof_rewrite_status
        aof_rewrite_status=$(${redis_cmd} INFO persistence | grep "aof_rewrite_in_progress:0" || echo "")

        if [[ -n "${aof_rewrite_status}" ]]; then
            log_info "AOF rewrite completed"
            break
        fi

        log_debug "AOF rewrite in progress..."
        sleep ${check_interval}
        wait_time=$((wait_time + check_interval))
    done

    if [[ ${wait_time} -ge ${max_wait} ]]; then
        log_error "AOF rewrite timeout after ${max_wait} seconds"
        return 1
    fi

    # Get AOF file location
    local aof_dir
    aof_dir=$(${redis_cmd} CONFIG GET dir | tail -n 1)
    
    local aof_filename
    aof_filename=$(${redis_cmd} CONFIG GET appendfilename | tail -n 1)

    local aof_path="${aof_dir}/${aof_filename}"
    
    log_debug "AOF file location: ${aof_path}"

    # Copy AOF file to backup directory
    if [[ -f "${aof_path}" ]]; then
        cp "${aof_path}" "${BACKUP_PATH}/appendonly.aof"
        log_info "AOF file copied to backup directory"
    else
        log_error "AOF file not found: ${aof_path}"
        return 1
    fi

    # Restore original AOF setting if it was disabled
    if [[ "${aof_enabled}" != "yes" ]]; then
        log_info "Restoring original AOF setting"
        ${redis_cmd} CONFIG SET appendonly no
    fi
}

# Create backup metadata
create_backup_metadata() {
    log_info "Creating backup metadata..."

    local metadata_file="${BACKUP_PATH}/backup_metadata.json"
    
    # Get Redis info
    local redis_info
    redis_info=$(get_redis_info)

    # Extract key information
    local redis_version
    redis_version=$(echo "${redis_info}" | grep "redis_version:" | cut -d: -f2 | tr -d '\r')

    local used_memory
    used_memory=$(echo "${redis_info}" | grep "used_memory:" | cut -d: -f2 | tr -d '\r')

    local connected_clients
    connected_clients=$(echo "${redis_info}" | grep "connected_clients:" | cut -d: -f2 | tr -d '\r')

    local total_commands_processed
    total_commands_processed=$(echo "${redis_info}" | grep "total_commands_processed:" | cut -d: -f2 | tr -d '\r')

    # Create comprehensive metadata
    cat > "${metadata_file}" << EOF
{
    "backup_id": "${BACKUP_ID}",
    "backup_date": "${BACKUP_DATE}",
    "environment": "${ENVIRONMENT}",
    "redis_host": "${REDIS_HOST}",
    "redis_port": ${REDIS_PORT},
    "redis_db": ${REDIS_DB},
    "redis_version": "${redis_version}",
    "used_memory_bytes": ${used_memory},
    "connected_clients": ${connected_clients},
    "total_commands_processed": ${total_commands_processed},
    "backup_type": "${BACKUP_TYPE}",
    "backup_size_bytes": $(du -sb "${BACKUP_PATH}" | cut -f1),
    "compression_enabled": ${COMPRESS},
    "retention_days": ${RETENTION_DAYS},
    "created_by": "$(whoami)@$(hostname)",
    "script_version": "1.0.0"
}
EOF

    log_info "Backup metadata created: ${metadata_file}"
}

# Create Redis backup
create_redis_backup() {
    log_info "Creating Redis backup: ${BACKUP_ID}"

    # Create backup directory
    mkdir -p "${BACKUP_PATH}"

    # Parse Redis URL
    parse_redis_url

    # Create backups based on type
    case "${BACKUP_TYPE}" in
        "rdb")
            create_rdb_backup
            ;;
        "aof")
            create_aof_backup
            ;;
        "both")
            create_rdb_backup
            create_aof_backup
            ;;
    esac

    # Create metadata
    create_backup_metadata
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

    local s3_key="redis/${ENVIRONMENT}/${BACKUP_ID}"
    if [[ "${COMPRESS}" == "true" ]]; then
        s3_key="${s3_key}.tar.gz"
    fi

    local s3_uri="s3://${S3_BUCKET}/${s3_key}"

    # Upload with metadata
    aws s3 cp "${BACKUP_PATH}" "${s3_uri}" \
        --region "${S3_REGION}" \
        --metadata "backup-id=${BACKUP_ID},environment=${ENVIRONMENT},backup-date=${BACKUP_DATE},backup-type=${BACKUP_TYPE}" \
        --storage-class STANDARD_IA

    if [[ $? -eq 0 ]]; then
        log_info "Backup uploaded successfully: ${s3_uri}"
        
        # Create latest symlink
        local latest_key="redis/${ENVIRONMENT}/latest"
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
    find "${BACKUP_DIR}" -name "redis_*" -type f -mtime +7 -delete 2>/dev/null || true
    find "${BACKUP_DIR}" -name "redis_*" -type d -mtime +7 -exec rm -rf {} + 2>/dev/null || true

    # Clean up S3 backups older than retention period
    local cutoff_date
    cutoff_date=$(date -u -d "${RETENTION_DAYS} days ago" +%Y-%m-%d)

    aws s3api list-objects-v2 \
        --bucket "${S3_BUCKET}" \
        --prefix "redis/${ENVIRONMENT}/" \
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
    log_info "Starting Redis backup process..."
    log_info "Backup ID: ${BACKUP_ID}"

    parse_args "$@"
    check_prerequisites
    create_redis_backup
    compress_backup
    upload_to_s3
    cleanup_old_backups

    local backup_size
    if [[ -f "${BACKUP_PATH}" ]]; then
        backup_size=$(du -sh "${BACKUP_PATH}" | cut -f1)
    else
        backup_size="unknown"
    fi

    log_info "Redis backup completed successfully!"
    log_info "Backup ID: ${BACKUP_ID}"
    log_info "Backup Type: ${BACKUP_TYPE}"
    log_info "Backup Size: ${backup_size}"
    log_info "S3 Location: s3://${S3_BUCKET}/redis/${ENVIRONMENT}/${BACKUP_ID}"
    
    # Clean up local backup file
    if [[ -f "${BACKUP_PATH}" ]]; then
        rm -f "${BACKUP_PATH}"
        log_info "Local backup file cleaned up"
    fi
}

# Execute main function
main "$@"
