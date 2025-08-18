#!/bin/bash

# Production Monitoring Setup Script - Task T3.8
# 
# This script sets up comprehensive 24/7 monitoring and alerting
# for the GremlinsAI Backend production environment.

set -euo pipefail

# Configuration
NAMESPACE="${NAMESPACE:-monitoring}"
GREMLINSAI_NAMESPACE="${GREMLINSAI_NAMESPACE:-gremlinsai}"
PROMETHEUS_VERSION="${PROMETHEUS_VERSION:-v2.45.0}"
GRAFANA_VERSION="${GRAFANA_VERSION:-10.0.0}"
ALERTMANAGER_VERSION="${ALERTMANAGER_VERSION:-v0.25.0}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

print_header() {
    echo "================================================================================"
    echo "🔍 GremlinsAI Production Monitoring Setup - Task T3.8"
    echo "================================================================================"
    echo "Monitoring Namespace: $NAMESPACE"
    echo "Application Namespace: $GREMLINSAI_NAMESPACE"
    echo "Prometheus Version: $PROMETHEUS_VERSION"
    echo "Grafana Version: $GRAFANA_VERSION"
    echo "================================================================================"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if kubectl is available
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    # Check if helm is available
    if ! command -v helm &> /dev/null; then
        log_error "helm is not installed or not in PATH"
        exit 1
    fi
    
    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Create monitoring namespace
create_monitoring_namespace() {
    log_info "Creating monitoring namespace..."
    
    kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
    kubectl label namespace "$NAMESPACE" name="$NAMESPACE" --overwrite
    kubectl label namespace "$NAMESPACE" purpose="monitoring" --overwrite
    
    log_success "Monitoring namespace created: $NAMESPACE"
}

# Install Prometheus Operator
install_prometheus_operator() {
    log_info "Installing Prometheus Operator..."
    
    # Add Prometheus community Helm repository
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo update
    
    # Install kube-prometheus-stack
    helm upgrade --install prometheus-stack prometheus-community/kube-prometheus-stack \
        --namespace "$NAMESPACE" \
        --version "48.3.1" \
        --set prometheus.prometheusSpec.retention=30d \
        --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=50Gi \
        --set grafana.adminPassword=admin123 \
        --set grafana.persistence.enabled=true \
        --set grafana.persistence.size=10Gi \
        --set alertmanager.alertmanagerSpec.storage.volumeClaimTemplate.spec.resources.requests.storage=10Gi
    
    log_success "Prometheus Operator installed"
}

# Apply Prometheus alerting rules
apply_alerting_rules() {
    log_info "Applying Prometheus alerting rules..."
    
    # Apply the alerting rules
    kubectl apply -f "$(dirname "$0")/prometheus-alerts.yaml" -n "$NAMESPACE"
    
    # Create PrometheusRule CRD
    cat <<EOF | kubectl apply -f -
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: gremlinsai-alerts
  namespace: $NAMESPACE
  labels:
    app: gremlinsai
    prometheus: kube-prometheus
    role: alert-rules
spec:
  groups:
$(cat "$(dirname "$0")/prometheus-alerts.yaml" | sed 's/^/  /')
EOF
    
    log_success "Alerting rules applied"
}

# Configure Alertmanager
configure_alertmanager() {
    log_info "Configuring Alertmanager..."
    
    # Create Alertmanager configuration secret
    kubectl create secret generic alertmanager-config \
        --from-file=alertmanager.yml="$(dirname "$0")/alertmanager-config.yaml" \
        --namespace="$NAMESPACE" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Update Alertmanager to use the configuration
    kubectl patch alertmanager prometheus-stack-kube-prom-alertmanager \
        --namespace="$NAMESPACE" \
        --type='merge' \
        --patch='{"spec":{"configSecret":"alertmanager-config"}}'
    
    log_success "Alertmanager configured"
}

# Create ServiceMonitor for GremlinsAI
create_service_monitor() {
    log_info "Creating ServiceMonitor for GremlinsAI..."
    
    cat <<EOF | kubectl apply -f -
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: gremlinsai-backend
  namespace: $NAMESPACE
  labels:
    app: gremlinsai-backend
    release: prometheus-stack
spec:
  selector:
    matchLabels:
      app: gremlinsai-backend
  namespaceSelector:
    matchNames:
      - $GREMLINSAI_NAMESPACE
  endpoints:
    - port: http
      path: /api/v1/metrics
      interval: 30s
      scrapeTimeout: 10s
      honorLabels: true
EOF
    
    log_success "ServiceMonitor created for GremlinsAI"
}

# Import Grafana dashboards
import_grafana_dashboards() {
    log_info "Importing Grafana dashboards..."
    
    # Wait for Grafana to be ready
    kubectl wait --for=condition=available --timeout=300s deployment/prometheus-stack-grafana -n "$NAMESPACE"
    
    # Create ConfigMap with dashboard definitions
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: gremlinsai-dashboards
  namespace: $NAMESPACE
  labels:
    grafana_dashboard: "1"
data:
  gremlinsai-overview.json: |
    {
      "dashboard": {
        "id": null,
        "title": "GremlinsAI Overview",
        "tags": ["gremlinsai", "overview"],
        "timezone": "browser",
        "panels": [
          {
            "id": 1,
            "title": "API Request Rate",
            "type": "graph",
            "targets": [
              {
                "expr": "sum(rate(gremlinsai_api_requests_total[5m]))",
                "legendFormat": "Requests/sec"
              }
            ]
          },
          {
            "id": 2,
            "title": "API Error Rate",
            "type": "graph",
            "targets": [
              {
                "expr": "sum(rate(gremlinsai_api_errors_total[5m])) / sum(rate(gremlinsai_api_requests_total[5m])) * 100",
                "legendFormat": "Error Rate %"
              }
            ]
          },
          {
            "id": 3,
            "title": "LLM Response Time",
            "type": "graph",
            "targets": [
              {
                "expr": "histogram_quantile(0.95, sum(rate(gremlinsai_llm_response_duration_seconds_bucket[5m])) by (le))",
                "legendFormat": "P95 Latency"
              }
            ]
          }
        ],
        "time": {
          "from": "now-1h",
          "to": "now"
        },
        "refresh": "30s"
      }
    }
EOF
    
    log_success "Grafana dashboards imported"
}

# Setup PagerDuty integration
setup_pagerduty_integration() {
    log_info "Setting up PagerDuty integration..."
    
    # Create PagerDuty integration secret
    kubectl create secret generic pagerduty-config \
        --from-literal=integration-key="${PAGERDUTY_INTEGRATION_KEY:-YOUR_PAGERDUTY_KEY}" \
        --namespace="$NAMESPACE" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    log_success "PagerDuty integration configured"
}

# Verify monitoring setup
verify_monitoring_setup() {
    log_info "Verifying monitoring setup..."
    
    # Check Prometheus
    if kubectl get prometheus -n "$NAMESPACE" &> /dev/null; then
        log_success "✅ Prometheus is running"
    else
        log_error "❌ Prometheus is not running"
        return 1
    fi
    
    # Check Grafana
    if kubectl get deployment prometheus-stack-grafana -n "$NAMESPACE" &> /dev/null; then
        log_success "✅ Grafana is running"
    else
        log_error "❌ Grafana is not running"
        return 1
    fi
    
    # Check Alertmanager
    if kubectl get alertmanager -n "$NAMESPACE" &> /dev/null; then
        log_success "✅ Alertmanager is running"
    else
        log_error "❌ Alertmanager is not running"
        return 1
    fi
    
    # Check ServiceMonitor
    if kubectl get servicemonitor gremlinsai-backend -n "$NAMESPACE" &> /dev/null; then
        log_success "✅ ServiceMonitor is configured"
    else
        log_error "❌ ServiceMonitor is not configured"
        return 1
    fi
    
    # Check PrometheusRule
    if kubectl get prometheusrule gremlinsai-alerts -n "$NAMESPACE" &> /dev/null; then
        log_success "✅ Alerting rules are configured"
    else
        log_error "❌ Alerting rules are not configured"
        return 1
    fi
    
    log_success "Monitoring setup verification completed"
}

# Display access information
display_access_info() {
    log_info "Getting access information..."
    
    # Get Grafana service details
    GRAFANA_SERVICE=$(kubectl get svc prometheus-stack-grafana -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")
    GRAFANA_PORT=$(kubectl get svc prometheus-stack-grafana -n "$NAMESPACE" -o jsonpath='{.spec.ports[0].port}')
    
    # Get Prometheus service details
    PROMETHEUS_SERVICE=$(kubectl get svc prometheus-stack-kube-prom-prometheus -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")
    PROMETHEUS_PORT=$(kubectl get svc prometheus-stack-kube-prom-prometheus -n "$NAMESPACE" -o jsonpath='{.spec.ports[0].port}')
    
    echo ""
    echo "================================================================================"
    echo "📊 Monitoring Access Information"
    echo "================================================================================"
    echo "Grafana:"
    echo "  URL: http://${GRAFANA_SERVICE}:${GRAFANA_PORT}"
    echo "  Username: admin"
    echo "  Password: admin123"
    echo ""
    echo "Prometheus:"
    echo "  URL: http://${PROMETHEUS_SERVICE}:${PROMETHEUS_PORT}"
    echo ""
    echo "Port Forward Commands (if LoadBalancer IPs are pending):"
    echo "  Grafana: kubectl port-forward svc/prometheus-stack-grafana 3000:80 -n $NAMESPACE"
    echo "  Prometheus: kubectl port-forward svc/prometheus-stack-kube-prom-prometheus 9090:9090 -n $NAMESPACE"
    echo "================================================================================"
}

# Main function
main() {
    print_header
    
    log_info "Starting production monitoring setup..."
    
    # Step 1: Check prerequisites
    check_prerequisites
    
    # Step 2: Create monitoring namespace
    create_monitoring_namespace
    
    # Step 3: Install Prometheus Operator
    install_prometheus_operator
    
    # Step 4: Apply alerting rules
    apply_alerting_rules
    
    # Step 5: Configure Alertmanager
    configure_alertmanager
    
    # Step 6: Create ServiceMonitor
    create_service_monitor
    
    # Step 7: Import Grafana dashboards
    import_grafana_dashboards
    
    # Step 8: Setup PagerDuty integration
    setup_pagerduty_integration
    
    # Step 9: Verify setup
    if verify_monitoring_setup; then
        log_success "🎉 Production monitoring setup completed successfully!"
        
        # Step 10: Display access information
        display_access_info
        
        echo ""
        echo "================================================================================"
        echo "📋 Next Steps"
        echo "================================================================================"
        echo "1. Configure PagerDuty integration key in secret"
        echo "2. Update Slack webhook URLs in Alertmanager config"
        echo "3. Test alert notifications"
        echo "4. Review and customize Grafana dashboards"
        echo "5. Train on-call team on procedures"
        echo "================================================================================"
    else
        log_error "Monitoring setup verification failed"
        exit 1
    fi
}

# Run main function
main "$@"
