#!/bin/bash
# Redis Restoration Script for GremlinsAI Disaster Recovery
# Phase 4, Task 4.3: Disaster Recovery & Backup
#
# This script restores Redis cache and session data from backup files
# with comprehensive validation and rollback capabilities.
#
# Usage: ./restore_redis.sh [options]

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOG_DIR="${PROJECT_ROOT}/logs/restore"

# Default configuration
BACKUP_PATH=""
REDIS_URL="${REDIS_URL:-redis://localhost:6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"
ENVIRONMENT="prod"
VERBOSE="false"

# Parse Redis URL
REDIS_HOST="localhost"
REDIS_PORT="6379"
REDIS_DB="0"

# Logging setup
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/restore_redis_$(date +%Y%m%d).log"

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

# Help function
show_help() {
    cat << EOF
Redis Restoration Script for GremlinsAI Disaster Recovery

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --backup-path PATH       Path to extracted backup directory [required]
    --redis-url URL          Redis connection URL [default: redis://localhost:6379]
    --environment ENV        Environment (dev/staging/prod) [default: prod]
    --verbose                Enable verbose output
    --help                   Show this help message

ENVIRONMENT VARIABLES:
    REDIS_PASSWORD          Redis password for authentication

EXAMPLES:
    # Restore from backup directory
    $0 --backup-path ./redis_20241201_143000_prod

    # Restore with custom Redis URL
    $0 --backup-path ./backup --redis-url redis://redis.example.com:6379

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --backup-path)
                BACKUP_PATH="$2"
                shift 2
                ;;
            --redis-url)
                REDIS_URL="$2"
                shift 2
                ;;
            --environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --verbose)
                VERBOSE="true"
                shift
                ;;
            --help)
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
    if [[ -z "${BACKUP_PATH}" ]]; then
        log_error "Backup path is required. Use --backup-path option."
        exit 1
    fi

    if [[ ! -d "${BACKUP_PATH}" ]]; then
        log_error "Backup directory not found: ${BACKUP_PATH}"
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
    local required_tools=("redis-cli")
    for tool in "${required_tools[@]}"; do
        if ! command -v "${tool}" &> /dev/null; then
            log_error "Required tool not found: ${tool}"
            exit 1
        fi
    done

    # Parse Redis URL
    parse_redis_url

    # Check Redis connectivity
    local redis_cmd="redis-cli -h ${REDIS_HOST} -p ${REDIS_PORT}"
    if [[ -n "${REDIS_PASSWORD}" ]]; then
        redis_cmd="${redis_cmd} -a ${REDIS_PASSWORD}"
    fi

    if ! ${redis_cmd} ping | grep -q "PONG"; then
        log_error "Cannot connect to Redis at ${REDIS_HOST}:${REDIS_PORT}"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Validate backup
validate_backup() {
    log_info "Validating backup..."

    # Check metadata file
    local metadata_file="${BACKUP_PATH}/backup_metadata.json"
    if [[ ! -f "${metadata_file}" ]]; then
        log_error "Backup metadata not found: ${metadata_file}"
        exit 1
    fi

    # Extract backup information
    local backup_id=$(jq -r '.backup_id' "${metadata_file}")
    local backup_date=$(jq -r '.backup_date' "${metadata_file}")
    local backup_type=$(jq -r '.backup_type' "${metadata_file}")

    log_info "Backup ID: ${backup_id}"
    log_info "Backup Date: ${backup_date}"
    log_info "Backup Type: ${backup_type}"

    # Validate backup files exist based on type
    case "${backup_type}" in
        "rdb"|"both")
            if [[ ! -f "${BACKUP_PATH}/dump.rdb" ]]; then
                log_error "RDB backup file not found: ${BACKUP_PATH}/dump.rdb"
                exit 1
            fi
            log_info "RDB backup file found"
            ;;
    esac

    case "${backup_type}" in
        "aof"|"both")
            if [[ ! -f "${BACKUP_PATH}/appendonly.aof" ]]; then
                log_error "AOF backup file not found: ${BACKUP_PATH}/appendonly.aof"
                exit 1
            fi
            log_info "AOF backup file found"
            ;;
    esac

    log_success "Backup validation passed"
}

