#!/usr/bin/env python3
"""
Demo script showing levels.v1 JSON schema format

This demonstrates the levels.v1 schema format that would be returned
by calc-levels when real historical API is implemented.
"""

import json
from datetime import date
from pathlib import Path
import sys

# Add app to path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

from app.schemas.levels_v1 import create_levels_v1_output, validate_levels_v1_schema


def demo_levels_v1_format():
    """Demonstrate the levels.v1 format with sample data"""
    
    print("🚀 levels.v1 JSON Schema Demo")
    print("=" * 50)
    
    # Sample data that would come from real Schwab API
    levels_data = {
        "R1": 23245.75,
        "S1": 23129.25,
        "VWAP": 23187.42,
        "pivot": 23187.50
    }
    
    quality_data = {
        "vwap_method": "intraday_true",
        "data_lag_ms": 850
    }
    
    provenance_data = {
        "provider": "schwab",
        "provider_request_id": "req-abc-123",
        "is_synthetic": False
    }
    
    # Simulate 390 intraday bars (6.5 hours * 60 minutes)
    mock_intraday_bars = [{"volume": 100} for _ in range(390)]
    
    # Create levels.v1 output
    output = create_levels_v1_output(
        symbol_raw="/NQ",
        symbol_resolved="NQU25", 
        target_date=date(2025, 8, 22),
        levels_data=levels_data,
        quality_data=quality_data,
        provenance_data=provenance_data,
        pivot_kind="classic",
        vwap_kind="session",
        session="rth",
        timezone="America/New_York",
        intraday_bars=mock_intraday_bars,
        roll_mode="calendar",
        interval="1min",
        precision=4
    )
    
    # Validate schema compliance
    try:
        validate_levels_v1_schema(output)
        print("✅ Schema validation: PASSED")
    except ValueError as e:
        print(f"❌ Schema validation: FAILED - {e}")
        return
    
    print("\n📋 Sample levels.v1 Output:")
    print("-" * 30)
    print(json.dumps(output, indent=2))
    
    print("\n🔍 Key Features:")
    print("- ✅ Full provenance tracking (data source, authenticity)")
    print("- ✅ Quality metrics (bar count, coverage percentage)")
    print("- ✅ Input parameters (symbol translation, timezone, precision)")
    print("- ✅ Schema validation (JSON Schema 2020-12 compliant)")
    print("- ✅ Machine-readable format with type safety")
    
    print(f"\n📊 Data Quality:")
    print(f"- VWAP Method: {output['quality']['vwap_method']}")
    print(f"- Bar Count: {output['quality']['intraday_bar_count']}")
    print(f"- Coverage: {output['quality']['coverage_pct']}%")
    print(f"- Data Lag: {output['quality']['data_lag_ms']}ms")
    
    print(f"\n🔒 Production Safety:")
    print(f"- Provider: {output['provenance']['provider']}")
    print(f"- Synthetic Data: {output['provenance']['is_synthetic']}")
    print(f"- Request ID: {output['provenance']['provider_request_id']}")
    print(f"- Session Window: {output['provenance']['session_window']}")
    
    print("\n🚀 Usage Example:")
    print("python ta_production.py calc-levels --symbol /NQ --date 2025-08-22 --format levels.v1")
    print("\n(Note: Currently blocked until real Schwab historical API is implemented)")


def demo_unavailable_vwap():
    """Demonstrate levels.v1 format when VWAP is unavailable"""
    
    print("\n" + "=" * 50)
    print("🚫 VWAP Unavailable Scenario Demo")
    print("=" * 50)
    
    levels_data = {
        "R1": 23245.75,
        "S1": 23129.25,
        "VWAP": None,  # Unavailable
        "pivot": 23187.50
    }
    
    quality_data = {
        "vwap_method": "unavailable",
        "data_lag_ms": None
    }
    
    provenance_data = {
        "provider": "schwab",
        "provider_request_id": "req-def-456",
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
    
    print("📋 levels.v1 with VWAP Unavailable:")
    print("-" * 40)
    print(json.dumps({
        "levels": output["levels"],
        "quality": output["quality"]
    }, indent=2))
    
    print("\n✅ Graceful degradation:")
    print("- R1/S1 calculated from OHLC data")
    print("- VWAP set to null (not synthetic)")
    print("- vwap_method explicitly marked as 'unavailable'")
    print("- Coverage accurately reflects 0% intraday data")


if __name__ == "__main__":
    demo_levels_v1_format()
    demo_unavailable_vwap()
