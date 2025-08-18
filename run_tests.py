#!/usr/bin/env python3
"""
Test runner script for GremlinsAI comprehensive testing framework.

This script provides a convenient way to run different test suites
and generate coverage reports.
"""

import subprocess
import sys
import argparse
import time
from pathlib import Path


def run_command(cmd, description=""):
    """Run a command and return the result."""
    print(f"\n{'='*60}")
    print(f"Running: {description or cmd}")
    print(f"{'='*60}")
    
    start_time = time.time()
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    duration = time.time() - start_time
    
    print(f"Duration: {duration:.2f} seconds")
    print(f"Return code: {result.returncode}")
    
    if result.stdout:
        print("\nSTDOUT:")
        print(result.stdout)
    
    if result.stderr:
        print("\nSTDERR:")
        print(result.stderr)
    
    return result.returncode == 0, result


def run_unit_tests():
    """Run unit tests with coverage."""
    cmd = "python -m pytest tests/unit/ -v --cov=app --cov-report=term-missing --cov-report=html --cov-report=xml"
    return run_command(cmd, "Unit Tests with Coverage")


def run_integration_tests():
    """Run integration tests."""
    cmd = "python -m pytest tests/integration/ -v --tb=short"
    return run_command(cmd, "Integration Tests")


def run_e2e_tests():
    """Run end-to-end tests."""
    cmd = "python -m pytest tests/e2e/ -v --tb=short"
    return run_command(cmd, "End-to-End Tests")


def run_performance_tests():
    """Run performance tests."""
    cmd = "python -m pytest tests/performance/ -v --tb=short"
    return run_command(cmd, "Performance Tests")


def run_all_tests():
    """Run all test suites."""
    cmd = "python -m pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html --cov-report=xml --tb=short"
    return run_command(cmd, "All Tests with Coverage")


def run_quick_tests():
    """Run a quick subset of tests for development."""
    cmd = "python -m pytest tests/unit/ -x --tb=short --maxfail=3"
    return run_command(cmd, "Quick Unit Tests (fail fast)")


def check_code_quality():
    """Run code quality checks."""
    commands = [
        ("python -m black --check app/ tests/", "Black formatting check"),
        ("python -m isort --check-only app/ tests/", "Import sorting check"),
        ("python -m flake8 app/ tests/ --max-line-length=120", "Flake8 linting")
    ]
    
    all_passed = True
    for cmd, desc in commands:
        success, _ = run_command(cmd, desc)
        if not success:
            all_passed = False
    
    return all_passed


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="GremlinsAI Test Runner")
    parser.add_argument(
        "suite",
        choices=["unit", "integration", "e2e", "performance", "all", "quick", "quality"],
        help="Test suite to run"
    )
    parser.add_argument(
        "--coverage-threshold",
        type=float,
        default=50.0,
        help="Minimum coverage threshold (default: 50.0)"
    )
    
    args = parser.parse_args()
    
    print(f"GremlinsAI Test Runner")
    print(f"Running: {args.suite} tests")
    print(f"Coverage threshold: {args.coverage_threshold}%")
    
    # Run the selected test suite
    if args.suite == "unit":
        success, result = run_unit_tests()
    elif args.suite == "integration":
        success, result = run_integration_tests()
    elif args.suite == "e2e":
        success, result = run_e2e_tests()
    elif args.suite == "performance":
        success, result = run_performance_tests()
    elif args.suite == "all":
        success, result = run_all_tests()
    elif args.suite == "quick":
        success, result = run_quick_tests()
    elif args.suite == "quality":
        success = check_code_quality()
        result = None
    else:
        print(f"Unknown test suite: {args.suite}")
        sys.exit(1)
    
    # Check coverage if applicable
    if args.suite in ["unit", "all"] and success:
        coverage_file = Path("coverage.xml")
        if coverage_file.exists():
            try:
                import xml.etree.ElementTree as ET
                tree = ET.parse(coverage_file)
                root = tree.getroot()
                coverage = float(root.attrib['line-rate']) * 100
                
                print(f"\n{'='*60}")
                print(f"COVERAGE REPORT")
                print(f"{'='*60}")
                print(f"Current coverage: {coverage:.1f}%")
                print(f"Threshold: {args.coverage_threshold}%")
                
                if coverage >= args.coverage_threshold:
                    print("✅ Coverage threshold met!")
                else:
                    print("❌ Coverage below threshold!")
                    success = False
                    
            except Exception as e:
                print(f"Error reading coverage report: {e}")
    
    # Final result
    print(f"\n{'='*60}")
    print(f"FINAL RESULT")
    print(f"{'='*60}")
    
    if success:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
