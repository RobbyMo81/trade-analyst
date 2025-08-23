"""
Stub Detection and Production Safety Module

Ensures production systems never use stub/synthetic data by default.
Environment variable FAIL_ON_STUB=1 (default) causes hard failure when stub code executes.
"""

import os
import logging
from typing import Optional, Any, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class StubExecutionError(Exception):
    """Raised when stub code executes in production mode"""
    pass


def check_stub_execution(stub_name: str, context: Optional[Dict[str, Any]] = None) -> None:
    """
    Check if stub execution is allowed, raise exception if not.
    
    Args:
        stub_name: Name/identifier of the stub being executed
        context: Optional context information for debugging
        
    Raises:
        StubExecutionError: If FAIL_ON_STUB=1 and stub code is executed
    """
    fail_on_stub = os.environ.get('FAIL_ON_STUB', '1').lower() in ('1', 'true', 'yes', 'on')
    
    if fail_on_stub:
        error_msg = f"E-STUB-PATH: Production system attempted to execute stub code: {stub_name}"
        
        if context:
            error_msg += f" | Context: {context}"
        
        logger.error(error_msg)
        logger.error("Set FAIL_ON_STUB=0 to allow stub execution in development")
        
        raise StubExecutionError(error_msg)
    else:
        logger.warning(f"STUB EXECUTION ALLOWED: {stub_name} (FAIL_ON_STUB={os.environ.get('FAIL_ON_STUB', '1')})")
        if context:
            logger.warning(f"Stub context: {context}")


def is_production_mode() -> bool:
    """Check if running in production mode (FAIL_ON_STUB=1)"""
    return os.environ.get('FAIL_ON_STUB', '1').lower() in ('1', 'true', 'yes', 'on')


def log_stub_warning(stub_name: str, replacement_suggestion: str = "") -> None:
    """Log warning about stub usage"""
    warning_msg = f"WARNING: Using stub implementation: {stub_name}"
    if replacement_suggestion:
        warning_msg += f" | Suggestion: {replacement_suggestion}"
    
    logger.warning(warning_msg)


def get_stub_status() -> Dict[str, Any]:
    """Get current stub execution policy status"""
    fail_on_stub = os.environ.get('FAIL_ON_STUB', '1')
    
    return {
        'fail_on_stub_enabled': is_production_mode(),
        'fail_on_stub_env_var': fail_on_stub,
        'mode': 'PRODUCTION' if is_production_mode() else 'DEVELOPMENT',
        'timestamp': datetime.now().isoformat()
    }


def validate_no_stub_execution():
    """Decorator/utility to mark functions that should never execute stubs"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Force production mode for this function
            original_env = os.environ.get('FAIL_ON_STUB')
            os.environ['FAIL_ON_STUB'] = '1'
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                # Restore original environment
                if original_env is None:
                    os.environ.pop('FAIL_ON_STUB', None)
                else:
                    os.environ['FAIL_ON_STUB'] = original_env
        
        return wrapper
    return decorator


# Export key functions
__all__ = [
    'StubExecutionError',
    'check_stub_execution', 
    'is_production_mode',
    'log_stub_warning',
    'get_stub_status',
    'validate_no_stub_execution'
]
