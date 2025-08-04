#!/usr/bin/env python3
"""Test runner script for GitLab tools."""

import sys
import subprocess
from pathlib import Path

def run_tests():
    """Run all tests with pytest."""
    
    print("GitLab Tools Test Suite")
    print("=" * 60)
    print()
    
    # Test categories
    test_suites = {
        "Unit Tests - API": "tests/unit/api",
        "Unit Tests - Models": "tests/unit/models", 
        "Unit Tests - Services": "tests/unit/services",
        "Unit Tests - Scripts": "tests/unit/scripts",
        "Unit Tests - Utils": "tests/unit/utils",
        "Integration Tests": "tests/integration"
    }
    
    # Check if pytest is available
    try:
        subprocess.run([sys.executable, "-m", "pytest", "--version"], 
                      capture_output=True, check=True)
    except subprocess.CalledProcessError:
        print("ERROR: pytest is not installed!")
        print("Please install it with: pip install pytest pytest-cov pytest-mock")
        return 1
    
    # Run each test suite
    total_passed = 0
    total_failed = 0
    
    for suite_name, suite_path in test_suites.items():
        if not Path(suite_path).exists():
            print(f"⚠️  Skipping {suite_name} (path not found)")
            continue
            
        print(f"\n{'='*60}")
        print(f"Running {suite_name}")
        print(f"{'='*60}")
        
        cmd = [
            sys.executable, "-m", "pytest",
            suite_path,
            "-v",  # Verbose
            "--tb=short",  # Short traceback
            "--no-header",  # No pytest header
            "-q"  # Quiet mode
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Parse output for results
            output_lines = result.stdout.split('\n')
            for line in output_lines:
                if 'passed' in line or 'failed' in line:
                    print(line)
                    
            if result.returncode == 0:
                print(f"✅ {suite_name} - All tests passed!")
            else:
                print(f"❌ {suite_name} - Some tests failed!")
                print("\nFailure details:")
                print(result.stdout)
                if result.stderr:
                    print("Errors:")
                    print(result.stderr)
                    
        except Exception as e:
            print(f"❌ Error running {suite_name}: {e}")
    
    # Run all tests with coverage
    print(f"\n{'='*60}")
    print("Running all tests with coverage report")
    print(f"{'='*60}")
    
    coverage_cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "--cov=src",
        "--cov=scripts",
        "--cov-report=term-missing",
        "--cov-report=html",
        "-v"
    ]
    
    try:
        subprocess.run(coverage_cmd)
        print("\n✅ Coverage report generated in htmlcov/index.html")
    except:
        print("\n⚠️  Could not generate coverage report")
        print("Install coverage with: pip install pytest-cov")
    
    return 0


def run_specific_test(test_path):
    """Run a specific test file or directory."""
    cmd = [
        sys.executable, "-m", "pytest",
        test_path,
        "-v",
        "--tb=short"
    ]
    
    return subprocess.run(cmd).returncode


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run specific test
        sys.exit(run_specific_test(sys.argv[1]))
    else:
        # Run all tests
        sys.exit(run_tests())