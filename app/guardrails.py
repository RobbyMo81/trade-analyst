"""
Production Guardrails for Trade Analyst

Ensures no stub code paths in production and provides error handling utilities.
Uses the structured error taxonomy (E-* codes) for consistent error handling.
"""

import os
import sys
from typing import Any, Dict, Optional
from .errors import ErrorCode, fail_with_error, fail_stub_path_error, fail_config_error


def assert_no_stub():
    """Assert that stub code paths are not allowed in this environment."""
    # Default to FAIL_ON_STUB=1 (production mode) unless explicitly overridden
    if os.getenv("FAIL_ON_STUB", "1") == "1":
        fail_stub_path_error("stub code path is disabled in this environment")


def require(condition: bool, code: str, msg: str):
    """
    Require a condition or fail fast with explicit error code.
    
    Note: This function maintains backward compatibility with legacy error codes.
    New code should use the structured error functions from app.errors module.
    """
    if not condition:
        # Map legacy codes to new error taxonomy where possible
        if code == "E-STUB-PATH":
            fail_stub_path_error(msg)
        elif code == "E-AUTH":
            from .errors import fail_auth_error
            fail_auth_error(msg)
        elif code == "E-CONFIG":
            fail_config_error(msg)
        elif code in ["E-NODATA-DAILY", "E-NODATA-INTRADAY"]:
            # Let the specific error handlers deal with these
            print(f"{code}: {msg}", file=sys.stderr)
            exit_code = 4 if "DAILY" in code else 1
            raise SystemExit(exit_code)
        else:
            # Generic fallback for other legacy codes
            print(f"{code}: {msg}", file=sys.stderr)
            raise SystemExit(2)


def provenance_stderr(**kv):
    """Write provenance information to STDERR for AI-block format."""
    items = " ".join(f"{k}={v if v is not None else 'N/A'}" for k, v in kv.items())
    print(f"PROVENANCE {items}", file=sys.stderr)


def fail_fast(code: str, msg: str) -> None:
    """
    Fail immediately with error code and message.
    
    Note: This function maintains backward compatibility with legacy error codes.
    New code should use the structured error functions from app.errors module.
    """
    if code == "E-STUB-PATH":
        fail_stub_path_error(msg)
    elif code == "E-CONFIG":
        fail_config_error(msg)
    elif code == "E-INVALID-FORMAT":
        from .errors import fail_format_error
        fail_format_error(msg)
    elif code == "E-AUTH":
        from .errors import fail_auth_error
        fail_auth_error(msg)
    else:
        # Generic fallback for other legacy codes
        print(f"{code}: {msg}", file=sys.stderr)
        raise SystemExit(2)


class ProductionSafetyError(Exception):
    """Exception raised when production safety checks fail."""
    
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def validate_environment():
    """Validate that the environment is properly configured for production."""
    errors = []
    
    # Check if running in production mode
    fail_on_stub = os.getenv("FAIL_ON_STUB", "1")
    if fail_on_stub not in ["0", "1"]:
        errors.append("FAIL_ON_STUB must be '0' or '1'")
    
    if errors:
        for error in errors:
            print(f"E-CONFIG: {error}", file=sys.stderr)
        raise SystemExit(2)
    
    return {
        "fail_on_stub": fail_on_stub == "1",
        "environment": "production" if fail_on_stub == "1" else "development"
    }


def create_provenance_data(
    provider: str,
    is_synthetic: bool,
    vwap_method: str,
    provider_request_id: Optional[str] = None,
    source_session: Optional[str] = None
) -> Dict[str, Any]:
    """Create standardized provenance data structure."""
    from datetime import datetime
    
    provenance = {
        "data_source": provider,
        "is_synthetic": is_synthetic,
        "vwap_method": vwap_method,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    if provider_request_id:
        provenance["provider_request_id"] = provider_request_id
    
    if source_session:
        provenance["source_session"] = source_session
    
    return provenance


def emit_provenance(format_type: str, **provenance_data):
    """Emit provenance information in the appropriate format."""
    if format_type == "ai-block":
        provenance_stderr(**provenance_data)
    # For JSON/CSV formats, provenance is embedded in the data structure
    # and handled by the caller
