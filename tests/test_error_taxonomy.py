"""
Test the error taxonomy and structured error handling system
"""

import json
import pytest
from pathlib import Path
import sys

# Add app to path for imports
repo_root = Path(__file__).parent.parent
app_dir = repo_root / "app"
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(app_dir))

from app.errors import (
    ErrorCode, RetryStrategy, ERROR_TAXONOMY, create_error_envelope,
    fail_auth_error, fail_config_error, fail_stub_path_error,
    fail_no_daily_data, fail_no_intraday_data, fail_format_error,
    create_telemetry_context, get_error_info, is_retryable, should_refresh_auth
)


def test_error_code_enum():
    """Test that all error codes are properly defined"""
    expected_codes = [
        "E-AUTH", "E-CONFIG", "E-STUB-PATH", "E-TIMEOUT", "E-NETWORK",
        "E-RATE-LIMIT", "E-PROVIDER-HTTP", "E-PROVIDER-PARSE", "E-CALENDAR",
        "E-SESSION", "E-ROLL", "E-NODATA-DAILY", "E-NODATA-INTRADAY",
        "E-FORMAT", "E-VALIDATION", "E-SCHEMA", "E-UNKNOWN"
    ]
    
    for code in expected_codes:
        assert hasattr(ErrorCode, code.replace("-", "_"))
        assert ErrorCode[code.replace("-", "_")].value == code


def test_error_taxonomy_completeness():
    """Test that all error codes have taxonomy entries"""
    for error_code in ErrorCode:
        assert error_code in ERROR_TAXONOMY
        error_info = ERROR_TAXONOMY[error_code]
        assert error_info.code == error_code
        assert error_info.meaning
        assert error_info.when_to_use
        assert isinstance(error_info.retry_strategy, RetryStrategy)
        assert isinstance(error_info.cli_exit_code, int)


def test_exit_codes():
    """Test that exit codes match specifications"""
    expected_exit_codes = {
        ErrorCode.E_AUTH: 2,
        ErrorCode.E_CONFIG: 2,
        ErrorCode.E_STUB_PATH: 2,
        ErrorCode.E_TIMEOUT: 3,
        ErrorCode.E_NETWORK: 3,
        ErrorCode.E_RATE_LIMIT: 3,
        ErrorCode.E_PROVIDER_HTTP: 3,
        ErrorCode.E_PROVIDER_PARSE: 3,
        ErrorCode.E_CALENDAR: 2,
        ErrorCode.E_SESSION: 2,
        ErrorCode.E_ROLL: 2,
        ErrorCode.E_NODATA_DAILY: 4,
        ErrorCode.E_NODATA_INTRADAY: 0,  # Note: varies by mode
        ErrorCode.E_FORMAT: 2,
        ErrorCode.E_VALIDATION: 2,
        ErrorCode.E_SCHEMA: 2,
        ErrorCode.E_UNKNOWN: 3
    }
    
    for error_code, expected_exit in expected_exit_codes.items():
        error_info = ERROR_TAXONOMY[error_code]
        assert error_info.cli_exit_code == expected_exit


def test_retry_strategies():
    """Test retry strategy assignments"""
    no_retry_codes = [
        ErrorCode.E_CONFIG, ErrorCode.E_STUB_PATH, ErrorCode.E_CALENDAR,
        ErrorCode.E_SESSION, ErrorCode.E_ROLL, ErrorCode.E_NODATA_DAILY,
        ErrorCode.E_NODATA_INTRADAY, ErrorCode.E_FORMAT, ErrorCode.E_VALIDATION,
        ErrorCode.E_SCHEMA
    ]
    
    backoff_codes = [
        ErrorCode.E_TIMEOUT, ErrorCode.E_NETWORK, ErrorCode.E_RATE_LIMIT,
        ErrorCode.E_PROVIDER_HTTP, ErrorCode.E_PROVIDER_PARSE, ErrorCode.E_UNKNOWN
    ]
    
    auth_codes = [ErrorCode.E_AUTH]
    
    for code in no_retry_codes:
        assert ERROR_TAXONOMY[code].retry_strategy == RetryStrategy.NO
        assert not is_retryable(code)
    
    for code in backoff_codes:
        assert ERROR_TAXONOMY[code].retry_strategy == RetryStrategy.BACKOFF
        assert is_retryable(code)
    
    for code in auth_codes:
        assert ERROR_TAXONOMY[code].retry_strategy == RetryStrategy.AUTH
        assert should_refresh_auth(code)


