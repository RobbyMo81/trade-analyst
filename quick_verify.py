#!/usr/bin/env python3
"""
Quick OHLC Data Accuracy Check

Simple tool to quickly verify OHLC data accuracy using multiple methods.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add the app directory to Python path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

async def quick_verify(symbol: str, date: str):
    """Quick verification of OHLC data"""
    
    print(f"\n🔍 QUICK OHLC VERIFICATION: {symbol} on {date}")
    print("=" * 50)
    
    # Method 1: Get our system results manually
    print("\n1️⃣ OUR SYSTEM RESULTS")
    print("-" * 20)
    
    from app.config import Config
    from app.auth import AuthManager
    from app.historical import HistoricalInterface
    from app.providers import schwab as S
    from app.utils.futures import translate_root_to_front_month
    
    config = Config()
    auth_manager = AuthManager(config)
    historical = HistoricalInterface(config, auth_manager)
    
    translated_symbol = translate_root_to_front_month(symbol).upper()
    print(f"📝 Translated symbol: {symbol} -> {translated_symbol}")
    
    # Get the same data our system uses
    ohlc_records = await historical.get_latest_ohlc(translated_symbol, '1D', 1)
    
    if ohlc_records and len(ohlc_records) > 0:
        ohlc = ohlc_records[0]
        H = float(ohlc['high'])
        L = float(ohlc['low'])
        C = float(ohlc['close'])
        vwap = float(ohlc.get('vwap', C))
        
        # Calculate same as our system
        pivot = (H + L + C) / 3.0
        r1 = 2 * pivot - L
        s1 = 2 * pivot - H
        
        print(f"📊 System calculation results:")
        print(f"   R1: {r1:.4f}")
        print(f"   S1: {s1:.4f}")
        print(f"   VWAP: {vwap:.4f}")
        print(f"   Pivot: {pivot:.4f}")
    else:
        print("❌ No data available from our system")
    
    # Method 2: Manual calculation verification
    print("\n2️⃣ MANUAL VERIFICATION")
    print("-" * 22)
    
    if ohlc_records and len(ohlc_records) > 0:
        ohlc = ohlc_records[0]
        H = float(ohlc['high'])
        L = float(ohlc['low'])
        C = float(ohlc['close'])
        O = float(ohlc['open'])
        V = int(ohlc.get('volume', 0))
        vwap = float(ohlc.get('vwap', C))
        
        print(f"📊 Raw OHLC Data:")
        print(f"   Open:  ${O:.2f}")
        print(f"   High:  ${H:.2f}")
        print(f"   Low:   ${L:.2f}")
        print(f"   Close: ${C:.2f}")
        print(f"   Volume: {V:,}")
        print(f"   VWAP:  ${vwap:.2f}")
        
        # Manual pivot calculation
        pivot = (H + L + C) / 3.0
        r1 = 2 * pivot - L
        s1 = 2 * pivot - H
        
        print(f"\n🧮 Manual Pivot Calculations:")
        print(f"   Pivot = (H + L + C) / 3 = ({H} + {L} + {C}) / 3 = {pivot:.4f}")
        print(f"   R1 = 2 * Pivot - L = 2 * {pivot:.4f} - {L} = {r1:.4f}")
        print(f"   S1 = 2 * Pivot - H = 2 * {pivot:.4f} - {H} = {s1:.4f}")
        
        # Method 3: Reasonableness checks
        print(f"\n3️⃣ REASONABLENESS CHECKS")
        print("-" * 26)
        
        daily_range = (H - L) / C * 100 if C > 0 else 0
        print(f"✅ Daily range: {daily_range:.1f}% ({'reasonable' if daily_range < 10 else 'high volatility'})")
        
        print(f"✅ High >= Close: {H >= C} ({H} >= {C})")
        print(f"✅ Low <= Close: {L <= C} ({L} <= {C})")
        print(f"✅ High >= Open: {H >= O} ({H} >= {O})")
        print(f"✅ Low <= Open: {L <= O} ({L} <= {O})")
        print(f"✅ All prices positive: {all(p > 0 for p in [H, L, O, C])}")
        
        # Method 4: Compare with alternative calculation
        print(f"\n4️⃣ ALTERNATIVE FORMULAS")
        print("-" * 25)
        
        # Traditional pivot
        traditional_pivot = (H + L + C) / 3.0
        
        # Fibonacci pivot
        fib_pivot = (H + L + C) / 3.0  # Same as traditional for basic pivot
        
        # Woodie's pivot
        woodie_pivot = (H + L + 2 * C) / 4.0
        
        print(f"📊 Traditional Pivot: {traditional_pivot:.4f}")
        print(f"📈 Woodie's Pivot:    {woodie_pivot:.4f}")
        
        # Method 5: Data freshness check
        print(f"\n5️⃣ DATA FRESHNESS")
        print("-" * 19)
        
        data_timestamp = ohlc.get('datetime', '')
        if data_timestamp:
            try:
                dt = datetime.fromisoformat(data_timestamp.replace('Z', '+00:00'))
                now = datetime.now()
                age = now - dt.replace(tzinfo=None)
                print(f"📅 Data timestamp: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"⏰ Data age: {age.days} days, {age.seconds // 3600} hours")
                
                if age.days == 0:
                    print("✅ Fresh data (today)")
                elif age.days <= 3:
                    print("✅ Recent data (within 3 days)")
                else:
                    print(f"⚠️  Older data ({age.days} days old)")
            except Exception as e:
                print(f"❓ Could not parse timestamp: {data_timestamp}")
        
    else:
        print("❌ No OHLC data available")

def main():
    """Main function"""
    if len(sys.argv) < 3:
        print("Usage: python quick_verify.py SYMBOL DATE")
        print("Example: python quick_verify.py /NQ 2025-08-18")
        sys.exit(1)
    
    symbol = sys.argv[1]
    date = sys.argv[2]
    
    asyncio.run(quick_verify(symbol, date))

if __name__ == "__main__":
    main()