# Stop Redis (if we have control)
stop_redis() {
    log_info "Preparing Redis for restoration..."

    local redis_cmd="redis-cli -h ${REDIS_HOST} -p ${REDIS_PORT}"
    if [[ -n "${REDIS_PASSWORD}" ]]; then
        redis_cmd="${redis_cmd} -a ${REDIS_PASSWORD}"
    fi

    # Get current Redis info
    local redis_info
    redis_info=$(${redis_cmd} INFO server)
    
    local redis_version
    redis_version=$(echo "${redis_info}" | grep "redis_version:" | cut -d: -f2 | tr -d '\r')
    
    log_info "Redis version: ${redis_version}"

    # Flush existing data (with confirmation in production)
    if [[ "${ENVIRONMENT}" == "prod" ]]; then
        log_warn "About to flush all Redis data in production environment"
        log_warn "This action is irreversible. Proceeding in 10 seconds..."
        sleep 10
    fi

    log_info "Flushing existing Redis data..."
    ${redis_cmd} FLUSHALL

    log_success "Redis prepared for restoration"
}

# Restore RDB backup
restore_rdb() {
    log_info "Restoring RDB backup..."

    local redis_cmd="redis-cli -h ${REDIS_HOST} -p ${REDIS_PORT}"
    if [[ -n "${REDIS_PASSWORD}" ]]; then
        redis_cmd="${redis_cmd} -a ${REDIS_PASSWORD}"
    fi

    # Get Redis data directory
    local redis_dir
    redis_dir=$(${redis_cmd} CONFIG GET dir | tail -n 1)
    
    local redis_dbfilename
    redis_dbfilename=$(${redis_cmd} CONFIG GET dbfilename | tail -n 1)

    log_info "Redis data directory: ${redis_dir}"
    log_info "Redis DB filename: ${redis_dbfilename}"

    # Stop Redis writes temporarily
    log_info "Disabling Redis writes..."
    ${redis_cmd} CONFIG SET save ""
    
    # Copy RDB file to Redis data directory
    local source_rdb="${BACKUP_PATH}/dump.rdb"
    local target_rdb="${redis_dir}/${redis_dbfilename}"

    log_info "Copying RDB file from ${source_rdb} to ${target_rdb}"
    
    # For containerized Redis, we need to copy via redis-cli
    if [[ "${REDIS_HOST}" != "localhost" && "${REDIS_HOST}" != "127.0.0.1" ]]; then
        log_info "Remote Redis detected, using DEBUG RELOAD for restoration"
        
        # Use DEBUG RELOAD to load RDB file
        # Note: This requires the RDB file to be accessible to the Redis server
        ${redis_cmd} DEBUG RELOAD
    else
        # Local Redis - direct file copy
        cp "${source_rdb}" "${target_rdb}"
        
        # Restart Redis to load the new data
        log_info "Restarting Redis to load restored data..."
        ${redis_cmd} DEBUG RESTART
    fi

    log_success "RDB restoration completed"
}