def test_create_error_envelope():
    """Test error envelope creation"""
    envelope = create_error_envelope(
        code=ErrorCode.E_NODATA_INTRADAY,
        message="No intraday bars for 2025-08-20 rth",
        hint="Check session window or venue calendar",
        provider="schwab",
        provider_status=200,
        request_id="abc-123",
        telemetry={"symbol": "/NQ", "date": "2025-08-20"}
    )
    
    expected = {
        "error": {
            "code": "E-NODATA-INTRADAY",
            "message": "No intraday bars for 2025-08-20 rth",
            "hint": "Check session window or venue calendar",
            "retry": "no",
            "provenance": {
                "provider": "schwab",
                "provider_status": 200,
                "request_id": "abc-123"
            },
            "telemetry": {
                "symbol": "/NQ",
                "date": "2025-08-20"
            }
        }
    }
    
    assert envelope == expected


def test_create_telemetry_context():
    """Test telemetry context creation"""
    context = create_telemetry_context(
        symbol="/NQ",
        date="2025-08-22",
        session="rth",
        pivot_kind="classic",
        vwap_kind="session",
        request_id="req-123",
        provider_status=200,
        duration_ms=850,
        bars_expected=390,
        bars_received=390
    )
    
    expected_keys = {
        'symbol', 'date', 'session', 'pivot_kind', 'vwap_kind',
        'request_id', 'provider_status', 'duration_ms',
        'bars_expected', 'bars_received', 'timestamp'
    }
    
    assert set(context.keys()) == expected_keys
    assert context['symbol'] == "/NQ"
    assert context['date'] == "2025-08-22"
    assert context['session'] == "rth"
    assert context['bars_expected'] == 390
    assert context['bars_received'] == 390
    
    # Timestamp should be present and in ISO format
    assert 'timestamp' in context
    assert context['timestamp'].endswith('Z')


def test_create_telemetry_context_with_nulls():
    """Test telemetry context with None values"""
    context = create_telemetry_context(
        symbol="/NQ",
        date="2025-08-22",
        session=None,  # Should not be included
        bars_expected=None  # Should not be included
    )
    
    # Only non-None values should be included
    assert 'symbol' in context
    assert 'date' in context
    assert 'session' not in context
    assert 'bars_expected' not in context
    assert 'timestamp' in context  # Always included


def test_get_error_info():
    """Test getting error information"""
    info = get_error_info(ErrorCode.E_AUTH)
    assert info.code == ErrorCode.E_AUTH
    assert info.meaning == "Missing/expired/invalid auth"
    assert info.retry_strategy == RetryStrategy.AUTH
    assert info.cli_exit_code == 2


def test_error_envelope_json_serializable():
    """Test that error envelopes can be JSON serialized"""
    envelope = create_error_envelope(
        code=ErrorCode.E_NETWORK,
        message="Connection timeout",
        provider="schwab"
    )
    
    # Should not raise exception
    json_str = json.dumps(envelope)
    
    # Should be able to parse back
    parsed = json.loads(json_str)
    assert parsed["error"]["code"] == "E-NETWORK"
    assert parsed["error"]["message"] == "Connection timeout"
    assert parsed["error"]["retry"] == "backoff"


def test_minimal_error_envelope():
    """Test minimal error envelope creation"""
    envelope = create_error_envelope(
        code=ErrorCode.E_CONFIG,
        message="Missing API key"
    )
    
    expected = {
        "error": {
            "code": "E-CONFIG",
            "message": "Missing API key",
            "hint": None,
            "retry": "no",
            "provenance": {
                "provider": "schwab",
                "provider_status": None,
                "request_id": None
            }
        }
    }
    
    assert envelope == expected


if __name__ == "__main__":
    # Run basic tests
    test_error_code_enum()
    test_error_taxonomy_completeness()
    test_exit_codes()
    test_retry_strategies()
    test_create_error_envelope()
    test_create_telemetry_context()
    test_get_error_info()
    test_error_envelope_json_serializable()
    test_minimal_error_envelope()
    print("✅ All error taxonomy tests passed!")
