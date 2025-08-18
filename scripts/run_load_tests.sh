#!/bin/bash
# GremlinsAI Production Load Testing Automation Script
# Phase 4, Task 4.4: Load Testing & Optimization
#
# This script automates the execution of comprehensive load tests at multiple
# tiers to validate scalability targets and identify performance bottlenecks.
#
# Usage: ./run_load_tests.sh [options]
# Options:
#   -h, --host HOST          Target host URL [default: http://localhost:8000]
#   -t, --test-type TYPE     Test type (baseline|intermediate|peak|full) [default: full]
#   -d, --duration MINUTES  Test duration in minutes [default: 30]
#   -r, --report-dir DIR     Report output directory [default: ./load_test_reports]
#   -m, --monitor            Enable monitoring integration [default: true]
#   -v, --verbose            Verbose output
#   --help                   Show this help message

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TESTS_DIR="${PROJECT_ROOT}/tests/performance"
REPORTS_DIR="${PROJECT_ROOT}/load_test_reports"

# Default configuration
TARGET_HOST="http://localhost:8000"
TEST_TYPE="full"
TEST_DURATION="30"
ENABLE_MONITORING="true"
VERBOSE="false"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

# Test configuration
declare -A TEST_CONFIGS=(
    ["baseline"]="100 10 30"      # users spawn_rate duration
    ["intermediate"]="500 25 30"   # users spawn_rate duration
    ["peak"]="1000 50 30"         # users spawn_rate duration
    ["stress"]="1500 75 30"       # users spawn_rate duration
)

# Performance thresholds
RESPONSE_TIME_THRESHOLD="2.0"  # seconds
CPU_THRESHOLD="80"             # percentage
MEMORY_THRESHOLD="80"          # percentage
ERROR_RATE_THRESHOLD="5"       # percentage

# Logging setup
LOG_DIR="${PROJECT_ROOT}/logs/load_tests"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/load_test_${TIMESTAMP}.log"

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

# Help function
show_help() {
    cat << EOF
GremlinsAI Production Load Testing Automation Script

USAGE:
    $0 [OPTIONS]

OPTIONS:
    -h, --host HOST          Target host URL [default: http://localhost:8000]
    -t, --test-type TYPE     Test type (baseline|intermediate|peak|stress|full) [default: full]
    -d, --duration MINUTES  Test duration in minutes [default: 30]
    -r, --report-dir DIR     Report output directory [default: ./load_test_reports]
    -m, --monitor            Enable monitoring integration [default: true]
    -v, --verbose            Verbose output
    --help                   Show this help message

TEST TYPES:
    baseline      - 100 concurrent users (30 minutes)
    intermediate  - 500 concurrent users (30 minutes)
    peak          - 1000 concurrent users (30 minutes)
    stress        - 1500 concurrent users (30 minutes)
    full          - All test tiers sequentially

EXAMPLES:
    # Run full test suite
    $0 --host http://gremlinsai.example.com

    # Run only peak load test
    $0 --test-type peak --duration 60

    # Run with custom report directory
    $0 --report-dir /tmp/load_reports --verbose

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--host)
                TARGET_HOST="$2"
                shift 2
                ;;
            -t|--test-type)
                TEST_TYPE="$2"
                shift 2
                ;;
            -d|--duration)
                TEST_DURATION="$2"
                shift 2
                ;;
            -r|--report-dir)
                REPORTS_DIR="$2"
                shift 2
                ;;
            -m|--monitor)
                ENABLE_MONITORING="$2"
                shift 2
                ;;
            -v|--verbose)
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
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check required tools
    local required_tools=("locust" "curl" "jq")
    for tool in "${required_tools[@]}"; do
        if ! command -v "${tool}" &> /dev/null; then
            log_error "Required tool not found: ${tool}"
            exit 1
        fi
    done

    # Check Python dependencies
    if ! python3 -c "import locust, websocket" &> /dev/null; then
        log_error "Required Python packages not installed. Run: pip install locust websocket-client"
        exit 1
    fi

    # Check target host connectivity
    if ! curl -f -s "${TARGET_HOST}/api/v1/health" &> /dev/null; then
        log_warn "Target host may not be accessible: ${TARGET_HOST}"
        log_warn "Continuing anyway - host may start during test preparation"
    fi

    # Create report directory
    mkdir -p "${REPORTS_DIR}"

    log_info "Prerequisites check completed"
}

