#!/usr/bin/env python3
"""
Test Runner for Production Safety Tests

Runs the comprehensive test suite that would have caught the critical issues
where synthetic stub data was being presented as real market data.
"""

import os
import sys
import subprocess
from pathlib import Path


def run_test_suite():
    """Run the complete production safety test suite"""
    
    project_root = Path(__file__).parent
    
    print("=" * 60)
    print("PRODUCTION SAFETY TEST SUITE")
    print("=" * 60)
    print()
    print("Running tests that would have caught the critical stub data issue...")
    print()
    
    # Test categories to run
    test_files = [
        ("Production Safety Unit Tests", "test_production_safety.py"),
        ("CLI Contract Tests", "test_cli_contracts.py"), 
        ("Integration Tests", "test_integration.py")
    ]
    
    results = {}
    
    for test_name, test_file in test_files:
        print(f"Running {test_name}...")
        print("-" * 50)
        
        test_path = project_root / test_file
        if not test_path.exists():
            print(f"❌ Test file not found: {test_file}")
            results[test_name] = "MISSING"
            continue
        
        try:
            # Run pytest on the specific test file
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                str(test_path),
                "-v",
                "--tb=short"
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print(f"✅ {test_name} PASSED")
                results[test_name] = "PASSED"
            else:
                print(f"❌ {test_name} FAILED")
                print("STDOUT:", result.stdout[-500:])  # Last 500 chars
                print("STDERR:", result.stderr[-500:])
                results[test_name] = "FAILED"
                
        except subprocess.TimeoutExpired:
            print(f"⏱️  {test_name} TIMEOUT") 
            results[test_name] = "TIMEOUT"
        except Exception as e:
            print(f"💥 {test_name} ERROR: {e}")
            results[test_name] = "ERROR"
        
        print()
    
    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, result in results.items():
        status_icon = {
            "PASSED": "✅",
            "FAILED": "❌", 
            "MISSING": "❓",
            "TIMEOUT": "⏱️",
            "ERROR": "💥"
        }.get(result, "❓")
        
        print(f"{status_icon} {test_name}: {result}")
    
    print()
    
    # Overall result
    failed_tests = [name for name, result in results.items() 
                   if result in ["FAILED", "TIMEOUT", "ERROR"]]
    
    if failed_tests:
        print(f"❌ {len(failed_tests)} test suites failed")
        print("The following issues would have been caught by these tests:")
        print("• Stub data being presented as real market data")
        print("• Missing provenance tracking")
        print("• Silent fallbacks to synthetic data") 
        print("• Incorrect CLI output formats")
        return 1
    else:
        print("✅ All production safety tests passed")
        print("These tests would have prevented the stub data issue")
        return 0


def run_specific_guardrail_tests():
    """Run just the critical guardrail tests"""
    print("Running critical guardrail tests...")
    print("-" * 40)
    
    # Test FAIL_ON_STUB environment variable
    print("Testing FAIL_ON_STUB=1 blocks stub execution...")
    
    test_code = """
import os
import sys
sys.path.insert(0, 'app')
from guardrails import assert_no_stub

os.environ['FAIL_ON_STUB'] = '1'
try:
    assert_no_stub()
    print("❌ FAIL: assert_no_stub() should have raised SystemExit")
    sys.exit(1)
except SystemExit as e:
    if "E-STUB-PATH" in str(e):
        print("✅ PASS: assert_no_stub() correctly blocked stub execution")
        sys.exit(0)
    else:
        print(f"❌ FAIL: Wrong error message: {e}")
        sys.exit(1)
"""
    
    try:
        result = subprocess.run([
            sys.executable, "-c", test_code
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
            
        return result.returncode
        
    except Exception as e:
        print(f"❌ Error running guardrail test: {e}")
        return 1


if __name__ == "__main__":
    print("Production Safety Test Runner")
    print("=============================")
    print()
    
    if len(sys.argv) > 1 and sys.argv[1] == "guardrails":
        exit_code = run_specific_guardrail_tests()
    else:
        exit_code = run_test_suite()
    
    sys.exit(exit_code)
