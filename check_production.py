#!/usr/bin/env python3
"""Simple production mode verification"""
import os
import sys
from pathlib import Path

# Set production mode
os.environ['FAIL_ON_STUB'] = '1'

# Add app to path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

try:
    from utils.stub_detection import get_stub_status
    
    status = get_stub_status()
    print('🔒 PRODUCTION STUB SAFETY STATUS')
    print('=' * 40)
    print(f'Mode: {status["mode"]}')
    print(f'FAIL_ON_STUB: {status["fail_on_stub_env_var"]}')
    print(f'Stub blocking enabled: {status["fail_on_stub_enabled"]}')
    
    if status['mode'] == 'PRODUCTION':
        print()
        print('✅ SUCCESS: Production mode active')
        print('🚫 All stub code will fail with E-STUB-PATH')
    else:
        print('❌ Production mode not active')
        
except Exception as e:
    print(f'Error: {e}')
    print('Trying to import stub detection directly...')
    
    # Try direct import
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "stub_detection", 
        Path(__file__).parent / "app" / "utils" / "stub_detection.py"
    )
    stub_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stub_module)
    
    status = stub_module.get_stub_status()
    print(f'Production mode: {status["mode"]}')
