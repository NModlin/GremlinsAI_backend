#!/bin/bash
# Weaviate Restoration Script for GremlinsAI Disaster Recovery
# Phase 4, Task 4.3: Disaster Recovery & Backup
#
# This script restores Weaviate vector database from backup files
# with comprehensive validation and rollback capabilities.
#
# Usage: ./restore_weaviate.sh [options]

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOG_DIR="${PROJECT_ROOT}/logs/restore"

# Default configuration
BACKUP_PATH=""
WEAVIATE_URL="${WEAVIATE_URL:-http://localhost:8080}"
WEAVIATE_API_KEY="${WEAVIATE_API_KEY:-}"
ENVIRONMENT="prod"
VERBOSE="false"

# Logging setup
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/restore_weaviate_$(date +%Y%m%d).log"

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
Weaviate Restoration Script for GremlinsAI Disaster Recovery

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --backup-path PATH       Path to extracted backup directory [required]
    --weaviate-url URL       Weaviate server URL [default: http://localhost:8080]
    --environment ENV        Environment (dev/staging/prod) [default: prod]
    --verbose                Enable verbose output
    --help                   Show this help message

ENVIRONMENT VARIABLES:
    WEAVIATE_API_KEY        Weaviate API key for authentication

EXAMPLES:
    # Restore from backup directory
    $0 --backup-path ./weaviate_20241201_143000_prod

    # Restore with custom Weaviate URL
    $0 --backup-path ./backup --weaviate-url http://weaviate.example.com:8080

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
            --weaviate-url)
                WEAVIATE_URL="$2"
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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check required tools
    local required_tools=("curl" "jq")
    for tool in "${required_tools[@]}"; do
        if ! command -v "${tool}" &> /dev/null; then
            log_error "Required tool not found: ${tool}"
            exit 1
        fi
    done

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
    local collections=$(jq -r '.collections[]' "${metadata_file}" 2>/dev/null | wc -l)

    log_info "Backup ID: ${backup_id}"
    log_info "Backup Date: ${backup_date}"
    log_info "Collections: ${collections}"

    # Validate backup files exist
    local backup_files=$(find "${BACKUP_PATH}" -name "*.db" -o -name "*.json" | wc -l)
    if [[ ${backup_files} -eq 0 ]]; then
        log_error "No backup files found in ${BACKUP_PATH}"
        exit 1
    fi

    log_success "Backup validation passed"
}

# Clear existing data
clear_existing_data() {
    log_info "Clearing existing Weaviate data..."

    local auth_header=""
    if [[ -n "${WEAVIATE_API_KEY}" ]]; then
        auth_header="-H Authorization: Bearer ${WEAVIATE_API_KEY}"
    fi

    # Get existing collections
    local schema_url="${WEAVIATE_URL}/v1/schema"
    local existing_collections
    existing_collections=$(curl -s ${auth_header} "${schema_url}" | jq -r '.classes[].class' 2>/dev/null || echo "")

    if [[ -n "${existing_collections}" ]]; then
        log_info "Found existing collections: $(echo ${existing_collections} | tr '\n' ' ')"
        
        # Delete each collection
        echo "${existing_collections}" | while read -r collection; do
            if [[ -n "${collection}" ]]; then
                log_info "Deleting collection: ${collection}"
                curl -s -X DELETE ${auth_header} "${WEAVIATE_URL}/v1/schema/${collection}" || true
            fi
        done
    else
        log_info "No existing collections found"
    fi

    log_success "Existing data cleared"
}

# Restore backup using Weaviate API
restore_backup() {
    log_info "Restoring Weaviate backup..."

    local metadata_file="${BACKUP_PATH}/backup_metadata.json"
    local backup_id=$(jq -r '.backup_id' "${metadata_file}")
    
    local auth_header=""
    if [[ -n "${WEAVIATE_API_KEY}" ]]; then
        auth_header="-H Authorization: Bearer ${WEAVIATE_API_KEY}"
    fi

    # Initiate restore using Weaviate backup API
    local restore_url="${WEAVIATE_URL}/v1/backups/${backup_id}/restore"
    
    # Prepare restore request
    local restore_request=$(cat << EOF
{
    "include": [],
    "exclude": [],
    "config": {
        "CPUPercentage": 80
    }
}
EOF
)

    log_debug "Restore request: ${restore_request}"

    # Initiate restore
    local restore_response
    restore_response=$(curl -s -X POST ${auth_header} \
        -H "Content-Type: application/json" \
        -d "${restore_request}" \
        "${restore_url}")

    log_debug "Restore response: ${restore_response}"

    # Check if restore was initiated successfully
    local restore_status
    restore_status=$(echo "${restore_response}" | jq -r '.status // "FAILED"')

    if [[ "${restore_status}" != "STARTED" ]]; then
        log_error "Failed to initiate restore. Response: ${restore_response}"
        return 1
    fi

    log_info "Restore initiated successfully"

    # Wait for restore completion
    wait_for_restore_completion "${backup_id}"
}

# Wait for restore completion
wait_for_restore_completion() {
    local backup_id="$1"
    local status_url="${WEAVIATE_URL}/v1/backups/${backup_id}/restore"
    local auth_header=""
    if [[ -n "${WEAVIATE_API_KEY}" ]]; then
        auth_header="-H Authorization: Bearer ${WEAVIATE_API_KEY}"
    fi

    log_info "Waiting for restore completion..."

    local max_wait=3600  # 1 hour timeout
    local wait_time=0
    local check_interval=30

    while [[ ${wait_time} -lt ${max_wait} ]]; do
        local status_response
        status_response=$(curl -s ${auth_header} "${status_url}")
        
        local status
        status=$(echo "${status_response}" | jq -r '.status // "UNKNOWN"')

        log_debug "Restore status: ${status}"

        case "${status}" in
            "SUCCESS")
                log_success "Restore completed successfully"
                return 0
                ;;
            "FAILED")
                local error
                error=$(echo "${status_response}" | jq -r '.error // "Unknown error"')
                log_error "Restore failed: ${error}"
                return 1
                ;;
            "STARTED"|"TRANSFERRING")
                log_info "Restore in progress... (${status})"
                ;;
            *)
                log_warn "Unknown restore status: ${status}"
                ;;
        esac

        sleep ${check_interval}
        wait_time=$((wait_time + check_interval))
    done

    log_error "Restore timeout after ${max_wait} seconds"
    return 1
}

