"""
Error Taxonomy and Handling System

Implements structured error codes (E-* taxonomy) with proper retry strategies,
exit codes, and telemetry for the Trade Analyst system.
"""

import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional, Literal
from enum import Enum


class ErrorCode(Enum):
    """Standard error codes for the Trade Analyst system"""
    
    # Authentication and Configuration
    E_AUTH = "E-AUTH"
    E_CONFIG = "E-CONFIG"
    E_STUB_PATH = "E-STUB-PATH"
    
    # Network and Provider Issues
    E_TIMEOUT = "E-TIMEOUT"
    E_NETWORK = "E-NETWORK"
    E_RATE_LIMIT = "E-RATE-LIMIT"
    E_PROVIDER_HTTP = "E-PROVIDER-HTTP"
    E_PROVIDER_PARSE = "E-PROVIDER-PARSE"
    
    # Market Data and Calendar Issues
    E_CALENDAR = "E-CALENDAR"
    E_SESSION = "E-SESSION"
    E_ROLL = "E-ROLL"
    E_NODATA_DAILY = "E-NODATA-DAILY"
    E_NODATA_INTRADAY = "E-NODATA-INTRADAY"
    
    # Validation and Schema Issues
    E_FORMAT = "E-FORMAT"
    E_VALIDATION = "E-VALIDATION"
    E_SCHEMA = "E-SCHEMA"
    
    # Catch-all
    E_UNKNOWN = "E-UNKNOWN"


class RetryStrategy(Enum):
    """Retry strategies for different error types"""
    NO = "no"
    BACKOFF = "backoff"
    AUTH = "auth"


class ErrorInfo:
    """Error code metadata and handling information"""
    
    def __init__(
        self,
        code: ErrorCode,
        meaning: str,
        when_to_use: str,
        retry_strategy: RetryStrategy,
        cli_exit_code: int
    ):
        self.code = code
        self.meaning = meaning
        self.when_to_use = when_to_use
        self.retry_strategy = retry_strategy
        self.cli_exit_code = cli_exit_code


# Error taxonomy mapping
ERROR_TAXONOMY = {
    ErrorCode.E_AUTH: ErrorInfo(
        ErrorCode.E_AUTH,
        "Missing/expired/invalid auth",
        "Token not present/refresh failed",
        RetryStrategy.AUTH,
        2
    ),
    ErrorCode.E_CONFIG: ErrorInfo(
        ErrorCode.E_CONFIG,
        "Bad/missing config",
        "Required env/keys not set",
        RetryStrategy.NO,
        2
    ),
    ErrorCode.E_STUB_PATH: ErrorInfo(
        ErrorCode.E_STUB_PATH,
        "Stub invoked in prod",
        "Any synthetic path reached",
        RetryStrategy.NO,
        2
    ),
    ErrorCode.E_TIMEOUT: ErrorInfo(
        ErrorCode.E_TIMEOUT,
        "Upstream timeout",
        "Provider didn't respond in time",
        RetryStrategy.BACKOFF,
        3
    ),
    ErrorCode.E_NETWORK: ErrorInfo(
        ErrorCode.E_NETWORK,
        "DNS/TLS/connect errors",
        "Transport layer failures",
        RetryStrategy.BACKOFF,
        3
    ),
    ErrorCode.E_RATE_LIMIT: ErrorInfo(
        ErrorCode.E_RATE_LIMIT,
        "Provider 429/quotas",
        "Hit rate or burst limits",
        RetryStrategy.BACKOFF,
        3
    ),
    ErrorCode.E_PROVIDER_HTTP: ErrorInfo(
        ErrorCode.E_PROVIDER_HTTP,
        "Provider non-2xx",
        "4xx/5xx not mapped elsewhere",
        RetryStrategy.BACKOFF,  # Note: 5xx backoff, 4xx no
        3
    ),
    ErrorCode.E_PROVIDER_PARSE: ErrorInfo(
        ErrorCode.E_PROVIDER_PARSE,
        "Response shape invalid",
        "JSON/XML can't be parsed",
        RetryStrategy.BACKOFF,  # Note: rare, then no
        3
    ),
    ErrorCode.E_CALENDAR: ErrorInfo(
        ErrorCode.E_CALENDAR,
        "Calendar resolution failed",
        "Holiday/early close lookup fail",
        RetryStrategy.NO,
        2
    ),
    ErrorCode.E_SESSION: ErrorInfo(
        ErrorCode.E_SESSION,
        "Session window invalid",
        "RTH/ETH bounds inconsistent",
        RetryStrategy.NO,
        2
    ),
    ErrorCode.E_ROLL: ErrorInfo(
        ErrorCode.E_ROLL,
        "Futures roll resolution failed",
        "Couldn't map root→contract",
        RetryStrategy.NO,
        2
    ),
    ErrorCode.E_NODATA_DAILY: ErrorInfo(
        ErrorCode.E_NODATA_DAILY,
        "No prior daily OHLC",
        "Pivots impossible",
        RetryStrategy.NO,
        4
    ),
    ErrorCode.E_NODATA_INTRADAY: ErrorInfo(
        ErrorCode.E_NODATA_INTRADAY,
        "No intraday bars",
        "VWAP unavailable",
        RetryStrategy.NO,
        0  # Note: 0 in batch mode, 4 in single-date mode
    ),
    ErrorCode.E_FORMAT: ErrorInfo(
        ErrorCode.E_FORMAT,
        "Bad request from caller",
        "Input validation failed",
        RetryStrategy.NO,
        2
    ),
    ErrorCode.E_VALIDATION: ErrorInfo(
        ErrorCode.E_VALIDATION,
        "Output failed schema",
        "Internal contract violation",
        RetryStrategy.NO,
        2
    ),
    ErrorCode.E_SCHEMA: ErrorInfo(
        ErrorCode.E_SCHEMA,
        "Schema version unsupported",
        "Consumer asked wrong version",
        RetryStrategy.NO,
        2
    ),
    ErrorCode.E_UNKNOWN: ErrorInfo(
        ErrorCode.E_UNKNOWN,
        "Unclassified failure",
        "Final catch-all",
        RetryStrategy.BACKOFF,
        3
    )
}