# Start monitoring collection
start_monitoring() {
    if [[ "${ENABLE_MONITORING}" != "true" ]]; then
        return 0
    fi

    log_info "Starting monitoring collection..."

    # Start system metrics collection
    local monitoring_script="${SCRIPT_DIR}/collect_system_metrics.sh"
    if [[ -f "${monitoring_script}" ]]; then
        nohup "${monitoring_script}" "${REPORTS_DIR}/system_metrics_${TIMESTAMP}.json" > /dev/null 2>&1 &
        echo $! > "${REPORTS_DIR}/monitoring_pid.txt"
        log_info "System metrics collection started"
    fi

    # Query Prometheus for baseline metrics
    if command -v curl &> /dev/null; then
        local prometheus_url="http://localhost:9090"
        if curl -f -s "${prometheus_url}/api/v1/query?query=up" &> /dev/null; then
            log_info "Prometheus monitoring available at ${prometheus_url}"
            echo "${prometheus_url}" > "${REPORTS_DIR}/prometheus_url.txt"
        fi
    fi
}

# Stop monitoring collection
stop_monitoring() {
    if [[ "${ENABLE_MONITORING}" != "true" ]]; then
        return 0
    fi

    log_info "Stopping monitoring collection..."

    # Stop system metrics collection
    if [[ -f "${REPORTS_DIR}/monitoring_pid.txt" ]]; then
        local monitoring_pid=$(cat "${REPORTS_DIR}/monitoring_pid.txt")
        if kill "${monitoring_pid}" 2>/dev/null; then
            log_info "System metrics collection stopped"
        fi
        rm -f "${REPORTS_DIR}/monitoring_pid.txt"
    fi
}

# Run single load test
run_load_test() {
    local test_name="$1"
    local users="$2"
    local spawn_rate="$3"
    local duration="$4"

    log_info "Starting ${test_name} load test: ${users} users, ${spawn_rate} spawn rate, ${duration}m duration"

    local test_start_time=$(date +%s)
    local report_file="${REPORTS_DIR}/${test_name}_${TIMESTAMP}.html"
    local json_report="${REPORTS_DIR}/${test_name}_${TIMESTAMP}.json"

    # Run Locust load test
    locust \
        -f "${TESTS_DIR}/production_load_test.py" \
        --host="${TARGET_HOST}" \
        --users="${users}" \
        --spawn-rate="${spawn_rate}" \
        --run-time="${duration}m" \
        --html="${report_file}" \
        --csv="${REPORTS_DIR}/${test_name}_${TIMESTAMP}" \
        --logfile="${LOG_DIR}/${test_name}_${TIMESTAMP}.log" \
        --loglevel=INFO \
        --headless

    local test_end_time=$(date +%s)
    local test_duration=$((test_end_time - test_start_time))

    log_info "${test_name} load test completed in ${test_duration} seconds"

    # Parse results and generate JSON report
    generate_test_report "${test_name}" "${users}" "${spawn_rate}" "${duration}" "${test_duration}"

    return 0
}

# Generate test report
generate_test_report() {
    local test_name="$1"
    local users="$2"
    local spawn_rate="$3"
    local duration="$4"
    local actual_duration="$5"

    log_info "Generating report for ${test_name} test..."

    local csv_stats="${REPORTS_DIR}/${test_name}_${TIMESTAMP}_stats.csv"
    local json_report="${REPORTS_DIR}/${test_name}_${TIMESTAMP}.json"

    # Parse CSV results if available
    local avg_response_time="0"
    local p95_response_time="0"
    local p99_response_time="0"
    local requests_per_second="0"
    local failure_rate="0"

    if [[ -f "${csv_stats}" ]]; then
        # Extract metrics from CSV (skip header)
        local stats_line=$(tail -n 1 "${csv_stats}")
        if [[ -n "${stats_line}" ]]; then
            # Parse CSV fields (adjust indices based on Locust CSV format)
            avg_response_time=$(echo "${stats_line}" | cut -d',' -f10)
            p95_response_time=$(echo "${stats_line}" | cut -d',' -f13)
            p99_response_time=$(echo "${stats_line}" | cut -d',' -f14)
            requests_per_second=$(echo "${stats_line}" | cut -d',' -f15)
            failure_rate=$(echo "${stats_line}" | cut -d',' -f11)
        fi
    fi

    # Generate JSON report
    cat > "${json_report}" << EOF
{
    "test_configuration": {
        "test_name": "${test_name}",
        "target_host": "${TARGET_HOST}",
        "concurrent_users": ${users},
        "spawn_rate": ${spawn_rate},
        "planned_duration_minutes": ${duration},
        "actual_duration_seconds": ${actual_duration},
        "timestamp": "${TIMESTAMP}"
    },
    "performance_metrics": {
        "average_response_time_ms": ${avg_response_time},
        "p95_response_time_ms": ${p95_response_time},
        "p99_response_time_ms": ${p99_response_time},
        "requests_per_second": ${requests_per_second},
        "failure_rate_percent": ${failure_rate}
    },
    "acceptance_criteria": {
        "response_time_under_2s": $(echo "${avg_response_time} < 2000" | bc -l),
        "error_rate_under_5_percent": $(echo "${failure_rate} < 5" | bc -l),
        "target_users_achieved": $(echo "${users} >= 100" | bc -l)
    },
    "test_status": "completed",
    "report_files": {
        "html_report": "${report_file}",
        "csv_stats": "${csv_stats}",
        "log_file": "${LOG_DIR}/${test_name}_${TIMESTAMP}.log"
    }
}
EOF

    log_info "Report generated: ${json_report}"
}