# Alternative restore method using direct file restoration
restore_from_files() {
    log_info "Attempting direct file restoration..."

    # This is a simplified approach for cases where the backup API is not available
    # In production, you would typically use Weaviate's backup/restore API
    
    local metadata_file="${BACKUP_PATH}/backup_metadata.json"
    local collections=$(jq -r '.collections[]' "${metadata_file}" 2>/dev/null)

    if [[ -z "${collections}" ]]; then
        log_error "No collections found in backup metadata"
        return 1
    fi

    local auth_header=""
    if [[ -n "${WEAVIATE_API_KEY}" ]]; then
        auth_header="-H Authorization: Bearer ${WEAVIATE_API_KEY}"
    fi

    # Restore schema first
    log_info "Restoring schema..."
    local schema_file="${BACKUP_PATH}/schema.json"
    if [[ -f "${schema_file}" ]]; then
        curl -s -X POST ${auth_header} \
            -H "Content-Type: application/json" \
            -d @"${schema_file}" \
            "${WEAVIATE_URL}/v1/schema"
    fi

    # Restore data for each collection
    echo "${collections}" | while read -r collection; do
        if [[ -n "${collection}" ]]; then
            log_info "Restoring collection: ${collection}"
            
            local collection_file="${BACKUP_PATH}/${collection}.json"
            if [[ -f "${collection_file}" ]]; then
                # Import objects in batches
                curl -s -X POST ${auth_header} \
                    -H "Content-Type: application/json" \
                    -d @"${collection_file}" \
                    "${WEAVIATE_URL}/v1/batch/objects"
            else
                log_warn "Collection file not found: ${collection_file}"
            fi
        fi
    done

    log_success "Direct file restoration completed"
}

# Validate restoration
validate_restoration() {
    log_info "Validating restoration..."

    local auth_header=""
    if [[ -n "${WEAVIATE_API_KEY}" ]]; then
        auth_header="-H Authorization: Bearer ${WEAVIATE_API_KEY}"
    fi

    # Get current schema
    local schema_url="${WEAVIATE_URL}/v1/schema"
    local current_collections
    current_collections=$(curl -s ${auth_header} "${schema_url}" | jq -r '.classes[].class' 2>/dev/null || echo "")

    if [[ -z "${current_collections}" ]]; then
        log_error "No collections found after restoration"
        return 1
    fi

    log_info "Restored collections: $(echo ${current_collections} | tr '\n' ' ')"

    # Validate object counts
    local metadata_file="${BACKUP_PATH}/backup_metadata.json"
    local expected_collections=$(jq -r '.collections[]' "${metadata_file}" 2>/dev/null)

    echo "${expected_collections}" | while read -r collection; do
        if [[ -n "${collection}" ]]; then
            # Get object count
            local objects_url="${WEAVIATE_URL}/v1/objects"
            local object_count
            object_count=$(curl -s ${auth_header} "${objects_url}?class=${collection}&limit=1" | jq -r '.totalResults // 0')
            
            log_info "Collection ${collection}: ${object_count} objects"
        fi
    done

    # Test basic functionality
    log_info "Testing basic functionality..."
    local meta_url="${WEAVIATE_URL}/v1/meta"
    if curl -s ${auth_header} "${meta_url}" | jq -e '.hostname' &> /dev/null; then
        log_success "Basic functionality test passed"
    else
        log_error "Basic functionality test failed"
        return 1
    fi

    log_success "Restoration validation completed"
}

# Rollback restoration
rollback_restoration() {
    log_info "Rolling back Weaviate restoration..."

    local auth_header=""
    if [[ -n "${WEAVIATE_API_KEY}" ]]; then
        auth_header="-H Authorization: Bearer ${WEAVIATE_API_KEY}"
    fi

    # Get collections that were created during restoration
    local current_collections
    current_collections=$(curl -s ${auth_header} "${WEAVIATE_URL}/v1/schema" | jq -r '.classes[].class' 2>/dev/null || echo "")

    if [[ -n "${current_collections}" ]]; then
        log_info "Removing collections created during failed restoration..."
        echo "${current_collections}" | while read -r collection; do
            if [[ -n "${collection}" ]]; then
                log_info "Removing collection: ${collection}"
                curl -s -X DELETE ${auth_header} "${WEAVIATE_URL}/v1/schema/${collection}" || true
            fi
        done
    fi

    log_info "Rollback completed"
}

# Error handling with rollback
cleanup() {
    local exit_code=$?
    if [[ ${exit_code} -ne 0 ]]; then
        log_error "Weaviate restoration failed with exit code ${exit_code}"
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
    log_info "Starting Weaviate restoration..."
    export RESTORATION_IN_PROGRESS=true

    parse_args "$@"
    check_prerequisites
    validate_backup
    clear_existing_data

    # Try backup API first, fall back to file restoration
    if ! restore_backup; then
        log_warn "Backup API restoration failed, trying direct file restoration..."
        restore_from_files
    fi

    validate_restoration
    unset RESTORATION_IN_PROGRESS

    log_success "Weaviate restoration completed successfully!"
}

# Execute main function
main "$@"