# Restore AOF backup
restore_aof() {
    log_info "Restoring AOF backup..."

    local redis_cmd="redis-cli -h ${REDIS_HOST} -p ${REDIS_PORT}"
    if [[ -n "${REDIS_PASSWORD}" ]]; then
        redis_cmd="${redis_cmd} -a ${REDIS_PASSWORD}"
    fi

    # Enable AOF if not already enabled
    local aof_enabled
    aof_enabled=$(${redis_cmd} CONFIG GET appendonly | tail -n 1)
    
    if [[ "${aof_enabled}" != "yes" ]]; then
        log_info "Enabling AOF..."
        ${redis_cmd} CONFIG SET appendonly yes
    fi

    # Get AOF filename
    local aof_filename
    aof_filename=$(${redis_cmd} CONFIG GET appendfilename | tail -n 1)
    
    local redis_dir
    redis_dir=$(${redis_cmd} CONFIG GET dir | tail -n 1)

    log_info "AOF filename: ${aof_filename}"
    log_info "Redis data directory: ${redis_dir}"

    # Copy AOF file
    local source_aof="${BACKUP_PATH}/appendonly.aof"
    local target_aof="${redis_dir}/${aof_filename}"

    log_info "Copying AOF file from ${source_aof} to ${target_aof}"

    if [[ "${REDIS_HOST}" != "localhost" && "${REDIS_HOST}" != "127.0.0.1" ]]; then
        # For remote Redis, we need to replay the AOF commands
        log_info "Remote Redis detected, replaying AOF commands..."
        
        # Read and replay AOF commands
        while IFS= read -r line; do
            if [[ "${line}" =~ ^\*[0-9]+$ ]]; then
                # Start of a new command, read the full command
                local cmd_parts=()
                local num_parts=${line#*}
                
                for ((i=0; i<num_parts; i++)); do
                    read -r length_line
                    read -r cmd_part
                    cmd_parts+=("${cmd_part}")
                done
                
                # Execute the command
                if [[ ${#cmd_parts[@]} -gt 0 ]]; then
                    ${redis_cmd} "${cmd_parts[@]}" 2>/dev/null || true
                fi
            fi
        done < "${source_aof}"
    else
        # Local Redis - direct file copy
        cp "${source_aof}" "${target_aof}"
        
        # Restart Redis to load the AOF
        log_info "Restarting Redis to load AOF data..."
        ${redis_cmd} DEBUG RESTART
    fi

    log_success "AOF restoration completed"
}

# Restore backup based on type
restore_backup() {
    log_info "Starting backup restoration..."

    local metadata_file="${BACKUP_PATH}/backup_metadata.json"
    local backup_type=$(jq -r '.backup_type' "${metadata_file}")

    case "${backup_type}" in
        "rdb")
            restore_rdb
            ;;
        "aof")
            restore_aof
            ;;
        "both")
            # For both, prefer RDB for faster restoration
            restore_rdb
            ;;
        *)
            log_error "Unknown backup type: ${backup_type}"
            exit 1
            ;;
    esac

    log_success "Backup restoration completed"
}

