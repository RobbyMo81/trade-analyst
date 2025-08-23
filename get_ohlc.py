#!/usr/bin/env python3
"""
Simple script to retrieve and display daily OHLC data.
"""

import asyncio
import sys
from datetime import date, datetime, timedelta
from typing import Optional
from app.config import Config
from app.auth import AuthManager
from app.production_provider import ProductionDataProvider

async def get_daily_ohlc(symbol: str, target_date: Optional[str] = None):
    """Get daily OHLC data for a symbol."""
    try:
        # Parse date or use most recent trading day
        if target_date:
            trade_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        else:
            # Use yesterday (likely last trading day)
            trade_date = date.today() - timedelta(days=1)
        
        # Initialize provider
        config = Config()
        auth_manager = AuthManager(config)
        provider = ProductionDataProvider(config, auth_manager)
        
        # Run preflight check
        preflight = await provider.preflight_check()
        print(f"Preflight: {preflight['auth']}, Provider: {preflight['provider']}")
        
        # Get daily OHLC
        print(f"\nRetrieving daily OHLC for {symbol} on {trade_date}...")
        ohlc_data = await provider.get_daily_ohlc(symbol, trade_date)
        
        if ohlc_data:
            print(f"\n=== Daily OHLC Data for {symbol} ===")
            print(f"Date: {trade_date}")
            print(f"Open:   ${ohlc_data.open:.4f}")
            print(f"High:   ${ohlc_data.high:.4f}")
            print(f"Low:    ${ohlc_data.low:.4f}")
            print(f"Close:  ${ohlc_data.close:.4f}")
            print(f"Volume: {ohlc_data.volume:,}")
            print(f"Timestamp: {ohlc_data.timestamp}")
        else:
            print(f"No OHLC data found for {symbol} on {trade_date}")
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python get_ohlc.py <SYMBOL> [YYYY-MM-DD]")
        print("Examples:")
        print("  python get_ohlc.py AAPL")
        print("  python get_ohlc.py SPY 2025-08-22")
        print("  python get_ohlc.py /NQ 2025-08-22")
        sys.exit(1)
    
    symbol = sys.argv[1]
    target_date = sys.argv[2] if len(sys.argv) > 2 else None
    
    asyncio.run(get_daily_ohlc(symbol, target_date))

if __name__ == "__main__":
    main()
