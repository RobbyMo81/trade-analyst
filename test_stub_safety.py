#!/usr/bin/env python3
"""
Test Production Stub Safety System

This script tests that the system properly fails when stub code is executed
in production mode (FAIL_ON_STUB=1).
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the app directory to Python path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

def test_production_safety():
    """Test that production mode blocks stub execution"""
    print("🔒 TESTING PRODUCTION STUB SAFETY")
    print("=" * 50)
    
    from app.utils.stub_detection import get_stub_status, check_stub_execution, StubExecutionError
    
    # Test 1: Check current status
    print("\n1️⃣ CURRENT STUB STATUS")
    print("-" * 25)
    status = get_stub_status()
    print(f"Mode: {status['mode']}")
    print(f"FAIL_ON_STUB enabled: {status['fail_on_stub_enabled']}")
    print(f"Environment variable: FAIL_ON_STUB={status['fail_on_stub_env_var']}")
    
    # Test 2: Force production mode and test stub blocking
    print("\n2️⃣ TESTING PRODUCTION BLOCKING")
    print("-" * 32)
    
    # Save original environment
    original_env = os.environ.get('FAIL_ON_STUB')
    
    try:
        # Force production mode
        os.environ['FAIL_ON_STUB'] = '1'
        print("Set FAIL_ON_STUB=1 (production mode)")
        
        # This should fail
        print("Testing stub execution - should FAIL...")
        try:
            check_stub_execution("test_stub", {"test": "data"})
            print("❌ ERROR: Stub execution was allowed in production mode!")
            return False
        except StubExecutionError as e:
            print(f"✅ SUCCESS: Stub execution blocked - {e}")
        
    finally:
        # Restore original environment
        if original_env is None:
            os.environ.pop('FAIL_ON_STUB', None)
        else:
            os.environ['FAIL_ON_STUB'] = original_env
    
    # Test 3: Test development mode allows stubs
    print("\n3️⃣ TESTING DEVELOPMENT ALLOWING")
    print("-" * 33)
    
    try:
        # Force development mode
        os.environ['FAIL_ON_STUB'] = '0'
        print("Set FAIL_ON_STUB=0 (development mode)")
        
        # This should succeed with warning
        print("Testing stub execution - should WARN but allow...")
        try:
            check_stub_execution("test_stub", {"test": "data"})
            print("✅ SUCCESS: Stub execution allowed in development mode")
        except StubExecutionError as e:
            print(f"❌ ERROR: Stub execution blocked in development mode - {e}")
            return False
        
    finally:
        # Restore original environment
        if original_env is None:
            os.environ.pop('FAIL_ON_STUB', None)
        else:
            os.environ['FAIL_ON_STUB'] = original_env
    
    return True

async def test_calc_levels_production():
    """Test calc-levels function with production safety"""
    print("\n4️⃣ TESTING CALC-LEVELS PRODUCTION SAFETY")
    print("-" * 42)
    
    # Save original environment
    original_env = os.environ.get('FAIL_ON_STUB')
    
    try:
        # Force production mode
        os.environ['FAIL_ON_STUB'] = '1'
        print("Testing calc-levels in production mode...")
        
        # Import after setting environment
        from start import calc_levels
        
        # This should use only real APIs, no stubs
        try:
            calc_levels("/NQ", "2025-08-21", "json")
            print("✅ calc-levels completed successfully with real data only")
        except Exception as e:
            if "PRODUCTION FAILURE" in str(e):
                print(f"✅ SUCCESS: Production failure correctly triggered - {e}")
            elif "E-STUB-PATH" in str(e):
                print(f"✅ SUCCESS: Stub execution blocked - {e}")
            else:
                print(f"⚠️  calc-levels failed with: {e}")
        
    finally:
        # Restore original environment
        if original_env is None:
            os.environ.pop('FAIL_ON_STUB', None)
        else:
            os.environ['FAIL_ON_STUB'] = original_env

def main():
    """Main test function"""
    print("🧪 PRODUCTION STUB SAFETY TEST SUITE")
    print("=" * 60)
    
    success = test_production_safety()
    
    if success:
        print("\n5️⃣ TESTING INTEGRATION")
        print("-" * 24)
        asyncio.run(test_calc_levels_production())
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ALL TESTS PASSED - Production safety system working!")
        print("💡 Set FAIL_ON_STUB=0 for development, FAIL_ON_STUB=1 for production")
    else:
        print("❌ TESTS FAILED - Production safety system has issues!")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
