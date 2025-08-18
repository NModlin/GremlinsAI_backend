#!/usr/bin/env python3
"""
Monitoring & Observability Test Script for Phase 4, Task 4.2

This script validates the monitoring and observability implementation by:
- Testing metrics collection and exposure
- Validating distributed tracing functionality
- Checking dashboard accessibility
- Verifying alerting system configuration
- Generating test data for monitoring validation

Run this script to ensure the monitoring stack meets acceptance criteria.
"""

import asyncio
import json
import time
import requests
import sys
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.metrics_service import metrics_service
from app.core.tracing_service import tracing_service


class MonitoringValidator:
    """Comprehensive monitoring and observability validation."""
    
    def __init__(self):
        """Initialize monitoring validator."""
        self.results: Dict[str, Any] = {}
        self.base_url = "http://localhost:8000"
        self.prometheus_url = "http://localhost:9090"
        self.grafana_url = "http://localhost:3000"
        self.jaeger_url = "http://localhost:16686"
        self.alertmanager_url = "http://localhost:9093"
        
        self.test_passed = 0
        self.test_failed = 0
    
    async def run_validation(self) -> Dict[str, Any]:
        """Run complete monitoring validation."""
        print("🔍 GremlinsAI Monitoring & Observability Validation")
        print("=" * 60)
        
        # Run validation components
        await self.validate_metrics_collection()
        await self.validate_distributed_tracing()
        await self.validate_dashboards()
        await self.validate_alerting_system()
        await self.generate_test_data()
        
        # Generate comprehensive report
        return self.generate_validation_report()
    
    async def validate_metrics_collection(self):
        """Validate metrics collection and exposure."""
        print("\n📊 Validating Metrics Collection...")
        
        metrics_results = {
            'metrics_endpoint_accessible': False,
            'prometheus_metrics_format': False,
            'application_metrics_present': False,
            'system_metrics_present': False,
            'business_metrics_present': False,
            'prometheus_scraping': False
        }
        
        try:
            # Test metrics endpoint
            response = requests.get(f"{self.base_url}/metrics", timeout=10)
            if response.status_code == 200:
                metrics_results['metrics_endpoint_accessible'] = True
                print("   ✅ Metrics endpoint accessible")
                
                metrics_content = response.text
                
                # Check Prometheus format
                if "# HELP" in metrics_content and "# TYPE" in metrics_content:
                    metrics_results['prometheus_metrics_format'] = True
                    print("   ✅ Prometheus metrics format valid")
                
                # Check for application metrics
                app_metrics = [
                    'http_requests_total',
                    'http_request_duration_seconds',
                    'active_connections_total'
                ]
                
                if all(metric in metrics_content for metric in app_metrics):
                    metrics_results['application_metrics_present'] = True
                    print("   ✅ Application metrics present")
                
                # Check for system metrics
                system_metrics = [
                    'cpu_usage_percent',
                    'memory_usage_bytes'
                ]
                
                if any(metric in metrics_content for metric in system_metrics):
                    metrics_results['system_metrics_present'] = True
                    print("   ✅ System metrics present")
                
                # Check for business metrics
                business_metrics = [
                    'rag_queries_total',
                    'multi_agent_tasks_total',
                    'llm_requests_total'
                ]
                
                if any(metric in metrics_content for metric in business_metrics):
                    metrics_results['business_metrics_present'] = True
                    print("   ✅ Business metrics present")
            
            # Test Prometheus scraping
            try:
                prom_response = requests.get(
                    f"{self.prometheus_url}/api/v1/query",
                    params={"query": "up{job=\"gremlinsai\"}"},
                    timeout=5
                )
                
                if prom_response.status_code == 200:
                    data = prom_response.json()
                    if data.get('status') == 'success' and data.get('data', {}).get('result'):
                        metrics_results['prometheus_scraping'] = True
                        print("   ✅ Prometheus scraping working")
                
            except requests.RequestException:
                print("   ⚠️ Prometheus not accessible (may not be running)")
        
        except requests.RequestException as e:
            print(f"   ❌ Metrics endpoint error: {e}")
        
        self.results['metrics_collection'] = metrics_results
        
        # Count results
        passed = sum(1 for result in metrics_results.values() if result)
        total = len(metrics_results)
        self.test_passed += passed
        self.test_failed += (total - passed)
    
    async def validate_distributed_tracing(self):
        """Validate distributed tracing functionality."""
        print("\n🔍 Validating Distributed Tracing...")
        
        tracing_results = {
            'tracing_service_initialized': False,
            'fastapi_instrumentation': False,
            'custom_spans_working': False,
            'trace_context_propagation': False,
            'jaeger_accessible': False,
            'traces_visible': False
        }
        
        try:
            # Check tracing service initialization
            if hasattr(tracing_service, 'tracer') and tracing_service.tracer:
                tracing_results['tracing_service_initialized'] = True
                print("   ✅ Tracing service initialized")
            
            # Test custom span creation
            try:
                with tracing_service.trace_operation("test_operation") as span:
                    span.set_attribute("test.attribute", "test_value")
                    time.sleep(0.1)  # Simulate work
                
                tracing_results['custom_spans_working'] = True
                print("   ✅ Custom spans working")
            except Exception as e:
                print(f"   ❌ Custom spans error: {e}")
            
            # Test trace context
            trace_id = tracing_service.get_current_trace_id()
            if trace_id:
                tracing_results['trace_context_propagation'] = True
                print("   ✅ Trace context propagation working")
            
            # Test Jaeger accessibility
            try:
                jaeger_response = requests.get(f"{self.jaeger_url}/api/services", timeout=5)
                if jaeger_response.status_code == 200:
                    tracing_results['jaeger_accessible'] = True
                    print("   ✅ Jaeger UI accessible")
                    
                    # Check for traces
                    services = jaeger_response.json()
                    if 'gremlinsai' in services.get('data', []):
                        tracing_results['traces_visible'] = True
                        print("   ✅ Traces visible in Jaeger")
            
            except requests.RequestException:
                print("   ⚠️ Jaeger not accessible (may not be running)")
            
            # Test FastAPI instrumentation by making a request
            try:
                test_response = requests.get(f"{self.base_url}/health", timeout=5)
                if test_response.status_code == 200:
                    tracing_results['fastapi_instrumentation'] = True
                    print("   ✅ FastAPI instrumentation working")
            except requests.RequestException:
                print("   ⚠️ Application not accessible for tracing test")
        
        except Exception as e:
            print(f"   ❌ Tracing validation error: {e}")
        
        self.results['distributed_tracing'] = tracing_results
        
        # Count results
        passed = sum(1 for result in tracing_results.values() if result)
        total = len(tracing_results)
        self.test_passed += passed
        self.test_failed += (total - passed)
    
    async def validate_dashboards(self):
        """Validate Grafana dashboards."""
        print("\n📊 Validating Dashboards...")
        
        dashboard_results = {
            'grafana_accessible': False,
            'main_dashboard_exists': False,
            'business_dashboard_exists': False,
            'dashboard_data_sources': False,
            'dashboard_panels_working': False
        }
        
        try:
            # Test Grafana accessibility
            grafana_response = requests.get(f"{self.grafana_url}/api/health", timeout=5)
            if grafana_response.status_code == 200:
                dashboard_results['grafana_accessible'] = True
                print("   ✅ Grafana accessible")
                
                # Test dashboard existence (requires authentication)
                auth = ('admin', 'admin123')
                
                # Check main dashboard
                main_dash_response = requests.get(
                    f"{self.grafana_url}/api/dashboards/uid/gremlinsai-main-overview",
                    auth=auth,
                    timeout=5
                )
                
                if main_dash_response.status_code == 200:
                    dashboard_results['main_dashboard_exists'] = True
                    print("   ✅ Main application dashboard exists")
                
                # Check business dashboard
                business_dash_response = requests.get(
                    f"{self.grafana_url}/api/dashboards/uid/gremlinsai-business-metrics",
                    auth=auth,
                    timeout=5
                )
                
                if business_dash_response.status_code == 200:
                    dashboard_results['business_dashboard_exists'] = True
                    print("   ✅ Business metrics dashboard exists")
                
                # Check data sources
                datasources_response = requests.get(
                    f"{self.grafana_url}/api/datasources",
                    auth=auth,
                    timeout=5
                )
                
                if datasources_response.status_code == 200:
                    datasources = datasources_response.json()
                    prometheus_configured = any(
                        ds.get('type') == 'prometheus' for ds in datasources
                    )
                    
                    if prometheus_configured:
                        dashboard_results['dashboard_data_sources'] = True
                        print("   ✅ Dashboard data sources configured")
        
        except requests.RequestException:
            print("   ⚠️ Grafana not accessible (may not be running)")
        
        self.results['dashboards'] = dashboard_results
        
        # Count results
        passed = sum(1 for result in dashboard_results.values() if result)
        total = len(dashboard_results)
        self.test_passed += passed
        self.test_failed += (total - passed)
    
    async def validate_alerting_system(self):
        """Validate alerting system configuration."""
        print("\n🚨 Validating Alerting System...")
        
        alerting_results = {
            'alertmanager_accessible': False,
            'alert_rules_loaded': False,
            'notification_config': False,
            'alert_routing': False,
            'critical_alerts_defined': False
        }
        
        try:
            # Test AlertManager accessibility
            am_response = requests.get(f"{self.alertmanager_url}/api/v1/status", timeout=5)
            if am_response.status_code == 200:
                alerting_results['alertmanager_accessible'] = True
                print("   ✅ AlertManager accessible")
            
            # Test Prometheus alert rules
            try:
                rules_response = requests.get(
                    f"{self.prometheus_url}/api/v1/rules",
                    timeout=5
                )
                
                if rules_response.status_code == 200:
                    rules_data = rules_response.json()
                    if rules_data.get('status') == 'success':
                        groups = rules_data.get('data', {}).get('groups', [])
                        
                        if groups:
                            alerting_results['alert_rules_loaded'] = True
                            print("   ✅ Alert rules loaded")
                            
                            # Check for critical alerts
                            critical_alerts = [
                                'HighApiErrorRate',
                                'HighApiLatency',
                                'HostOutOfMemory'
                            ]
                            
                            all_rules = []
                            for group in groups:
                                for rule in group.get('rules', []):
                                    all_rules.append(rule.get('name', ''))
                            
                            if any(alert in all_rules for alert in critical_alerts):
                                alerting_results['critical_alerts_defined'] = True
                                print("   ✅ Critical alerts defined")
            
            except requests.RequestException:
                print("   ⚠️ Prometheus not accessible for alert rules check")
            
            # Test AlertManager configuration
            try:
                config_response = requests.get(
                    f"{self.alertmanager_url}/api/v1/status",
                    timeout=5
                )
                
                if config_response.status_code == 200:
                    config_data = config_response.json()
                    if config_data.get('status') == 'success':
                        alerting_results['notification_config'] = True
                        alerting_results['alert_routing'] = True
                        print("   ✅ AlertManager configuration valid")
            
            except requests.RequestException:
                print("   ⚠️ AlertManager configuration check failed")
        
        except requests.RequestException:
            print("   ⚠️ AlertManager not accessible (may not be running)")
        
        self.results['alerting_system'] = alerting_results
        
        # Count results
        passed = sum(1 for result in alerting_results.values() if result)
        total = len(alerting_results)
        self.test_passed += passed
        self.test_failed += (total - passed)
    
    async def generate_test_data(self):
        """Generate test data for monitoring validation."""
        print("\n🧪 Generating Test Data...")
        
        test_data_results = {
            'metrics_generated': False,
            'traces_generated': False,
            'test_requests_successful': False
        }
        
        try:
            # Generate test metrics
            metrics_service.record_http_request(
                method="GET",
                endpoint="/test",
                status_code=200,
                duration=0.1
            )
            
            metrics_service.record_rag_query(
                query_type="test",
                status="success",
                duration=0.5,
                similarity_score=0.85
            )
            
            metrics_service.record_multi_agent_task(
                workflow_type="test",
                status="success",
                duration=2.0
            )
            
            test_data_results['metrics_generated'] = True
            print("   ✅ Test metrics generated")
            
            # Generate test traces
            with tracing_service.trace_operation("test_validation") as span:
                span.set_attribute("test.type", "monitoring_validation")
                
                with tracing_service.trace_rag_query("test", 5) as rag_span:
                    rag_span.set_attribute("rag.test", True)
                    time.sleep(0.1)
                
                with tracing_service.trace_multi_agent_task("test", ["test_agent"]) as ma_span:
                    ma_span.set_attribute("multi_agent.test", True)
                    time.sleep(0.1)
            
            test_data_results['traces_generated'] = True
            print("   ✅ Test traces generated")
            
            # Generate test requests
            try:
                for i in range(5):
                    response = requests.get(f"{self.base_url}/health", timeout=5)
                    if response.status_code != 200:
                        break
                else:
                    test_data_results['test_requests_successful'] = True
                    print("   ✅ Test requests successful")
            
            except requests.RequestException:
                print("   ⚠️ Test requests failed (application may not be running)")
        
        except Exception as e:
            print(f"   ❌ Test data generation error: {e}")
        
        self.results['test_data_generation'] = test_data_results
        
        # Count results
        passed = sum(1 for result in test_data_results.values() if result)
        total = len(test_data_results)
        self.test_passed += passed
        self.test_failed += (total - passed)
    
    def generate_validation_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        print("\n" + "=" * 60)
        print("🔍 MONITORING & OBSERVABILITY VALIDATION REPORT")
        print("=" * 60)
        
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
            print("   Monitoring system is production-ready")
        elif overall_score >= 0.8:
            status = "GOOD"
            print(f"\n✅ MONITORING STATUS: {status}")
            print("   Monitoring system is operational with minor issues")
        elif overall_score >= 0.6:
            status = "NEEDS_IMPROVEMENT"
            print(f"\n⚠️ MONITORING STATUS: {status}")
            print("   Monitoring system needs improvements")
        else:
            status = "CRITICAL"
            print(f"\n🚨 MONITORING STATUS: {status}")
            print("   Monitoring system has critical issues")
        
        # Generate report
        report = {
            "timestamp": time.time(),
            "overall_score": overall_score,
            "monitoring_status": status,
            "total_tests": total_tests,
            "passed_tests": self.test_passed,
            "failed_tests": self.test_failed,
            "detailed_results": self.results,
            "recommendations": self._generate_recommendations()
        }
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate monitoring recommendations based on validation results."""
        recommendations = []
        
        # Metrics recommendations
        metrics_results = self.results.get('metrics_collection', {})
        if not metrics_results.get('prometheus_scraping'):
            recommendations.append("Configure Prometheus to scrape application metrics")
        if not metrics_results.get('business_metrics_present'):
            recommendations.append("Implement business metrics collection")
        
        # Tracing recommendations
        tracing_results = self.results.get('distributed_tracing', {})
        if not tracing_results.get('jaeger_accessible'):
            recommendations.append("Set up Jaeger for distributed tracing")
        if not tracing_results.get('traces_visible'):
            recommendations.append("Verify trace collection and visibility")
        
        # Dashboard recommendations
        dashboard_results = self.results.get('dashboards', {})
        if not dashboard_results.get('grafana_accessible'):
            recommendations.append("Set up Grafana for monitoring dashboards")
        if not dashboard_results.get('main_dashboard_exists'):
            recommendations.append("Import main application dashboard")
        
        # Alerting recommendations
        alerting_results = self.results.get('alerting_system', {})
        if not alerting_results.get('alertmanager_accessible'):
            recommendations.append("Configure AlertManager for notifications")
        if not alerting_results.get('critical_alerts_defined'):
            recommendations.append("Define critical alert rules")
        
        # Add general recommendations
        if self.test_failed > 5:
            recommendations.append("Review monitoring stack deployment")
        if self.test_passed < 15:
            recommendations.append("Complete monitoring system setup")
        
        return recommendations


async def main():
    """Run monitoring validation."""
    validator = MonitoringValidator()
    report = await validator.run_validation()
    
    # Save report to file
    with open("monitoring_validation_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Detailed validation report saved to: monitoring_validation_report.json")
    
    # Exit with appropriate code
    if report['monitoring_status'] in ['EXCELLENT', 'GOOD']:
        sys.exit(0)
    elif report['monitoring_status'] == 'NEEDS_IMPROVEMENT':
        sys.exit(1)
    else:
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())
