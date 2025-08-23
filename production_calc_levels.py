#!/usr/bin/env python3
"""
Production-Safe Calc Levels Command

Implements no-fallback, provenance-tracked calc-levels with hard failure on stub paths.
Supports levels.v1 JSON schema for comprehensive machine-readable output.
"""

import asyncio
import json
import sys
from datetime import datetime, date as date_type
from pathlib import Path

# Add the app directory to Python path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))


async def production_calc_levels(symbol: str, date: str, format: str = "ai-block"):
    """Calculate R1, S1, VWAP using production-safe real data with no fallbacks"""
    
    # Import modules first
    from app.config import Config
    from app.auth import AuthManager
    from app.production_provider import ProductionDataProvider
    from app.guardrails import require, create_provenance_data, emit_provenance
    from app.schemas.levels_v1 import create_levels_v1_output, validate_levels_v1_schema
    from app.utils.futures import translate_root_to_front_month
    from app.errors import (
        ErrorCode, fail_with_error, fail_format_error, create_telemetry_context
    )
    
    # Initialize variables to avoid unbound warnings
    target_date = None
    ohlc_data = None
    intraday_bars = []
    vwap_val = None
    vwap_method = "unavailable"
    data_lag_ms = None
    H = L = C = 0.0
    provenance = {}
    
    try:
        print(f"[DEBUG] production_calc_levels: symbol={symbol}, date={date}, format={format}")
        
        # Parse date
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            fail_format_error(f"Invalid date format: {date}. Use YYYY-MM-DD")
        
        # Initialize configuration and provider
        config = Config()
        auth_manager = AuthManager(config)
        provider = ProductionDataProvider(config, auth_manager)
        
        # Resolve symbol for output
        resolved_symbol = translate_root_to_front_month(symbol).upper()
        
        # Pre-flight check
        print("[DEBUG] Running pre-flight checks...")
        preflight_result = await provider.preflight_check()
        print(f"[DEBUG] Pre-flight result: {preflight_result}")
        
        # Get previous trading session OHLC for pivot calculations
        print(f"[DEBUG] Fetching daily OHLC for {symbol}")
        
        # This will fail until real historical API is implemented
        try:
            if target_date:  # Type guard
                ohlc_data = await provider.get_daily_ohlc(symbol, target_date)
                require(ohlc_data is not None, "E-NODATA-DAILY", f"No daily OHLC for {symbol} on {target_date}")
                
                # Extract OHLC values
                if ohlc_data:  # Type guard
                    H = ohlc_data.high
                    L = ohlc_data.low
                    C = ohlc_data.close
            
        except SystemExit as e:
            if "E-NODATA-DAILY" in str(e) or "E-STUB-PATH" in str(e):
                # This is expected until real historical API is implemented
                print(f"[DEBUG] {e}")
                print("[DEBUG] Historical API not yet implemented - this is expected")
                print("[DEBUG] In production, this would require real Schwab historical API")
                raise  # Re-raise to fail the command
            else:
                raise
        
        # Get intraday bars for true VWAP calculation
        print(f"[DEBUG] Fetching intraday bars for {symbol}")
        try:
            if target_date:  # Type guard
                start_time = datetime.now()
                intraday_bars = await provider.get_intraday_bars(symbol, target_date)
                end_time = datetime.now()
                data_lag_ms = int((end_time - start_time).total_seconds() * 1000)
                
                # Calculate true VWAP from intraday bars
                vwap_val = provider.calculate_true_vwap(intraday_bars)
                vwap_method = "intraday_true" if vwap_val is not None else "unavailable"
            
        except SystemExit as e:
            if "E-NODATA-INTRADAY" in str(e) or "E-STUB-PATH" in str(e):
                print(f"[DEBUG] {e}")
                print("[DEBUG] Intraday API not yet implemented")
                vwap_val = None
                vwap_method = "unavailable"
            else:
                raise
        
        # Calculate pivot levels (classic pivot points)
        pivot = (H + L + C) / 3.0
        r1 = 2 * pivot - L
        s1 = 2 * pivot - H
        
        # Prepare data structures
        levels_data = {
            "R1": r1,
            "S1": s1,
            "VWAP": vwap_val,
            "pivot": pivot
        }
        
        quality_data = {
            "vwap_method": vwap_method,
            "data_lag_ms": data_lag_ms
        }
        
        # Create provenance data
        if target_date:  # Type guard
            session_info = provider.create_session_info(target_date)
            provenance = create_provenance_data(
                provider="schwab",
                is_synthetic=False,
                vwap_method=vwap_method,
                provider_request_id=provider.request_id,
                source_session=session_info
            )
        else:
            fail_format_error("Failed to parse target date")
        
        # Output in requested format with mandatory provenance
        if format.lower() == "ai-block":
            print("[AI_DATA_BLOCK_START]")
            print(f"R1: {r1:.4f}")
            print(f"S1: {s1:.4f}")
            print(f"VWAP: {vwap_val:.4f if vwap_val is not None else 'N/A'}")
            print("[AI_DATA_BLOCK_END]")
            
            # Emit provenance to STDERR for AI-block format
            emit_provenance("ai-block", **provenance)
            
        elif format.lower() == "json":
            output = {
                "symbol": symbol,
                "date": date,
                "levels": levels_data,
                "provenance": provenance
            }
            print(json.dumps(output, indent=2, default=str))
            
        elif format.lower() == "levels.v1" or format.lower() == "levels-v1":
            # Generate levels.v1 compliant output
            if target_date:  # Type guard
                output = create_levels_v1_output(
                    symbol_raw=symbol,
                    symbol_resolved=resolved_symbol,
                    target_date=target_date,
                    levels_data=levels_data,
                    quality_data=quality_data,
                    provenance_data=provenance,
                    pivot_kind="classic",
                    vwap_kind="session",
                    session="rth",
                    timezone="America/New_York",
                    intraday_bars=intraday_bars,
                    roll_mode="calendar",
                    interval="1min"
                )
                
                # Validate schema compliance
                validate_levels_v1_schema(output)
                
                print(json.dumps(output, indent=2, default=str))
            
        elif format.lower() == "csv":
            print("symbol,date,R1,S1,VWAP,pivot,data_source,is_synthetic,vwap_method")
            vwap_str = f"{vwap_val:.4f}" if vwap_val is not None else "N/A"
            print(f"{symbol},{date},{r1:.4f},{s1:.4f},{vwap_str},{pivot:.4f},"
                  f"{provenance['data_source']},{provenance['is_synthetic']},{provenance['vwap_method']}")
        else:
            fail_format_error(f"Unknown format: {format}. Use: ai-block, json, levels.v1, csv")
        
        # Exit with non-zero code if VWAP is not available (single-date mode)
        if vwap_val is None:
            print(f"E-VWAP-UNAVAILABLE: VWAP data not available for {symbol} on {date}", file=sys.stderr)
            sys.exit(1)
            
    except SystemExit:
        raise
    except Exception as e:
        print(f"[ERROR] Calculation failed: {e}")
        # Use structured error handling
        fail_with_error(
            ErrorCode.E_UNKNOWN,
            f"Calculation failed: {e}",
            telemetry=create_telemetry_context(symbol=symbol, date=date)
        )


def main():
    """Main function for testing"""
    if len(sys.argv) < 3:
        print("Usage: python production_calc_levels.py SYMBOL DATE [FORMAT]")
        print("Example: python production_calc_levels.py /NQ 2025-08-21 ai-block")
        sys.exit(1)
    
    symbol = sys.argv[1]
    date = sys.argv[2]
    format_type = sys.argv[3] if len(sys.argv) > 3 else "ai-block"
    
    asyncio.run(production_calc_levels(symbol, date, format_type))


if __name__ == "__main__":
    main()