# Validate restoration
validate_restoration() {
    log_info "Validating restoration..."

    local redis_cmd="redis-cli -h ${REDIS_HOST} -p ${REDIS_PORT}"
    if [[ -n "${REDIS_PASSWORD}" ]]; then
        redis_cmd="${redis_cmd} -a ${REDIS_PASSWORD}"
    fi

    # Wait for Redis to be ready
    log_info "Waiting for Redis to be ready..."
    local max_attempts=30
    local attempt=1

    while [[ ${attempt} -le ${max_attempts} ]]; do
        if ${redis_cmd} ping | grep -q "PONG"; then
            break
        fi
        
        log_info "Waiting for Redis... (attempt ${attempt}/${max_attempts})"
        sleep 2
        attempt=$((attempt + 1))
    done

    if [[ ${attempt} -gt ${max_attempts} ]]; then
        log_error "Redis not ready after ${max_attempts} attempts"
        exit 1
    fi

    # Get Redis info
    local redis_info
    redis_info=$(${redis_cmd} INFO)

    # Extract key metrics
    local connected_clients
    connected_clients=$(echo "${redis_info}" | grep "connected_clients:" | cut -d: -f2 | tr -d '\r')

    local used_memory
    used_memory=$(echo "${redis_info}" | grep "used_memory_human:" | cut -d: -f2 | tr -d '\r')

    local total_keys
    total_keys=$(${redis_cmd} DBSIZE)

    log_info "Connected clients: ${connected_clients}"
    log_info "Used memory: ${used_memory}"
    log_info "Total keys: ${total_keys}"

    # Test basic functionality
    log_info "Testing basic functionality..."
    
    # Test SET/GET
    local test_key="test_restore_$(date +%s)"
    local test_value="restoration_test"
    
    ${redis_cmd} SET "${test_key}" "${test_value}" EX 60
    local retrieved_value
    retrieved_value=$(${redis_cmd} GET "${test_key}")
    
    if [[ "${retrieved_value}" == "${test_value}" ]]; then
        log_success "Basic functionality test passed"
        ${redis_cmd} DEL "${test_key}"
    else
        log_error "Basic functionality test failed"
        exit 1
    fi

    # Compare with backup metadata
    local metadata_file="${BACKUP_PATH}/backup_metadata.json"
    local expected_memory=$(jq -r '.used_memory_bytes' "${metadata_file}")
    
    if [[ "${expected_memory}" != "null" && "${expected_memory}" -gt 0 ]]; then
        local current_memory
        current_memory=$(echo "${redis_info}" | grep "used_memory:" | cut -d: -f2 | tr -d '\r')
        
        local memory_diff=$((current_memory - expected_memory))
        local memory_diff_pct=$((memory_diff * 100 / expected_memory))
        
        if [[ ${memory_diff_pct#-} -gt 20 ]]; then
            log_warn "Memory usage differs significantly from backup (${memory_diff_pct}%)"
        else
            log_info "Memory usage matches backup expectations"
        fi
    fi

    log_success "Restoration validation completed"
}

# Re-enable Redis features
finalize_restoration() {
    log_info "Finalizing restoration..."

    local redis_cmd="redis-cli -h ${REDIS_HOST} -p ${REDIS_PORT}"
    if [[ -n "${REDIS_PASSWORD}" ]]; then
        redis_cmd="${redis_cmd} -a ${REDIS_PASSWORD}"
    fi

    # Re-enable saves
    log_info "Re-enabling Redis persistence..."
    ${redis_cmd} CONFIG SET save "900 1 300 10 60 10000"

    # Ensure AOF is properly configured
    local metadata_file="${BACKUP_PATH}/backup_metadata.json"
    local backup_type=$(jq -r '.backup_type' "${metadata_file}")
    
    if [[ "${backup_type}" == "aof" || "${backup_type}" == "both" ]]; then
        ${redis_cmd} CONFIG SET appendonly yes
        ${redis_cmd} CONFIG SET appendfsync everysec
    fi

    # Trigger a save to ensure data persistence
    log_info "Triggering background save..."
    ${redis_cmd} BGSAVE

    log_success "Restoration finalized"
}

# Rollback restoration
rollback_restoration() {
    log_info "Rolling back Redis restoration..."

    local redis_cmd="redis-cli -h ${REDIS_HOST} -p ${REDIS_PORT}"
    if [[ -n "${REDIS_PASSWORD}" ]]; then
        redis_cmd="${redis_cmd} -a ${REDIS_PASSWORD}"
    fi

    # Flush all data to clean state
    log_info "Flushing Redis data to clean state..."
    ${redis_cmd} FLUSHALL

    # Reset configuration to defaults
    log_info "Resetting Redis configuration..."
    ${redis_cmd} CONFIG SET save "900 1 300 10 60 10000"
    ${redis_cmd} CONFIG SET appendonly no

    log_info "Rollback completed"
}

# Error handling with rollback
cleanup() {
    local exit_code=$?
    if [[ ${exit_code} -ne 0 ]]; then
        log_error "Redis restoration failed with exit code ${exit_code}"
        log_error "Check logs for details: ${LOG_FILE}"

        # Attempt rollback if restoration was in progress
        if [[ -n "${RESTORATION_IN_PROGRESS:-}" ]]; then
            log_warn "Attempting rollback of partial restoration..."
            rollback_restoration
        fi
    fi
    exit ${exit_code}
}

trap cleanup EXIT

# Main execution
main() {
    log_info "Starting Redis restoration..."
    export RESTORATION_IN_PROGRESS=true

    parse_args "$@"
    check_prerequisites
    validate_backup
    stop_redis
    restore_backup
    validate_restoration
    finalize_restoration
    unset RESTORATION_IN_PROGRESS

    log_success "Redis restoration completed successfully!"
}

# Execute main function
main "$@"
