#!/usr/bin/env python3
"""
Production Environment Setup Script

Sets up environment for production-safe operation where stub execution is blocked.
"""

import os
import sys
from pathlib import Path

def setup_production_env():
    """Setup production environment variables"""
    
    print("🔒 SETTING UP PRODUCTION ENVIRONMENT")
    print("=" * 50)
    
    # Set production environment variables
    env_vars = {
        'FAIL_ON_STUB': '1',  # Block stub execution
        'ENVIRONMENT': 'production',
        'LOG_LEVEL': 'INFO'
    }
    
    print("\n📝 Setting environment variables:")
    for key, value in env_vars.items():
        os.environ[key] = value
        print(f"   {key}={value}")
    
    # Verify setup
    print("\n✅ PRODUCTION SETUP VERIFICATION")
    print("-" * 35)
    
    # Add app to path for imports
    app_dir = Path(__file__).parent / "app"
    sys.path.insert(0, str(app_dir))
    
    from app.utils.stub_detection import get_stub_status
    
    status = get_stub_status()
    print(f"Mode: {status['mode']}")
    print(f"Stub blocking enabled: {status['fail_on_stub_enabled']}")
    
    if status['mode'] == 'PRODUCTION':
        print("\n🎉 SUCCESS: Production environment configured")
        print("💡 All stub code will now fail with E-STUB-PATH errors")
        print("🚀 System will only use real API data sources")
        
        print("\n📋 PRODUCTION CHECKLIST:")
        print("   ✅ FAIL_ON_STUB=1 (stubs blocked)")
        print("   ⚠️  Ensure real Schwab API credentials are configured")
        print("   ⚠️  Verify network access to Schwab API endpoints")
        print("   ⚠️  Test authentication before going live")
        
    else:
        print("❌ ERROR: Failed to configure production mode")
        return False
    
    return True

def setup_development_env():
    """Setup development environment variables"""
    
    print("🧪 SETTING UP DEVELOPMENT ENVIRONMENT")
    print("=" * 50)
    
    # Set development environment variables
    env_vars = {
        'FAIL_ON_STUB': '0',  # Allow stub execution
        'ENVIRONMENT': 'development',
        'LOG_LEVEL': 'DEBUG'
    }
    
    print("\n📝 Setting environment variables:")
    for key, value in env_vars.items():
        os.environ[key] = value
        print(f"   {key}={value}")
    
    print("\n✅ DEVELOPMENT SETUP VERIFICATION")
    print("-" * 38)
    
    # Add app to path for imports
    app_dir = Path(__file__).parent / "app"
    sys.path.insert(0, str(app_dir))
    
    from app.utils.stub_detection import get_stub_status
    
    status = get_stub_status()
    print(f"Mode: {status['mode']}")
    print(f"Stub execution allowed: {not status['fail_on_stub_enabled']}")
    
    if status['mode'] == 'DEVELOPMENT':
        print("\n🎉 SUCCESS: Development environment configured")
        print("💡 Stub code execution allowed for testing")
        print("🧪 System will warn about stubs but continue")
        
    else:
        print("❌ ERROR: Failed to configure development mode")
        return False
    
    return True

def main():
    """Main setup function"""
    
    if len(sys.argv) < 2:
        print("Usage: python setup_env.py [production|development]")
        print()
        print("Examples:")
        print("  python setup_env.py production   # Block all stubs")
        print("  python setup_env.py development  # Allow stubs with warnings")
        sys.exit(1)
    
    mode = sys.argv[1].lower()
    
    if mode == 'production':
        success = setup_production_env()
    elif mode == 'development':
        success = setup_development_env()
    else:
        print(f"❌ Unknown mode: {mode}")
        print("Valid modes: production, development")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    
    if success:
        print(f"🎯 {mode.upper()} environment ready!")
        print("💡 Run your Trade Analyst commands now")
    else:
        print(f"❌ Failed to set up {mode} environment")
        sys.exit(1)

if __name__ == "__main__":
    main()