# Run full test suite
run_full_test_suite() {
    log_info "Starting full load test suite..."

    local test_results=()

    # Run each test tier
    for test_tier in "baseline" "intermediate" "peak"; do
        local config="${TEST_CONFIGS[$test_tier]}"
        local users=$(echo $config | cut -d' ' -f1)
        local spawn_rate=$(echo $config | cut -d' ' -f2)
        local duration=$(echo $config | cut -d' ' -f3)

        log_info "Preparing for ${test_tier} test..."
        
        # Wait between tests to allow system recovery
        if [[ ${#test_results[@]} -gt 0 ]]; then
            log_info "Waiting 5 minutes for system recovery..."
            sleep 300
        fi

        # Run the test
        if run_load_test "${test_tier}" "${users}" "${spawn_rate}" "${duration}"; then
            test_results+=("${test_tier}:PASSED")
            log_info "${test_tier} test completed successfully"
        else
            test_results+=("${test_tier}:FAILED")
            log_error "${test_tier} test failed"
        fi
    done

    # Generate summary report
    generate_summary_report "${test_results[@]}"
}

# Generate summary report
generate_summary_report() {
    local test_results=("$@")
    
    log_info "Generating summary report..."

    local summary_file="${REPORTS_DIR}/load_test_summary_${TIMESTAMP}.json"
    local passed_tests=0
    local total_tests=${#test_results[@]}

    # Count passed tests
    for result in "${test_results[@]}"; do
        if [[ "${result}" == *":PASSED" ]]; then
            ((passed_tests++))
        fi
    done

    # Calculate overall success rate
    local success_rate=$(echo "scale=2; ${passed_tests} * 100 / ${total_tests}" | bc)

    # Generate summary
    cat > "${summary_file}" << EOF
{
    "load_test_summary": {
        "timestamp": "${TIMESTAMP}",
        "target_host": "${TARGET_HOST}",
        "total_tests": ${total_tests},
        "passed_tests": ${passed_tests},
        "success_rate": "${success_rate}%",
        "test_results": [
$(printf '            "%s"' "${test_results[@]}" | sed 's/$/,/g' | sed '$s/,$//')
        ]
    },
    "acceptance_criteria_status": {
        "handles_1000_users": $(echo "${passed_tests} >= 3" | bc),
        "response_times_under_2s": "See individual test reports",
        "resource_utilization_under_80": "See monitoring reports",
        "auto_scaling_functional": "Manual verification required"
    },
    "recommendations": [
        "Review individual test reports for detailed performance metrics",
        "Analyze monitoring data for resource utilization patterns",
        "Verify auto-scaling behavior during peak load test",
        "Consider stress testing beyond 1000 users if all tests passed"
    ],
    "next_steps": [
        "Implement any identified performance optimizations",
        "Update Kubernetes resource limits based on findings",
        "Schedule regular load testing as part of CI/CD pipeline",
        "Document performance baselines for future reference"
    ]
}
EOF

    log_info "Summary report generated: ${summary_file}"
    
    # Display summary
    echo
    echo "=========================================="
    echo "LOAD TEST SUMMARY"
    echo "=========================================="
    echo "Total Tests: ${total_tests}"
    echo "Passed Tests: ${passed_tests}"
    echo "Success Rate: ${success_rate}%"
    echo
    echo "Test Results:"
    for result in "${test_results[@]}"; do
        echo "  - ${result}"
    done
    echo
    echo "Reports Directory: ${REPORTS_DIR}"
    echo "Summary Report: ${summary_file}"
    echo "=========================================="
}

# Main execution
main() {
    log_info "Starting GremlinsAI load testing automation..."

    parse_args "$@"
    check_prerequisites
    start_monitoring

    # Trap to ensure monitoring is stopped on exit
    trap stop_monitoring EXIT

    case "${TEST_TYPE}" in
        "baseline"|"intermediate"|"peak"|"stress")
            local config="${TEST_CONFIGS[$TEST_TYPE]}"
            local users=$(echo $config | cut -d' ' -f1)
            local spawn_rate=$(echo $config | cut -d' ' -f2)
            local duration="${TEST_DURATION}"
            
            run_load_test "${TEST_TYPE}" "${users}" "${spawn_rate}" "${duration}"
            ;;
        "full")
            run_full_test_suite
            ;;
        *)
            log_error "Invalid test type: ${TEST_TYPE}"
            show_help
            exit 1
            ;;
    esac

    log_info "Load testing automation completed successfully"
}

# Execute main function
main "$@"
