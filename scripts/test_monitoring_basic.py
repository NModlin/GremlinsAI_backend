#!/usr/bin/env python3
"""
Basic Monitoring Test Script for Phase 4, Task 4.2

This script validates the core monitoring implementation without requiring
external dependencies like Jaeger or Prometheus to be running.
"""

import asyncio
import json
import time
import sys
import os
from typing import Dict, Any

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class BasicMonitoringValidator:
    """Basic monitoring validation without external dependencies."""
    
    def __init__(self):
        """Initialize validator."""
        self.results: Dict[str, Any] = {}
        self.test_passed = 0
        self.test_failed = 0
    
    async def run_validation(self) -> Dict[str, Any]:
        """Run basic monitoring validation."""
        print("🔍 GremlinsAI Basic Monitoring Validation")
        print("=" * 50)
        
        # Run validation components
        await self.validate_metrics_service()
        await self.validate_monitoring_middleware()
        await self.validate_configuration_files()
        
        # Generate report
        return self.generate_validation_report()
    
    async def validate_metrics_service(self):
        """Validate metrics service implementation."""
        print("\n📊 Validating Metrics Service...")
        
        metrics_results = {
            'metrics_service_importable': False,
            'prometheus_client_available': False,
            'metrics_initialization': False,
            'metric_recording': False,
            'metrics_export': False
        }
        
        try:
            # Test metrics service import
            from app.core.metrics_service import metrics_service
            metrics_results['metrics_service_importable'] = True
            print("   ✅ Metrics service importable")
            
            # Test prometheus client
            try:
                import prometheus_client
                metrics_results['prometheus_client_available'] = True
                print("   ✅ Prometheus client available")
            except ImportError:
                print("   ❌ Prometheus client not installed")
            
            # Test metrics initialization
            if hasattr(metrics_service, 'http_requests_total'):
                metrics_results['metrics_initialization'] = True
                print("   ✅ Metrics initialized")
            
            # Test metric recording
            try:
                metrics_service.record_http_request(
                    method="GET",
                    endpoint="/test",
                    status_code=200,
                    duration=0.1
                )
                metrics_results['metric_recording'] = True
                print("   ✅ Metric recording working")
            except Exception as e:
                print(f"   ❌ Metric recording failed: {e}")
            
            # Test metrics export
            try:
                metrics_data = metrics_service.get_metrics()
                if "http_requests_total" in metrics_data:
                    metrics_results['metrics_export'] = True
                    print("   ✅ Metrics export working")
            except Exception as e:
                print(f"   ❌ Metrics export failed: {e}")
        
        except ImportError as e:
            print(f"   ❌ Metrics service import failed: {e}")
        except Exception as e:
            print(f"   ❌ Metrics validation error: {e}")
        
        self.results['metrics_service'] = metrics_results
        
        # Count results
        passed = sum(1 for result in metrics_results.values() if result)
        total = len(metrics_results)
        self.test_passed += passed
        self.test_failed += (total - passed)
    
    async def validate_monitoring_middleware(self):
        """Validate monitoring middleware implementation."""
        print("\n🔧 Validating Monitoring Middleware...")
        
        middleware_results = {
            'middleware_importable': False,
            'fastapi_middleware_class': False,
            'websocket_monitoring': False,
            'health_check_middleware': False,
            'setup_function': False
        }
        
        try:
            # Test middleware import
            from app.middleware.monitoring_middleware import MonitoringMiddleware
            middleware_results['middleware_importable'] = True
            print("   ✅ Monitoring middleware importable")
            
            # Test FastAPI middleware class
            from fastapi.middleware.base import BaseHTTPMiddleware
            if issubclass(MonitoringMiddleware, BaseHTTPMiddleware):
                middleware_results['fastapi_middleware_class'] = True
                print("   ✅ FastAPI middleware class structure")
            
            # Test WebSocket monitoring
            try:
                from app.middleware.monitoring_middleware import WebSocketMonitoringMixin
                middleware_results['websocket_monitoring'] = True
                print("   ✅ WebSocket monitoring available")
            except ImportError:
                print("   ❌ WebSocket monitoring not available")
            
            # Test health check middleware
            try:
                from app.middleware.monitoring_middleware import HealthCheckMiddleware
                middleware_results['health_check_middleware'] = True
                print("   ✅ Health check middleware available")
            except ImportError:
                print("   ❌ Health check middleware not available")
            
            # Test setup function
            try:
                from app.middleware.monitoring_middleware import setup_monitoring_middleware
                middleware_results['setup_function'] = True
                print("   ✅ Setup function available")
            except ImportError:
                print("   ❌ Setup function not available")
        
        except ImportError as e:
            print(f"   ❌ Monitoring middleware import failed: {e}")
        except Exception as e:
            print(f"   ❌ Middleware validation error: {e}")
        
        self.results['monitoring_middleware'] = middleware_results
        
        # Count results
        passed = sum(1 for result in middleware_results.values() if result)
        total = len(middleware_results)
        self.test_passed += passed
        self.test_failed += (total - passed)
    
    async def validate_configuration_files(self):
        """Validate monitoring configuration files."""
        print("\n📋 Validating Configuration Files...")
        
        config_results = {
            'prometheus_config': False,
            'alertmanager_config': False,
            'grafana_dashboards': False,
            'alert_rules': False,
            'docker_compose': False
        }
        
        try:
            # Check Prometheus configuration
            prometheus_config_path = "ops/prometheus/prometheus.yml"
            if os.path.exists(prometheus_config_path):
                config_results['prometheus_config'] = True
                print("   ✅ Prometheus configuration exists")
            else:
                print("   ❌ Prometheus configuration missing")
            
            # Check AlertManager configuration
            alertmanager_config_path = "ops/alertmanager/alertmanager.yml"
            if os.path.exists(alertmanager_config_path):
                config_results['alertmanager_config'] = True
                print("   ✅ AlertManager configuration exists")
            else:
                print("   ❌ AlertManager configuration missing")
            
            # Check Grafana dashboards
            grafana_dashboard_path = "ops/grafana/dashboards/main-application-overview.json"
            if os.path.exists(grafana_dashboard_path):
                config_results['grafana_dashboards'] = True
                print("   ✅ Grafana dashboards exist")
            else:
                print("   ❌ Grafana dashboards missing")
            
            # Check alert rules
            alert_rules_path = "ops/prometheus/rules/alerts.yml"
            if os.path.exists(alert_rules_path):
                config_results['alert_rules'] = True
                print("   ✅ Alert rules exist")
            else:
                print("   ❌ Alert rules missing")
            
            # Check Docker Compose
            docker_compose_path = "ops/docker-compose.monitoring.yml"
            if os.path.exists(docker_compose_path):
                config_results['docker_compose'] = True
                print("   ✅ Docker Compose monitoring stack exists")
            else:
                print("   ❌ Docker Compose monitoring stack missing")
        
        except Exception as e:
            print(f"   ❌ Configuration validation error: {e}")
        
        self.results['configuration_files'] = config_results
        
        # Count results
        passed = sum(1 for result in config_results.values() if result)
        total = len(config_results)
        self.test_passed += passed
        self.test_failed += (total - passed)
    
    def generate_validation_report(self) -> Dict[str, Any]:
        """Generate validation report."""
        print("\n" + "=" * 50)
        print("🔍 BASIC MONITORING VALIDATION REPORT")
        print("=" * 50)
        
        # Calculate overall scores
        total_tests = self.test_passed + self.test_failed
        overall_score = self.test_passed / total_tests if total_tests > 0 else 0
        
        for category, results in self.results.items():
            if isinstance(results, dict):
                category_total = len(results)
                category_passed = sum(1 for check in results.values() if check)
                
                print(f"\n📊 {category.upper().replace('_', ' ')}:")
                print(f"   Passed: {category_passed}/{category_total} ({category_passed/category_total*100:.1f}%)")
        
        print(f"\n📈 OVERALL MONITORING SCORE: {overall_score:.1%}")
        print(f"📊 Total Tests: {total_tests}")
        print(f"✅ Passed: {self.test_passed}")
        print(f"❌ Failed: {self.test_failed}")
        
        # Monitoring status
        if overall_score >= 0.9:
            status = "EXCELLENT"
            print(f"\n🎉 MONITORING STATUS: {status}")
            print("   Core monitoring implementation is complete")
        elif overall_score >= 0.8:
            status = "GOOD"
            print(f"\n✅ MONITORING STATUS: {status}")
            print("   Core monitoring implementation is solid")
        elif overall_score >= 0.6:
            status = "NEEDS_IMPROVEMENT"
            print(f"\n⚠️ MONITORING STATUS: {status}")
            print("   Core monitoring needs improvements")
        else:
            status = "CRITICAL"
            print(f"\n🚨 MONITORING STATUS: {status}")
            print("   Core monitoring has critical issues")
        
        # Generate report
        report = {
            "timestamp": time.time(),
            "overall_score": overall_score,
            "monitoring_status": status,
            "total_tests": total_tests,
            "passed_tests": self.test_passed,
            "failed_tests": self.test_failed,
            "detailed_results": self.results,
            "next_steps": self._generate_next_steps()
        }
        
        return report
    
    def _generate_next_steps(self) -> list:
        """Generate next steps based on validation results."""
        next_steps = []
        
        # Metrics service recommendations
        metrics_results = self.results.get('metrics_service', {})
        if not metrics_results.get('prometheus_client_available'):
            next_steps.append("Install prometheus-client: pip install prometheus-client")
        if not metrics_results.get('metrics_export'):
            next_steps.append("Fix metrics export functionality")
        
        # Middleware recommendations
        middleware_results = self.results.get('monitoring_middleware', {})
        if not middleware_results.get('middleware_importable'):
            next_steps.append("Fix monitoring middleware import issues")
        
        # Configuration recommendations
        config_results = self.results.get('configuration_files', {})
        if not config_results.get('docker_compose'):
            next_steps.append("Create Docker Compose monitoring stack")
        if not config_results.get('alert_rules'):
            next_steps.append("Define Prometheus alert rules")
        
        # General recommendations
        if self.test_failed > 5:
            next_steps.append("Review and fix core monitoring implementation")
        if self.test_passed < 10:
            next_steps.append("Complete basic monitoring setup")
        
        # Deployment recommendations
        next_steps.extend([
            "Install OpenTelemetry dependencies for tracing",
            "Start monitoring stack with Docker Compose",
            "Configure Grafana dashboards",
            "Test end-to-end monitoring pipeline"
        ])
        
        return next_steps


async def main():
    """Run basic monitoring validation."""
    validator = BasicMonitoringValidator()
    report = await validator.run_validation()
    
    # Save report to file
    with open("basic_monitoring_validation_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Validation report saved to: basic_monitoring_validation_report.json")
    
    # Print next steps
    if report['next_steps']:
        print(f"\n🚀 NEXT STEPS:")
        for i, step in enumerate(report['next_steps'], 1):
            print(f"   {i}. {step}")
    
    # Exit with appropriate code
    if report['monitoring_status'] in ['EXCELLENT', 'GOOD']:
        sys.exit(0)
    elif report['monitoring_status'] == 'NEEDS_IMPROVEMENT':
        sys.exit(1)
    else:
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())
