#!/usr/bin/env python3
"""Get current /NQ price data"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add the app directory to Python path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

async def get_current_nq():
    print('🔍 Fetching current /NQ price data...')
    
    from app.config import Config
    from app.auth import AuthManager
    from app.providers import schwab as S
    from app.utils.futures import translate_root_to_front_month
    
    # Initialize
    config = Config()
    auth_manager = AuthManager(config)
    client = S.SchwabClient(auth=auth_manager, config=config)
    
    # Translate /NQ to contract symbol
    symbol = '/NQ'
    translated = translate_root_to_front_month(symbol).upper()
    print(f'📝 Symbol translation: {symbol} -> {translated}')
    
    # Get current quote
    result = await client.quotes([translated])
    
    if result and 'records' in result and result['records']:
        quote = result['records'][0]
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print()
        print(f'📊 CURRENT /NQ PRICE DATA ({timestamp})')
        print('=' * 50)
        print(f'Symbol: {quote.get("symbol", translated)}')
        print(f'Bid: ${quote.get("bid", "N/A")}')
        print(f'Ask: ${quote.get("ask", "N/A")}')
        
        bid = float(quote.get('bid', 0)) if quote.get('bid') else 0
        ask = float(quote.get('ask', 0)) if quote.get('ask') else 0
        
        if bid > 0 and ask > 0:
            mid = (bid + ask) / 2
            spread = ask - bid
            print(f'Mid Price: ${mid:.2f}')
            print(f'Spread: ${spread:.2f}')
            print(f'Spread %: {(spread/mid*100):.3f}%')
        
        # Additional quote data if available
        print()
        print('📈 Additional Market Data:')
        print('-' * 25)
        
        for field, label in [
            ('last', 'Last Price'), 
            ('volume', 'Volume'),
            ('change', 'Change'),
            ('changePercent', 'Change %'),
            ('high', 'Day High'),
            ('low', 'Day Low'),
            ('open', 'Open')
        ]:
            if field in quote and quote[field] is not None:
                value = quote[field]
                if field == 'volume':
                    print(f'{label}: {int(value):,}')
                elif field in ['change', 'changePercent']:
                    print(f'{label}: {value}')
                elif field in ['high', 'low', 'open', 'last']:
                    print(f'{label}: ${float(value):.2f}')
        
        print()
        print('🕒 Real-time quote retrieved successfully')
        
    else:
        print('❌ No current quote data available')
        if result:
            print(f'Raw result keys: {list(result.keys()) if isinstance(result, dict) else type(result)}')

if __name__ == "__main__":
    asyncio.run(get_current_nq())
