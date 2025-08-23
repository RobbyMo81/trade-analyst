#!/usr/bin/env python3
"""
Enhanced OHLC retrieval with futures-to-ETF mapping for historical data.
"""

import asyncio
import sys
from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any
from app.config import Config
from app.auth import AuthManager
from app.production_provider import ProductionDataProvider
from app.utils.futures_symbols import get_futures_info, get_front_month_contract

# Futures to ETF mapping for historical data
FUTURES_ETF_MAPPING = {
    # Indices
    "/ES": "SPY",     # E-mini S&P 500 -> SPDR S&P 500 ETF
    "/NQ": "QQQ",     # E-mini NASDAQ 100 -> Invesco QQQ ETF  
    "/RTY": "IWM",    # E-mini Russell 2000 -> iShares Russell 2000 ETF
    "/YM": "DIA",     # E-mini Dow -> SPDR Dow Jones Industrial Average ETF
    
    # Energy
    "/CL": "USO",     # Crude Oil -> United States Oil Fund
    "/NG": "UNG",     # Natural Gas -> United States Natural Gas Fund
    "/RB": "UGA",     # RBOB Gasoline -> United States Gasoline Fund
    "/HO": "UHN",     # Heating Oil -> United States Heating Oil Fund
    
    # Metals
    "/GC": "GLD",     # Gold -> SPDR Gold Shares
    "/SI": "SLV",     # Silver -> iShares Silver Trust
    "/HG": "CPER",    # Copper -> United States Copper Index Fund
    "/PL": "PPLT",    # Platinum -> Aberdeen Standard Platinum Shares ETF
    
    # Currency (limited ETF options)
    "/6E": "FXE",     # Euro -> Invesco CurrencyShares Euro Trust
    "/6J": "FXY",     # Japanese Yen -> Invesco CurrencyShares Japanese Yen Trust
    "/6B": "FXB",     # British Pound -> Invesco CurrencyShares British Pound Sterling Trust
    
    # Grains (agricultural ETFs)
    "/ZC": "CORN",    # Corn -> Teucrium Corn Fund
    "/ZS": "SOYB",    # Soybeans -> Teucrium Soybean Fund  
    "/ZW": "WEAT",    # Wheat -> Teucrium Wheat Fund
    
    # Interest Rates (bond ETFs)
    "/ZB": "TLT",     # 30-Year Treasury Bond -> iShares 20+ Year Treasury Bond ETF
    "/ZN": "IEF",     # 10-Year Treasury Note -> iShares 7-10 Year Treasury Bond ETF
    "/ZF": "IEI",     # 5-Year Treasury Note -> iShares 3-7 Year Treasury Bond ETF
    "/ZT": "SHY",     # 2-Year Treasury Note -> iShares 1-3 Year Treasury Bond ETF
    
    # Livestock (limited options)
    "/LE": "COW",     # Live Cattle -> iPath Series B Bloomberg Livestock Subindex Total Return ETN
    "/HE": "COW",     # Lean Hogs -> iPath Series B Bloomberg Livestock Subindex Total Return ETN
}

async def get_daily_ohlc_with_fallback(symbol: str, target_date: Optional[str] = None):
    """Get daily OHLC data with automatic futures-to-ETF fallback."""
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
        
        # Check if this is a futures symbol and show info
        original_symbol = symbol
        futures_info = get_futures_info(symbol)
        if futures_info:
            print(f"\nFutures Symbol Detected: {futures_info.description} ({futures_info.category.value})")
            front_month = get_front_month_contract(futures_info.root)
            if front_month:
                print(f"Contract Translation: {symbol} -> {front_month.symbol}")
        
        # Try to get OHLC data directly first
        print(f"\nRetrieving daily OHLC for {symbol} on {trade_date}...")
        try:
            ohlc_data = await provider.get_daily_ohlc(symbol, trade_date)
            
            if ohlc_data:
                display_ohlc_data(original_symbol, symbol, trade_date, ohlc_data, "Direct")
                return
        except SystemExit:
            # This means the provider failed with an error - continue to ETF fallback
            pass
        except Exception as e:
            print(f"Direct retrieval failed: {e}")
        
        # If direct retrieval failed and this is a futures symbol, try ETF equivalent
        if symbol in FUTURES_ETF_MAPPING:
            etf_symbol = FUTURES_ETF_MAPPING[symbol]
            print(f"\nDirect futures data unavailable. Trying ETF equivalent: {etf_symbol}")
            print(f"Note: {etf_symbol} tracks similar underlying asset as {symbol}")
            
            try:
                ohlc_data = await provider.get_daily_ohlc(etf_symbol, trade_date)
                
                if ohlc_data:
                    display_ohlc_data(original_symbol, etf_symbol, trade_date, ohlc_data, "ETF Equivalent")
                    return
                else:
                    print(f"No data available for ETF equivalent {etf_symbol} either.")
            except SystemExit:
                print(f"ETF equivalent {etf_symbol} also failed.")
            except Exception as e:
                print(f"ETF retrieval failed: {e}")
        
        # If we get here, no data was found
        print(f"\nNo OHLC data found for {original_symbol} on {trade_date}")
        if symbol not in FUTURES_ETF_MAPPING and futures_info:
            print("Note: Schwab retail API doesn't provide futures historical data.")
            print("Consider using equity index ETFs like SPY (for /ES) or QQQ (for /NQ).")
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def display_ohlc_data(original_symbol: str, retrieved_symbol: str, trade_date: date, ohlc_data: Any, data_type: str):
    """Display OHLC data in a formatted way."""
    print(f"\n=== Daily OHLC Data ({data_type}) ===")
    print(f"Requested Symbol: {original_symbol}")
    if original_symbol != retrieved_symbol:
        print(f"Data Source Symbol: {retrieved_symbol}")
    print(f"Date: {trade_date}")
    print(f"Open:   ${ohlc_data.open:.4f}")
    print(f"High:   ${ohlc_data.high:.4f}")
    print(f"Low:    ${ohlc_data.low:.4f}")
    print(f"Close:  ${ohlc_data.close:.4f}")
    print(f"Volume: {ohlc_data.volume:,}")
    print(f"Timestamp: {ohlc_data.timestamp}")

def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python get_ohlc_enhanced.py <SYMBOL> [YYYY-MM-DD]")
        print("Examples:")
        print("  python get_ohlc_enhanced.py AAPL")
        print("  python get_ohlc_enhanced.py SPY 2025-08-22")
        print("  python get_ohlc_enhanced.py /NQ 2025-08-22   # Will use QQQ as ETF equivalent")
        print("  python get_ohlc_enhanced.py /ES 2025-08-22   # Will use SPY as ETF equivalent")
        print("\nSupported Futures with ETF Equivalents:")
        for futures, etf in FUTURES_ETF_MAPPING.items():
            print(f"  {futures:<6} -> {etf}")
        sys.exit(1)
    
    symbol = sys.argv[1]
    target_date = sys.argv[2] if len(sys.argv) > 2 else None
    
    asyncio.run(get_daily_ohlc_with_fallback(symbol, target_date))

if __name__ == "__main__":
    main()
