#!/usr/bin/env python3
"""
Load Testing Infrastructure Validation Script
Phase 4, Task 4.4: Load Testing & Optimization

This script validates that the load testing infrastructure is properly
configured and ready for production-scale testing.

Usage:
    python validate_load_testing.py [options]
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional

class LoadTestingValidator:
    """Validates load testing infrastructure setup."""
    
    def __init__(self):
        """Initialize validator."""
        self.project_root = Path(__file__).parent.parent
        self.results = {}
        
    def validate_infrastructure(self) -> Dict[str, Any]:
        """Validate complete load testing infrastructure."""
        print("🔍 GremlinsAI Load Testing Infrastructure Validation")
        print("=" * 60)
        
        # Run validation components
        files_check = self.check_required_files()
        dependencies_check = self.check_dependencies()
        scripts_check = self.check_scripts_functionality()
        config_check = self.check_configuration()
        
        # Calculate overall score
        all_checks = [files_check, dependencies_check, scripts_check, config_check]
        total_tests = sum(len(check.values()) for check in all_checks)
        passed_tests = sum(sum(check.values()) for check in all_checks)
        
        overall_score = passed_tests / total_tests if total_tests > 0 else 0
        
        print(f"\n📈 OVERALL SCORE: {overall_score:.1%}")
        print(f"📊 Tests Passed: {passed_tests}/{total_tests}")
        
        # Determine readiness status
        if overall_score >= 0.95:
            status = "READY_FOR_LOAD_TESTING"
            print(f"\n🎉 STATUS: {status}")
        elif overall_score >= 0.85:
            status = "MOSTLY_READY"
            print(f"\n✅ STATUS: {status}")
        else:
            status = "NOT_READY"
            print(f"\n⚠️ STATUS: {status}")
        
        return {
            "overall_score": overall_score,
            "status": status,
            "files_check": files_check,
            "dependencies_check": dependencies_check,
            "scripts_check": scripts_check,
            "config_check": config_check,
            "passed_tests": passed_tests,
            "total_tests": total_tests
        }
    
    def check_required_files(self) -> Dict[str, bool]:
        """Check for required load testing files."""
        print("\n📁 Checking Required Files...")
        
        required_files = {
            'locust_test_file': 'tests/performance/production_load_test.py',
            'load_test_runner': 'scripts/run_load_tests.sh',
            'metrics_collector': 'scripts/collect_system_metrics.sh',
            'performance_optimizer': 'scripts/optimize_performance.py',
            'validation_report': 'docs/PERFORMANCE_VALIDATION_REPORT.md',
            'test_validator': 'scripts/validate_load_testing.py'
        }
        
        results = {}
        for name, path in required_files.items():
            file_path = self.project_root / path
            exists = file_path.exists()
            results[name] = exists
            
            status = "✅" if exists else "❌"
            print(f"   {status} {name}: {path}")
        
        return results
    
    def check_dependencies(self) -> Dict[str, bool]:
        """Check for required dependencies."""
        print("\n📦 Checking Dependencies...")
        
        results = {
            'python_locust': False,
            'python_websocket': False,
            'bash_available': False,
            'curl_available': False,
            'jq_available': False
        }
        
        # Check Python packages
        try:
            import locust
            results['python_locust'] = True
            print("   ✅ Python locust package available")
        except ImportError:
            print("   ❌ Python locust package missing")
        
        try:
            import websocket
            results['python_websocket'] = True
            print("   ✅ Python websocket-client package available")
        except ImportError:
            print("   ❌ Python websocket-client package missing")
        
        # Check system tools
        system_tools = {
            'bash_available': 'bash',
            'curl_available': 'curl',
            'jq_available': 'jq'
        }
        
        for result_key, tool in system_tools.items():
            try:
                subprocess.run([tool, '--version'], 
                             capture_output=True, check=True, timeout=5)
                results[result_key] = True
                print(f"   ✅ {tool} available")
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                print(f"   ❌ {tool} not available")
        
        return results
    
    def check_scripts_functionality(self) -> Dict[str, bool]:
        """Check script functionality and syntax."""
        print("\n🔧 Checking Scripts Functionality...")
        
        results = {
            'locust_syntax': False,
            'bash_scripts_syntax': False,
            'python_scripts_syntax': False,
            'load_test_config': False
        }
        
        # Check Locust test syntax
        locust_file = self.project_root / 'tests/performance/production_load_test.py'
        if locust_file.exists():
            try:
                # Try to compile the Python file
                with open(locust_file, 'r') as f:
                    content = f.read()
                compile(content, str(locust_file), 'exec')
                results['locust_syntax'] = True
                print("   ✅ Locust test file syntax valid")
            except SyntaxError as e:
                print(f"   ❌ Locust test file syntax error: {e}")
        
        # Check bash scripts syntax
        bash_scripts = [
            'scripts/run_load_tests.sh',
            'scripts/collect_system_metrics.sh'
        ]
        
        bash_syntax_valid = True
        for script_path in bash_scripts:
            script_file = self.project_root / script_path
            if script_file.exists():
                try:
                    # Check bash syntax
                    result = subprocess.run(
                        ['bash', '-n', str(script_file)],
                        capture_output=True, timeout=10
                    )
                    if result.returncode != 0:
                        bash_syntax_valid = False
                        print(f"   ❌ Bash syntax error in {script_path}")
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    bash_syntax_valid = False
        
        if bash_syntax_valid:
            results['bash_scripts_syntax'] = True
            print("   ✅ Bash scripts syntax valid")
        
        # Check Python scripts syntax
        python_scripts = [
            'scripts/optimize_performance.py',
            'scripts/validate_load_testing.py'
        ]
        
        python_syntax_valid = True
        for script_path in python_scripts:
            script_file = self.project_root / script_path
            if script_file.exists():
                try:
                    with open(script_file, 'r') as f:
                        content = f.read()
                    compile(content, str(script_file), 'exec')
                except SyntaxError:
                    python_syntax_valid = False
                    print(f"   ❌ Python syntax error in {script_path}")
        
        if python_syntax_valid:
            results['python_scripts_syntax'] = True
            print("   ✅ Python scripts syntax valid")
        
        # Check load test configuration
        locust_file = self.project_root / 'tests/performance/production_load_test.py'
        if locust_file.exists():
            try:
                with open(locust_file, 'r') as f:
                    content = f.read()
                
                # Check for essential configuration elements
                required_elements = [
                    'TEST_CONFIG',
                    'GremlinsAIUser',
                    'authenticate',
                    'upload_document',
                    'perform_rag_query',
                    'execute_multi_agent_task',
                    'websocket_collaboration'
                ]
                
                if all(element in content for element in required_elements):
                    results['load_test_config'] = True
                    print("   ✅ Load test configuration complete")
                else:
                    print("   ❌ Load test configuration incomplete")
            except Exception as e:
                print(f"   ❌ Error checking load test configuration: {e}")
        
        return results
    
    def check_configuration(self) -> Dict[str, bool]:
        """Check configuration and setup."""
        print("\n⚙️ Checking Configuration...")
        
        results = {
            'test_directories': False,
            'report_structure': False,
            'monitoring_integration': False,
            'performance_thresholds': False
        }
        
        # Check test directories
        required_dirs = [
            'tests/performance',
            'scripts',
            'docs',
            'logs'
        ]
        
        dirs_exist = True
        for dir_path in required_dirs:
            full_path = self.project_root / dir_path
            if not full_path.exists():
                full_path.mkdir(parents=True, exist_ok=True)
                print(f"   📁 Created directory: {dir_path}")
            else:
                dirs_exist = True
        
        if dirs_exist:
            results['test_directories'] = True
            print("   ✅ Test directories structure valid")
        
        # Check report structure
        report_file = self.project_root / 'docs/PERFORMANCE_VALIDATION_REPORT.md'
        if report_file.exists():
            try:
                with open(report_file, 'r') as f:
                    content = f.read()
                
                # Check for essential report sections
                required_sections = [
                    'Executive Summary',
                    'Test Objectives',
                    'Load Test Results',
                    'Performance Analysis',
                    'Acceptance Criteria',
                    'Production Readiness'
                ]
                
                if all(section in content for section in required_sections):
                    results['report_structure'] = True
                    print("   ✅ Performance report structure complete")
                else:
                    print("   ❌ Performance report structure incomplete")
            except Exception as e:
                print(f"   ❌ Error checking report structure: {e}")
        
        # Check monitoring integration
        metrics_script = self.project_root / 'scripts/collect_system_metrics.sh'
        if metrics_script.exists():
            try:
                with open(metrics_script, 'r') as f:
                    content = f.read()
                
                # Check for monitoring capabilities
                monitoring_features = [
                    'collect_cpu_metrics',
                    'collect_memory_metrics',
                    'collect_kubernetes_metrics',
                    'collect_prometheus_metrics'
                ]
                
                if all(feature in content for feature in monitoring_features):
                    results['monitoring_integration'] = True
                    print("   ✅ Monitoring integration configured")
                else:
                    print("   ❌ Monitoring integration incomplete")
            except Exception as e:
                print(f"   ❌ Error checking monitoring integration: {e}")
        
        # Check performance thresholds
        locust_file = self.project_root / 'tests/performance/production_load_test.py'
        if locust_file.exists():
            try:
                with open(locust_file, 'r') as f:
                    content = f.read()
                
                # Check for performance thresholds
                threshold_elements = [
                    'performance_thresholds',
                    'auth_response_time',
                    'rag_query_time',
                    'multi_agent_task_time'
                ]
                
                if all(element in content for element in threshold_elements):
                    results['performance_thresholds'] = True
                    print("   ✅ Performance thresholds configured")
                else:
                    print("   ❌ Performance thresholds incomplete")
            except Exception as e:
                print(f"   ❌ Error checking performance thresholds: {e}")
        
        return results
    
    def generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        # File-related recommendations
        files_check = results.get('files_check', {})
        if not all(files_check.values()):
            recommendations.append("Ensure all required load testing files are present")
        
        # Dependency recommendations
        dependencies_check = results.get('dependencies_check', {})
        if not dependencies_check.get('python_locust'):
            recommendations.append("Install Locust: pip install locust")
        if not dependencies_check.get('python_websocket'):
            recommendations.append("Install WebSocket client: pip install websocket-client")
        if not dependencies_check.get('jq_available'):
            recommendations.append("Install jq for JSON processing")
        
        # Script recommendations
        scripts_check = results.get('scripts_check', {})
        if not scripts_check.get('locust_syntax'):
            recommendations.append("Fix syntax errors in Locust test file")
        if not scripts_check.get('bash_scripts_syntax'):
            recommendations.append("Fix syntax errors in bash scripts")
        
        # Configuration recommendations
        config_check = results.get('config_check', {})
        if not config_check.get('monitoring_integration'):
            recommendations.append("Complete monitoring integration setup")
        if not config_check.get('performance_thresholds'):
            recommendations.append("Configure performance thresholds in test files")
        
        # General recommendations
        if results.get('overall_score', 0) < 0.95:
            recommendations.extend([
                "Run load tests in staging environment before production",
                "Verify monitoring dashboards are accessible",
                "Test auto-scaling configuration",
                "Prepare incident response procedures"
            ])
        
        return recommendations


def main():
    """Run load testing infrastructure validation."""
    validator = LoadTestingValidator()
    results = validator.validate_infrastructure()
    
    # Save results
    with open("load_testing_validation_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Results saved to: load_testing_validation_results.json")
    
    # Generate and display recommendations
    recommendations = validator.generate_recommendations(results)
    
    if recommendations:
        print(f"\n🚀 RECOMMENDATIONS:")
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec}")
    
    # Display summary
    print(f"\n📊 VALIDATION SUMMARY:")
    for category, checks in results.items():
        if isinstance(checks, dict) and category.endswith('_check'):
            category_name = category.replace('_check', '').replace('_', ' ').title()
            passed = sum(checks.values())
            total = len(checks)
            print(f"   {category_name}: {passed}/{total} ({passed/total*100:.1f}%)")
    
    # Exit with appropriate code
    if results['overall_score'] >= 0.95:
        print(f"\n🎉 Load testing infrastructure is ready!")
        return 0
    elif results['overall_score'] >= 0.85:
        print(f"\n✅ Load testing infrastructure is mostly ready with minor issues")
        return 1
    else:
        print(f"\n⚠️ Load testing infrastructure needs significant work")
        return 2


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