def create_error_envelope(
    code: ErrorCode,
    message: str,
    hint: Optional[str] = None,
    provider: str = "schwab",
    provider_status: Optional[int] = None,
    request_id: Optional[str] = None,
    telemetry: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a structured error envelope for service responses.
    
    Args:
        code: Error code from ErrorCode enum
        message: Human-readable error message
        hint: Optional hint for resolution
        provider: Data provider name
        provider_status: HTTP status from provider
        request_id: Request ID for tracing
        telemetry: Additional telemetry fields
        
    Returns:
        Structured error envelope dictionary
    """
    error_info = ERROR_TAXONOMY[code]
    
    envelope = {
        "error": {
            "code": code.value,
            "message": message,
            "hint": hint,
            "retry": error_info.retry_strategy.value,
            "provenance": {
                "provider": provider,
                "provider_status": provider_status,
                "request_id": request_id
            }
        }
    }
    
    # Add telemetry fields if provided
    if telemetry:
        envelope["error"]["telemetry"] = telemetry
    
    return envelope


def fail_with_error(
    code: ErrorCode,
    message: str,
    hint: Optional[str] = None,
    provider: str = "schwab",
    provider_status: Optional[int] = None,
    request_id: Optional[str] = None,
    telemetry: Optional[Dict[str, Any]] = None,
    single_date_mode: bool = True
) -> None:
    """
    Fail with structured error handling for CLI mode.
    
    Args:
        code: Error code from ErrorCode enum
        message: Human-readable error message
        hint: Optional hint for resolution
        provider: Data provider name
        provider_status: HTTP status from provider
        request_id: Request ID for tracing
        telemetry: Additional telemetry fields
        single_date_mode: Whether in single-date mode (affects exit codes)
    """
    error_info = ERROR_TAXONOMY[code]
    
    # Special handling for E-NODATA-INTRADAY
    if code == ErrorCode.E_NODATA_INTRADAY and not single_date_mode:
        # In batch mode, this should be handled gracefully with VWAP=null
        exit_code = 0
    else:
        exit_code = error_info.cli_exit_code
    
    # Create error envelope for structured logging
    envelope = create_error_envelope(
        code, message, hint, provider, provider_status, request_id, telemetry
    )
    
    # Output error message to STDERR
    print(f"{code.value}: {message}", file=sys.stderr)
    
    if hint:
        print(f"Hint: {hint}", file=sys.stderr)
    
    # Output structured error for logging/monitoring (optional JSON to STDERR)
    print(f"ERROR_ENVELOPE: {json.dumps(envelope, default=str)}", file=sys.stderr)
    
    # Exit with appropriate code
    sys.exit(exit_code)


def create_telemetry_context(
    symbol: Optional[str] = None,
    date: Optional[str] = None,
    session: Optional[str] = None,
    pivot_kind: Optional[str] = None,
    vwap_kind: Optional[str] = None,
    request_id: Optional[str] = None,
    provider_status: Optional[int] = None,
    duration_ms: Optional[int] = None,
    bars_expected: Optional[int] = None,
    bars_received: Optional[int] = None
) -> Dict[str, Any]:
    """
    Create telemetry context for error reporting.
    
    Args:
        symbol: Trading symbol
        date: Trading date
        session: Session type (rth/eth)
        pivot_kind: Pivot calculation method
        vwap_kind: VWAP calculation method
        request_id: Request ID for tracing
        provider_status: Provider HTTP status
        duration_ms: Request duration
        bars_expected: Expected number of bars
        bars_received: Actual number of bars received
        
    Returns:
        Telemetry context dictionary
    """
    context = {}
    
    # Add non-None values to context
    fields = {
        'symbol': symbol,
        'date': date,
        'session': session,
        'pivot_kind': pivot_kind,
        'vwap_kind': vwap_kind,
        'request_id': request_id,
        'provider_status': provider_status,
        'duration_ms': duration_ms,
        'bars_expected': bars_expected,
        'bars_received': bars_received,
        'timestamp': datetime.utcnow().isoformat() + "Z"
    }
    
    for key, value in fields.items():
        if value is not None:
            context[key] = value
    
    return context


def get_error_info(code: ErrorCode) -> ErrorInfo:
    """Get error information for a specific code"""
    return ERROR_TAXONOMY[code]


def is_retryable(code: ErrorCode) -> bool:
    """Check if an error code indicates a retryable condition"""
    error_info = ERROR_TAXONOMY[code]
    return error_info.retry_strategy != RetryStrategy.NO


def should_refresh_auth(code: ErrorCode) -> bool:
    """Check if an error code indicates auth refresh is needed"""
    error_info = ERROR_TAXONOMY[code]
    return error_info.retry_strategy == RetryStrategy.AUTH


# Convenience functions for common error scenarios
def fail_auth_error(message: str, request_id: Optional[str] = None) -> None:
    """Fail with authentication error"""
    fail_with_error(
        ErrorCode.E_AUTH,
        message,
        hint="Check token validity and refresh credentials",
        request_id=request_id
    )


def fail_config_error(message: str) -> None:
    """Fail with configuration error"""
    fail_with_error(
        ErrorCode.E_CONFIG,
        message,
        hint="Check environment variables and configuration files"
    )


def fail_stub_path_error(message: str) -> None:
    """Fail with stub path error (production safety)"""
    fail_with_error(
        ErrorCode.E_STUB_PATH,
        message,
        hint="Set FAIL_ON_STUB=0 for development or implement real provider"
    )


def fail_no_daily_data(symbol: str, date: str, request_id: Optional[str] = None) -> None:
    """Fail with no daily OHLC data error"""
    fail_with_error(
        ErrorCode.E_NODATA_DAILY,
        f"No daily OHLC data available for {symbol} on {date}",
        hint="Check symbol validity and market calendar",
        request_id=request_id,
        telemetry=create_telemetry_context(symbol=symbol, date=date)
    )


def fail_no_intraday_data(
    symbol: str, 
    date: str, 
    session: str = "rth",
    single_date_mode: bool = True,
    request_id: Optional[str] = None
) -> None:
    """Fail with no intraday data error"""
    fail_with_error(
        ErrorCode.E_NODATA_INTRADAY,
        f"No intraday bars for {symbol} on {date} {session}",
        hint="Check session window or venue calendar",
        request_id=request_id,
        telemetry=create_telemetry_context(symbol=symbol, date=date, session=session),
        single_date_mode=single_date_mode
    )


def fail_format_error(message: str) -> None:
    """Fail with format validation error"""
    fail_with_error(
        ErrorCode.E_FORMAT,
        message,
        hint="Check input format and parameter values"
    )


def fail_network_error(message: str, request_id: Optional[str] = None) -> None:
    """Fail with network error"""
    fail_with_error(
        ErrorCode.E_NETWORK,
        message,
        hint="Check network connectivity and try again",
        request_id=request_id
    )


def fail_provider_error(
    status_code: int,
    message: str,
    request_id: Optional[str] = None
) -> None:
    """Fail with provider HTTP error"""
    fail_with_error(
        ErrorCode.E_PROVIDER_HTTP,
        f"Provider error {status_code}: {message}",
        hint="Provider may be experiencing issues, try again later",
        provider_status=status_code,
        request_id=request_id
    )
