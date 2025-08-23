"""
Test the levels.v1 JSON schema implementation
"""

import json
import pytest
from datetime import date, datetime
from pathlib import Path
import sys
import os

# Add repository root and app to path for imports
repo_root = Path(__file__).parent.parent
app_dir = repo_root / "app"
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(app_dir))

from app.schemas.levels_v1 import (
    create_levels_v1_output, 
    validate_levels_v1_schema,
    get_schema_json
)


def test_create_levels_v1_output():
    """Test creating a valid levels.v1 output"""
    
    # Sample data
    levels_data = {
        "R1": 24158.0,
        "S1": 23861.0, 
        "VWAP": 24009.23,
        "pivot": 24009.23
    }
    
    quality_data = {
        "vwap_method": "intraday_true",
        "data_lag_ms": 800
    }
    
    provenance_data = {
        "provider": "schwab",
        "provider_request_id": "abc-123",
        "is_synthetic": False
    }
    
    # Create output
    output = create_levels_v1_output(
        symbol_raw="ES",
        symbol_resolved="ESU25", 
        target_date=date(2025, 8, 20),
        levels_data=levels_data,
        quality_data=quality_data,
        provenance_data=provenance_data,
        pivot_kind="classic",
        vwap_kind="session",
        session="rth",
        timezone="America/New_York",
        intraday_bars=[1] * 390,  # Mock 390 bars
        roll_mode="calendar",
        interval="1min"
    )
    
    # Verify structure
    assert output["version"] == "levels.v1"
    assert output["symbol"] == "ESU25"
    assert output["date"] == "2025-08-20"
    assert output["session"] == "rth"
    assert output["pivot_kind"] == "classic"
    assert output["vwap_kind"] == "session"
    
    # Verify levels
    assert output["levels"]["R1"] == 24158.0
    assert output["levels"]["S1"] == 23861.0
    assert output["levels"]["VWAP"] == 24009.23
    assert output["levels"]["pivot"] == 24009.23
    
    # Verify quality
    assert output["quality"]["vwap_method"] == "intraday_true"
    assert output["quality"]["intraday_bar_count"] == 390
    assert output["quality"]["bars_expected"] == 390
    assert output["quality"]["coverage_pct"] == 100.0
    assert output["quality"]["data_lag_ms"] == 800
    
    # Verify provenance
    assert output["provenance"]["provider"] == "schwab"
    assert output["provenance"]["provider_request_id"] == "abc-123"
    assert output["provenance"]["is_synthetic"] == False
    assert "2025-08-20 09:30–16:00 America/New_York" in output["provenance"]["session_window"]
    assert output["provenance"]["roll_mode"] == "calendar"
    
    # Verify input
    assert output["input"]["symbol_raw"] == "ES"
    assert output["input"]["tz"] == "America/New_York"
    assert output["input"]["roll"] == "calendar"
    assert output["input"]["interval"] == "1min"


def test_validate_levels_v1_schema_valid():
    """Test validation of a valid levels.v1 output"""
    
    valid_output = {
        "version": "levels.v1",
        "symbol": "ESU25",
        "date": "2025-08-20",
        "session": "rth",
        "pivot_kind": "classic",
        "vwap_kind": "session",
        "input": {
            "symbol_raw": "ES",
            "tz": "America/New_York",
            "anchor": None,
            "adjust": None,
            "roll": "calendar",
            "interval": "1min",
            "precision": None
        },
        "levels": {
            "R1": 24158.0,
            "S1": 23861.0,
            "VWAP": 24009.23,
            "pivot": 24009.23
        },
        "quality": {
            "vwap_method": "intraday_true",
            "intraday_bar_count": 390,
            "bars_expected": 390,
            "coverage_pct": 100.0,
            "data_lag_ms": 800
        },
        "provenance": {
            "provider": "schwab",
            "provider_request_id": "abc-123",
            "is_synthetic": False,
            "session_window": "2025-08-20 09:30–16:00 America/New_York",
            "roll_mode": "calendar"
        }
    }
    
    # Should not raise any exception
    assert validate_levels_v1_schema(valid_output) == True


def test_validate_levels_v1_schema_invalid_version():
    """Test validation fails with invalid version"""
    
    invalid_output = {
        "version": "levels.v2",  # Wrong version
        "symbol": "ESU25",
        "date": "2025-08-20",
        "session": "rth",
        "pivot_kind": "classic",
        "levels": {"R1": 1, "S1": 2, "VWAP": 3},
        "quality": {"vwap_method": "intraday_true", "intraday_bar_count": 390, "coverage_pct": 100.0},
        "provenance": {"provider": "schwab", "is_synthetic": False, "session_window": "2025-08-20 09:30–16:00 America/New_York"},
        "input": {"symbol_raw": "ES", "tz": "America/New_York"}
    }
    
    with pytest.raises(ValueError, match="Invalid version"):
        validate_levels_v1_schema(invalid_output)


def test_validate_levels_v1_schema_missing_required():
    """Test validation fails with missing required fields"""
    
    incomplete_output = {
        "version": "levels.v1",
        "symbol": "ESU25",
        # Missing required fields
    }
    
    with pytest.raises(ValueError, match="Missing required field"):
        validate_levels_v1_schema(incomplete_output)


def test_get_schema_json():
    """Test getting the JSON schema definition"""
    
    schema = get_schema_json()
    
    # Verify it's a proper JSON schema
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["title"] == "levels.v1"
    assert schema["type"] == "object"
    
    # Verify required fields
    required_fields = schema["required"]
    expected_required = ["version", "symbol", "date", "session", "pivot_kind", 
                        "levels", "quality", "provenance", "input"]
    
    for field in expected_required:
        assert field in required_fields
    
    # Verify properties structure
    properties = schema["properties"]
    assert "version" in properties
    assert properties["version"]["const"] == "levels.v1"
    
    assert "levels" in properties
    levels_props = properties["levels"]["properties"]
    assert "R1" in levels_props
    assert "S1" in levels_props
    assert "VWAP" in levels_props


def test_levels_v1_with_null_vwap():
    """Test levels.v1 output when VWAP is unavailable"""
    
    levels_data = {
        "R1": 24158.0,
        "S1": 23861.0, 
        "VWAP": None,  # Unavailable
        "pivot": 24009.23
    }
    
    quality_data = {
        "vwap_method": "unavailable",
        "data_lag_ms": None
    }
    
    provenance_data = {
        "provider": "schwab",
        "provider_request_id": "def-456", 
        "is_synthetic": False
    }
    
    output = create_levels_v1_output(
        symbol_raw="/NQ",
        symbol_resolved="NQU25",
        target_date=date(2025, 8, 22),
        levels_data=levels_data,
        quality_data=quality_data,
        provenance_data=provenance_data,
        intraday_bars=[]  # No bars available
    )
    
    # Verify VWAP handling
    assert output["levels"]["VWAP"] is None
    assert output["quality"]["vwap_method"] == "unavailable"
    assert output["quality"]["intraday_bar_count"] == 0
    assert output["quality"]["coverage_pct"] == 0.0
    
    # Should still validate
    assert validate_levels_v1_schema(output) == True


if __name__ == "__main__":
    # Run basic tests
    test_create_levels_v1_output()
    test_validate_levels_v1_schema_valid()
    test_get_schema_json()
    test_levels_v1_with_null_vwap()
    print("✅ All levels.v1 schema tests passed!")
