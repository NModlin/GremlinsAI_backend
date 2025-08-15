#!/usr/bin/env python3
# Make the script executable
import stat
"""
GremlinsAI Backend Test Runner

Comprehensive test runner for the GremlinsAI backend test suite.
Supports running different test categories and provides detailed reporting.

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --unit             # Run only unit tests
    python run_tests.py --integration      # Run only integration tests
    python run_tests.py --e2e              # Run only end-to-end tests
    python run_tests.py --performance      # Run only performance tests
    python run_tests.py --fast             # Run fast tests only (exclude slow/performance)
    python run_tests.py --coverage         # Run with coverage report
    python run_tests.py --verbose          # Verbose output
"""

import os
import sys
import argparse
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Any


def setup_test_environment():
    """Set up the test environment."""
    # Set environment variables for testing
    os.environ["TESTING"] = "true"
    os.environ["PYTHONPATH"] = str(Path.cwd())
    
    # Load test environment variables
    env_test_file = Path(".env.test")
    if env_test_file.exists():
        print("Loading test environment variables from .env.test")
        with open(env_test_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value
    
    # Ensure test data directory exists
    Path("data").mkdir(exist_ok=True)
    
    print("Test environment setup complete")


def run_pytest_command(args: List[str]) -> Dict[str, Any]:
    """Run pytest with given arguments and return results."""
    cmd = ["python", "-m", "pytest"] + args
    
    print(f"Running command: {' '.join(cmd)}")
    print("-" * 80)
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=False,  # Show output in real-time
            text=True,
            cwd=Path.cwd()
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        return {
            "success": result.returncode == 0,
            "return_code": result.returncode,
            "duration": duration,
            "command": " ".join(cmd)
        }
        
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"Error running tests: {e}")
        return {
            "success": False,
            "return_code": -1,
            "duration": duration,
            "error": str(e),
            "command": " ".join(cmd)
        }


def run_unit_tests(verbose: bool = False, coverage: bool = False) -> Dict[str, Any]:
    """Run unit tests."""
    print("\n🧪 Running Unit Tests")
    print("=" * 50)
    
    args = ["tests/unit/", "-m", "unit"]
    
    if verbose:
        args.append("-v")
    
    if coverage:
        args.extend(["--cov=app", "--cov-report=term-missing"])
    
    return run_pytest_command(args)


def run_integration_tests(verbose: bool = False) -> Dict[str, Any]:
    """Run integration tests."""
    print("\n🔗 Running Integration Tests")
    print("=" * 50)
    
    args = ["tests/integration/", "-m", "integration"]
    
    if verbose:
        args.append("-v")
    
    return run_pytest_command(args)


def run_e2e_tests(verbose: bool = False) -> Dict[str, Any]:
    """Run end-to-end tests."""
    print("\n🎯 Running End-to-End Tests")
    print("=" * 50)
    
    args = ["tests/e2e/", "-m", "e2e"]
    
    if verbose:
        args.append("-v")
    
    return run_pytest_command(args)


def run_performance_tests(verbose: bool = False) -> Dict[str, Any]:
    """Run performance tests."""
    print("\n⚡ Running Performance Tests")
    print("=" * 50)
    
    args = ["tests/performance/", "-m", "performance"]
    
    if verbose:
        args.append("-v")
    
    return run_pytest_command(args)


def run_fast_tests(verbose: bool = False, coverage: bool = False) -> Dict[str, Any]:
    """Run fast tests (exclude slow and performance tests)."""
    print("\n🚀 Running Fast Tests")
    print("=" * 50)
    
    args = ["tests/", "-m", "not slow and not performance"]
    
    if verbose:
        args.append("-v")
    
    if coverage:
        args.extend(["--cov=app", "--cov-report=term-missing"])
    
    return run_pytest_command(args)


def run_all_tests(verbose: bool = False, coverage: bool = False) -> Dict[str, Any]:
    """Run all tests."""
    print("\n🎪 Running All Tests")
    print("=" * 50)
    
    args = ["tests/"]
    
    if verbose:
        args.append("-v")
    
    if coverage:
        args.extend(["--cov=app", "--cov-report=term-missing", "--cov-report=html"])
    
    return run_pytest_command(args)


def print_test_summary(results: List[Dict[str, Any]]):
    """Print a summary of test results."""
    print("\n" + "=" * 80)
    print("🏁 TEST SUMMARY")
    print("=" * 80)
    
    total_duration = sum(r["duration"] for r in results)
    successful_runs = [r for r in results if r["success"]]
    failed_runs = [r for r in results if not r["success"]]
    
    print(f"Total test runs: {len(results)}")
    print(f"Successful runs: {len(successful_runs)}")
    print(f"Failed runs: {len(failed_runs)}")
    print(f"Total duration: {total_duration:.2f} seconds")
    
    if successful_runs:
        print("\n✅ Successful test runs:")
        for result in successful_runs:
            print(f"  - {result['command']} ({result['duration']:.2f}s)")
    
    if failed_runs:
        print("\n❌ Failed test runs:")
        for result in failed_runs:
            print(f"  - {result['command']} (exit code: {result['return_code']}, {result['duration']:.2f}s)")
            if "error" in result:
                print(f"    Error: {result['error']}")
    
    # Overall status
    if failed_runs:
        print(f"\n❌ TESTS FAILED - {len(failed_runs)} test run(s) failed")
        return False
    else:
        print(f"\n✅ ALL TESTS PASSED - {len(successful_runs)} test run(s) successful")
        return True


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(
        description="GremlinsAI Backend Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Test category options
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--e2e", action="store_true", help="Run end-to-end tests only")
    parser.add_argument("--performance", action="store_true", help="Run performance tests only")
    parser.add_argument("--fast", action="store_true", help="Run fast tests only (exclude slow/performance)")
    
    # Options
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--no-setup", action="store_true", help="Skip test environment setup")
    
    args = parser.parse_args()
    
    # Setup test environment
    if not args.no_setup:
        setup_test_environment()
    
    # Determine which tests to run
    results = []
    
    if args.unit:
        results.append(run_unit_tests(args.verbose, args.coverage))
    elif args.integration:
        results.append(run_integration_tests(args.verbose))
    elif args.e2e:
        results.append(run_e2e_tests(args.verbose))
    elif args.performance:
        results.append(run_performance_tests(args.verbose))
    elif args.fast:
        results.append(run_fast_tests(args.verbose, args.coverage))
    else:
        # Run all tests by default
        results.append(run_all_tests(args.verbose, args.coverage))
    
    # Print summary and exit with appropriate code
    success = print_test_summary(results)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
