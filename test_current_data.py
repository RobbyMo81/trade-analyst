#!/usr/bin/env python3
"""Test different methods to get current /NQ price data"""
import asyncio
import sys
from pathlib import Path

# Add the app directory to Python path  
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

async def test_current_data():
    from app.config import Config
    from app.auth import AuthManager
    from app.quotes import QuotesInterface
    from app.providers import schwab as S
    from app.utils.futures import translate_root_to_front_month
    
    config = Config()
    auth_manager = AuthManager(config)
    
    print("🔍 Testing multiple methods to get current /NQ data...")
    print("=" * 60)
    
    # Method 1: Direct Schwab client  
    print("\n1️⃣ SCHWAB CLIENT DIRECT")
    print("-" * 25)
    try:
        client = S.SchwabClient(auth=auth_manager, config=config)
        
        # Try different contract months
        test_symbols = ['NQU25', 'NQZ25', 'NQH26']  # Aug, Dec, March
        
        for symbol in test_symbols:
            print(f"Testing {symbol}...")
            result = await client.quotes([symbol])
            
            if result and 'records' in result and result['records']:
                quote = result['records'][0]
                print(f"✅ {symbol} found:")
                print(f"   Bid: ${quote.get('bid', 'N/A')}")
                print(f"   Ask: ${quote.get('ask', 'N/A')}")
                break
            else:
                print(f"❌ {symbol} - no data")
        else:
            print("❌ No futures data found via Schwab client")
    
    except Exception as e:
        print(f"❌ Schwab client error: {e}")
    
    # Method 2: Quotes Interface
    print("\n2️⃣ QUOTES INTERFACE")  
    print("-" * 20)
    try:
        quotes = QuotesInterface(config, auth_manager)
        
        # Test with stock symbol first to verify connection
        print("Testing AAPL for connection verification...")
        aapl_result = await quotes.get_quote('AAPL')
        if aapl_result:
            print(f"✅ Connection OK - AAPL price: ${aapl_result.get('price', 'N/A')}")
        else:
            print("❌ Connection issue - no AAPL data")
            
        # Now try NQ
        nq_result = await quotes.get_quote('/NQ')
        if nq_result:
            print(f"✅ /NQ data: ${nq_result.get('price', 'N/A')}")
        else:
            print("❌ No /NQ data via quotes interface")
            
    except Exception as e:
        print(f"❌ Quotes interface error: {e}")
    
    # Method 3: Check what our calc-levels system would return
    print("\n3️⃣ CALC-LEVELS SYSTEM DATA")
    print("-" * 28)
    try:
        from app.historical import HistoricalInterface
        
        historical = HistoricalInterface(config, auth_manager)
        symbol = translate_root_to_front_month('/NQ').upper()
        
        ohlc_data = await historical.get_latest_ohlc(symbol, '1D', 1)
        
        if ohlc_data:
            recent = ohlc_data[0]
            print(f"✅ Latest OHLC for {symbol}:")
            print(f"   Open: ${recent.get('open', 'N/A')}")
            print(f"   High: ${recent.get('high', 'N/A')}")
            print(f"   Low: ${recent.get('low', 'N/A')}")
            print(f"   Close: ${recent.get('close', 'N/A')}")
            print(f"   VWAP: ${recent.get('vwap', 'N/A')}")
            print(f"   Date: {recent.get('datetime', 'N/A')}")
        else:
            print("❌ No historical OHLC data")
            
    except Exception as e:
        print(f"❌ Historical data error: {e}")
    
    print("\n" + "=" * 60)
    print("📝 Note: Market may be closed or data delayed")
    print("📝 Futures data requires specific contract symbols")

if __name__ == "__main__":
    asyncio.run(test_current_data())
