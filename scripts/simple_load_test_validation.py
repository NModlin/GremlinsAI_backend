#!/usr/bin/env python3
"""
Simple Load Testing Validation Script
Phase 4, Task 4.4: Load Testing & Optimization

This script provides a simplified validation of the load testing infrastructure
that works across different operating systems.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any

class SimpleLoadTestValidator:
    """Simple load testing infrastructure validator."""
    
    def __init__(self):
        """Initialize validator."""
        self.project_root = Path(__file__).parent.parent
        
    def validate_infrastructure(self) -> Dict[str, Any]:
        """Validate load testing infrastructure."""
        print("🔍 GremlinsAI Load Testing Infrastructure Validation")
        print("=" * 60)
        
        # Check files
        files_check = self.check_files()
        
        # Check Python dependencies
        deps_check = self.check_python_dependencies()
        
        # Check configuration
        config_check = self.check_basic_configuration()
        
        # Calculate score
        all_checks = [files_check, deps_check, config_check]
        total_tests = sum(len(check.values()) for check in all_checks)
        passed_tests = sum(sum(check.values()) for check in all_checks)
        
        overall_score = passed_tests / total_tests if total_tests > 0 else 0
        
        print(f"\n📈 OVERALL SCORE: {overall_score:.1%}")
        print(f"📊 Tests Passed: {passed_tests}/{total_tests}")
        
        if overall_score >= 0.9:
            status = "READY"
            print(f"\n🎉 STATUS: {status}")
        elif overall_score >= 0.7:
            status = "MOSTLY_READY"
            print(f"\n✅ STATUS: {status}")
        else:
            status = "NOT_READY"
            print(f"\n⚠️ STATUS: {status}")
        
        return {
            "overall_score": overall_score,
            "status": status,
            "files_check": files_check,
            "deps_check": deps_check,
            "config_check": config_check,
            "passed_tests": passed_tests,
            "total_tests": total_tests
        }
    
    def check_files(self) -> Dict[str, bool]:
        """Check for required files."""
        print("\n📁 Checking Required Files...")
        
        required_files = {
            'locust_test': 'tests/performance/production_load_test.py',
            'load_runner': 'scripts/run_load_tests.sh',
            'metrics_collector': 'scripts/collect_system_metrics.sh',
            'optimizer': 'scripts/optimize_performance.py',
            'report_template': 'docs/PERFORMANCE_VALIDATION_REPORT.md'
        }
        
        results = {}
        for name, path in required_files.items():
            file_path = self.project_root / path
            exists = file_path.exists()
            results[name] = exists
            
            status = "✅" if exists else "❌"
            print(f"   {status} {name}: {path}")
        
        return results
    
    def check_python_dependencies(self) -> Dict[str, bool]:
        """Check Python dependencies."""
        print("\n📦 Checking Python Dependencies...")
        
        results = {
            'locust_available': False,
            'websocket_available': False,
            'json_available': True,  # Built-in
            'pathlib_available': True  # Built-in
        }
        
        # Check Locust
        try:
            import locust
            results['locust_available'] = True
            print("   ✅ Locust package available")
        except ImportError:
            print("   ❌ Locust package missing (pip install locust)")
        
        # Check WebSocket
        try:
            import websocket
            results['websocket_available'] = True
            print("   ✅ WebSocket client available")
        except ImportError:
            print("   ❌ WebSocket client missing (pip install websocket-client)")
        
        print("   ✅ JSON support available")
        print("   ✅ Path handling available")
        
        return results
    
    def check_basic_configuration(self) -> Dict[str, bool]:
        """Check basic configuration."""
        print("\n⚙️ Checking Configuration...")
        
        results = {
            'test_directory': False,
            'scripts_directory': False,
            'docs_directory': False,
            'locust_config': False
        }
        
        # Check directories
        test_dir = self.project_root / 'tests/performance'
        if test_dir.exists():
            results['test_directory'] = True
            print("   ✅ Test directory exists")
        else:
            print("   ❌ Test directory missing")
        
        scripts_dir = self.project_root / 'scripts'
        if scripts_dir.exists():
            results['scripts_directory'] = True
            print("   ✅ Scripts directory exists")
        else:
            print("   ❌ Scripts directory missing")
        
        docs_dir = self.project_root / 'docs'
        if docs_dir.exists():
            results['docs_directory'] = True
            print("   ✅ Docs directory exists")
        else:
            print("   ❌ Docs directory missing")
        
        # Check Locust configuration
        locust_file = self.project_root / 'tests/performance/production_load_test.py'
        if locust_file.exists():
            try:
                with open(locust_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Check for key components
                if all(component in content for component in [
                    'GremlinsAIUser', 'HttpUser', 'task', 'authenticate'
                ]):
                    results['locust_config'] = True
                    print("   ✅ Locust configuration valid")
                else:
                    print("   ❌ Locust configuration incomplete")
            except Exception as e:
                print(f"   ❌ Error reading Locust file: {e}")
        
        return results


def main():
    """Run validation."""
    validator = SimpleLoadTestValidator()
    results = validator.validate_infrastructure()
    
    # Save results
    with open("load_test_validation.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Results saved to: load_test_validation.json")
    
    # Show recommendations
    print(f"\n🚀 RECOMMENDATIONS:")
    
    if not results['deps_check'].get('locust_available'):
        print("   1. Install Locust: pip install locust")
    
    if not results['deps_check'].get('websocket_available'):
        print("   2. Install WebSocket client: pip install websocket-client")
    
    if results['overall_score'] < 1.0:
        print("   3. Address missing files and configuration issues")
    
    print("   4. Test load testing scripts in staging environment")
    print("   5. Configure monitoring dashboards")
    print("   6. Prepare production deployment checklist")
    
    # Summary by category
    print(f"\n📊 DETAILED RESULTS:")
    for category, checks in results.items():
        if isinstance(checks, dict):
            category_name = category.replace('_check', '').replace('_', ' ').title()
            passed = sum(checks.values())
            total = len(checks)
            print(f"   {category_name}: {passed}/{total} ({passed/total*100:.1f}%)")
    
    return 0 if results['overall_score'] >= 0.9 else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
