"""
Levels.v1 JSON Schema Implementation

Implements the comprehensive levels.v1 schema for machine-readable output
from the calc-levels command with full provenance and quality metrics.
"""

from datetime import datetime, date as date_type
from typing import Dict, Any, Optional, List
import pytz


def translate_root_to_front_month(symbol: str) -> str:
    """
    Simple futures translation function.
    In production, this would import from utils.futures
    """
    if symbol.upper() in ["/NQ", "NQ"]:
        return "NQU25"  # September 2025 contract
    elif symbol.upper() in ["/ES", "ES"]:
        return "ESU25"  # September 2025 contract
    else:
        return symbol.upper()


def create_levels_v1_output(
    symbol_raw: str,
    symbol_resolved: str,
    target_date: date_type,
    levels_data: Dict[str, Any],
    quality_data: Dict[str, Any],
    provenance_data: Dict[str, Any],
    pivot_kind: str = "classic",
    vwap_kind: str = "session",
    session: str = "rth",
    timezone: str = "America/New_York",
    intraday_bars: Optional[List] = None,
    roll_mode: Optional[str] = "calendar",
    interval: str = "1min",
    precision: Optional[int] = None
) -> Dict[str, Any]:
    """
    Create a levels.v1 compliant output object.
    
    Args:
        symbol_raw: Original input symbol (e.g., "/NQ", "ES")
        symbol_resolved: Resolved trading symbol (e.g., "NQU25", "ESU25")
        target_date: Trading session date
        levels_data: Dictionary with R1, S1, VWAP, pivot values
        quality_data: Quality metrics (vwap_method, bar_count, coverage, etc.)
        provenance_data: Data source provenance information
        pivot_kind: Type of pivot calculation ("classic", "fib", "camarilla")
        vwap_kind: VWAP calculation type ("session", "anchored")
        session: Trading session ("rth", "eth")
        timezone: IANA timezone string
        intraday_bars: List of intraday bars for quality metrics
        roll_mode: Futures contract roll mode
        interval: Data interval for intraday bars
        precision: Price precision (decimal places)
    
    Returns:
        Dictionary conforming to levels.v1 schema
    """
    
    # Calculate quality metrics
    bar_count = len(intraday_bars) if intraday_bars else 0
    
    # Expected bars calculation (rough estimate for RTH session)
    bars_expected = None
    coverage_pct = 0.0
    
    if session == "rth" and interval == "1min":
        # RTH is 6.5 hours = 390 minutes
        bars_expected = 390
        coverage_pct = (bar_count / bars_expected * 100.0) if bars_expected > 0 else 0.0
    elif session == "rth" and interval == "5min":
        bars_expected = 78  # 390 / 5
        coverage_pct = (bar_count / bars_expected * 100.0) if bars_expected > 0 else 0.0
    else:
        # For other sessions/intervals, use actual count as 100% if available
        coverage_pct = 100.0 if bar_count > 0 else 0.0
    
    # Ensure coverage doesn't exceed 100%
    coverage_pct = min(coverage_pct, 100.0)
    
    # Create session window string
    if session == "rth":
        session_window = f"{target_date.strftime('%Y-%m-%d')} 09:30–16:00 {timezone}"
    else:
        session_window = f"{target_date.strftime('%Y-%m-%d')} ETH {timezone}"
    
    # Determine adjustment type for futures
    adjust_type = None if "/" in symbol_raw or symbol_raw.upper() in ["ES", "NQ", "YM", "RTY"] else "none"
    
    return {
        "version": "levels.v1",
        "symbol": symbol_resolved,
        "date": target_date.strftime("%Y-%m-%d"),
        "session": session,
        "pivot_kind": pivot_kind,
        "vwap_kind": vwap_kind,
        
        "input": {
            "symbol_raw": symbol_raw,
            "tz": timezone,
            "anchor": None,  # Only used for anchored VWAP
            "adjust": adjust_type,
            "roll": roll_mode,
            "interval": interval,
            "precision": precision
        },
        
        "levels": {
            "R1": levels_data.get("R1"),
            "S1": levels_data.get("S1"),
            "VWAP": levels_data.get("VWAP"),
            "pivot": levels_data.get("pivot")
        },
        
        "quality": {
            "vwap_method": quality_data.get("vwap_method", "unavailable"),
            "intraday_bar_count": bar_count,
            "bars_expected": bars_expected,
            "coverage_pct": round(coverage_pct, 1),
            "data_lag_ms": quality_data.get("data_lag_ms")
        },
        
        "provenance": {
            "provider": provenance_data.get("provider", "schwab"),
            "provider_request_id": provenance_data.get("provider_request_id"),
            "is_synthetic": provenance_data.get("is_synthetic", False),
            "session_window": session_window,
            "roll_mode": roll_mode
        }
    }


def validate_levels_v1_schema(data: Dict[str, Any]) -> bool:
    """
    Basic validation of levels.v1 schema compliance.
    
    Args:
        data: Dictionary to validate
        
    Returns:
        True if valid, raises ValueError if invalid
    """
    required_fields = ["version", "symbol", "date", "session", "pivot_kind", 
                      "levels", "quality", "provenance", "input"]
    
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")
    
    # Check version
    if data["version"] != "levels.v1":
        raise ValueError(f"Invalid version: {data['version']}")
    
    # Validate session
    if data["session"] not in ["rth", "eth"]:
        raise ValueError(f"Invalid session: {data['session']}")
    
    # Validate pivot_kind
    if data["pivot_kind"] not in ["classic", "fib", "camarilla"]:
        raise ValueError(f"Invalid pivot_kind: {data['pivot_kind']}")
    
    # Validate levels structure
    levels = data["levels"]
    required_levels = ["R1", "S1", "VWAP"]
    for level in required_levels:
        if level not in levels:
            raise ValueError(f"Missing required level: {level}")
    
    # Validate quality structure
    quality = data["quality"]
    required_quality = ["vwap_method", "intraday_bar_count", "coverage_pct"]
    for field in required_quality:
        if field not in quality:
            raise ValueError(f"Missing required quality field: {field}")
    
    # Validate provenance structure  
    provenance = data["provenance"]
    required_provenance = ["provider", "is_synthetic", "session_window"]
    for field in required_provenance:
        if field not in provenance:
            raise ValueError(f"Missing required provenance field: {field}")
    
    return True


def get_schema_json() -> Dict[str, Any]:
    """Return the JSON Schema definition for levels.v1"""
    return {
        "$id": "https://trade-analyst/specs/levels.v1.schema.json",
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "levels.v1",
        "type": "object",
        "additionalProperties": False,
        "required": ["version", "symbol", "date", "session", "pivot_kind", 
                    "levels", "quality", "provenance", "input"],
        "properties": {
            "version": {"const": "levels.v1"},
            "symbol": {
                "type": "string",
                "minLength": 1,
                "description": "Resolved trading symbol for this date (e.g., ESU25, AAPL)"
            },
            "date": {
                "type": "string",
                "format": "date",
                "description": "Trading session date (YYYY-MM-DD)"
            },
            "session": {
                "type": "string",
                "enum": ["rth", "eth"],
                "description": "Session used for VWAP"
            },
            "pivot_kind": {
                "type": "string",
                "enum": ["classic", "fib", "camarilla"]
            },
            "vwap_kind": {
                "type": "string",
                "enum": ["session", "anchored"],
                "default": "session"
            },
            "input": {
                "type": "object",
                "additionalProperties": False,
                "required": ["symbol_raw", "tz"],
                "properties": {
                    "symbol_raw": {"type": "string"},
                    "tz": {
                        "type": "string",
                        "description": "IANA timezone (e.g., America/New_York)"
                    },
                    "anchor": {
                        "type": ["string", "null"],
                        "description": "HH:MM if vwap_kind=anchored"
                    },
                    "adjust": {
                        "type": ["string", "null"],
                        "enum": ["none", "split", "split+div", None]
                    },
                    "roll": {
                        "type": ["string", "null"],
                        "enum": ["calendar", "volume", "open_interest", None]
                    },
                    "interval": {
                        "type": ["string", "null"],
                        "enum": ["1min", "5min", "15min", "1h", "1d", None]
                    },
                    "precision": {
                        "type": ["integer", "null"],
                        "minimum": 0
                    }
                }
            },
            "levels": {
                "type": "object",
                "additionalProperties": False,
                "required": ["R1", "S1", "VWAP"],
                "properties": {
                    "R1": {"type": "number"},
                    "S1": {"type": "number"},
                    "VWAP": {
                        "type": ["number", "null"],
                        "description": "null when intraday bars unavailable"
                    },
                    "pivot": {
                        "type": ["number", "null"],
                        "description": "Included when useful for debugging"
                    }
                }
            },
            "quality": {
                "type": "object",
                "additionalProperties": False,
                "required": ["vwap_method", "intraday_bar_count", "coverage_pct"],
                "properties": {
                    "vwap_method": {
                        "type": "string",
                        "enum": ["intraday_true", "unavailable"]
                    },
                    "intraday_bar_count": {
                        "type": "integer",
                        "minimum": 0
                    },
                    "bars_expected": {
                        "type": ["integer", "null"],
                        "minimum": 0
                    },
                    "coverage_pct": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 100
                    },
                    "data_lag_ms": {
                        "type": ["integer", "null"],
                        "minimum": 0
                    }
                }
            },
            "provenance": {
                "type": "object",
                "additionalProperties": False,
                "required": ["provider", "is_synthetic", "session_window"],
                "properties": {
                    "provider": {
                        "type": "string",
                        "description": "e.g., schwab"
                    },
                    "provider_request_id": {
                        "type": ["string", "null"]
                    },
                    "is_synthetic": {
                        "type": "boolean"
                    },
                    "session_window": {
                        "type": "string",
                        "description": "e.g., 2025-08-20 09:30–16:00 America/New_York"
                    },
                    "roll_mode": {
                        "type": ["string", "null"],
                        "enum": ["calendar", "volume", "open_interest", None]
                    }
                }
            }
        }
    }
