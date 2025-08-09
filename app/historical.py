"""Interface for historical OHLC (Open, High, Low, Close) data"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio
import pandas as pd
from .config import Config
from .auth import AuthManager

logger = logging.getLogger(__name__)


class HistoricalInterface:
    """Interface for retrieving historical OHLC data"""
    
    def __init__(self, config: Config, auth_manager: AuthManager):
        self.config = config
        self.auth_manager = auth_manager
        self.base_url = config.get('historical_api_url', 'https://api.example.com/historical')
    
    async def get_ohlc(self, 
                      symbol: str, 
                      start_date: datetime, 
                      end_date: datetime, 
                      interval: str = '1D') -> Optional[List[Dict[str, Any]]]:
        """
        Get historical OHLC data for a symbol
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'MSFT')
            start_date: Start date for historical data
            end_date: End date for historical data
            interval: Data interval ('1m', '5m', '15m', '1h', '1D', '1W', '1M')
            
        Returns:
            List of OHLC records or None if error
        """
        try:
            logger.info(f"Fetching OHLC data for {symbol} from {start_date} to {end_date}, interval: {interval}")
            
            # Get authentication token
            token = await self.auth_manager.get_access_token('historical_provider')
            if not token:
                logger.error("No valid authentication token available")
                return None
            
            # Validate date range
            if start_date >= end_date:
                logger.error("Start date must be before end date")
                return None
            
            # TODO: Implement actual API call
            # This is a stub implementation
            ohlc_data = []
            current_date = start_date
            
            while current_date <= end_date:
                ohlc_record = {
                    'symbol': symbol,
                    'datetime': current_date.isoformat(),
                    'open': 150.00 + (current_date.day % 10),
                    'high': 155.00 + (current_date.day % 10),
                    'low': 148.00 + (current_date.day % 10),
                    'close': 152.00 + (current_date.day % 10),
                    'volume': 1000000 + (current_date.day * 50000),
                    'vwap': 151.50 + (current_date.day % 10),
                    'interval': interval
                }
                ohlc_data.append(ohlc_record)
                
                # Increment date based on interval
                if interval == '1D':
                    current_date += timedelta(days=1)
                elif interval == '1W':
                    current_date += timedelta(weeks=1)
                elif interval == '1M':
                    current_date += timedelta(days=30)
                else:
                    # For intraday intervals, just add a day for this stub
                    current_date += timedelta(days=1)
            
            logger.info(f"Retrieved {len(ohlc_data)} OHLC records for {symbol}")
            return ohlc_data
            
        except Exception as e:
            logger.error(f"Failed to get OHLC data for {symbol}: {e}")
            return None
    
    async def get_ohlc_dataframe(self, 
                                symbol: str, 
                                start_date: datetime, 
                                end_date: datetime, 
                                interval: str = '1D') -> Optional[pd.DataFrame]:
        """
        Get historical OHLC data as pandas DataFrame
        
        Args:
            symbol: Stock symbol
            start_date: Start date for historical data
            end_date: End date for historical data
            interval: Data interval
            
        Returns:
            pandas DataFrame with OHLC data
        """
        try:
            ohlc_data = await self.get_ohlc(symbol, start_date, end_date, interval)
            if not ohlc_data:
                return None
            
            df = pd.DataFrame(ohlc_data)
            df['datetime'] = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)
            
            logger.info(f"Created DataFrame with {len(df)} records for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Failed to create DataFrame for {symbol}: {e}")
            return None
    
    async def get_multi_symbol_ohlc(self, 
                                   symbols: List[str], 
                                   start_date: datetime, 
                                   end_date: datetime, 
                                   interval: str = '1D') -> Dict[str, List[Dict[str, Any]]]:
        """
        Get historical OHLC data for multiple symbols
        
        Args:
            symbols: List of stock symbols
            start_date: Start date for historical data
            end_date: End date for historical data
            interval: Data interval
            
        Returns:
            Dict mapping symbols to OHLC data
        """
        try:
            logger.info(f"Fetching OHLC data for {len(symbols)} symbols")
            
            # Get OHLC data for all symbols concurrently
            tasks = [self.get_ohlc(symbol, start_date, end_date, interval) for symbol in symbols]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            ohlc_data = {}
            for symbol, result in zip(symbols, results):
                if isinstance(result, Exception):
                    logger.error(f"Error getting OHLC data for {symbol}: {result}")
                    continue
                
                if result:
                    ohlc_data[symbol] = result
            
            logger.info(f"Retrieved OHLC data for {len(ohlc_data)} symbols")
            return ohlc_data
            
        except Exception as e:
            logger.error(f"Failed to get multi-symbol OHLC data: {e}")
            return {}
    
    async def get_latest_ohlc(self, symbol: str, interval: str = '1D', count: int = 10) -> Optional[List[Dict[str, Any]]]:
        """
        Get latest OHLC records for a symbol
        
        Args:
            symbol: Stock symbol
            interval: Data interval
            count: Number of latest records to retrieve
            
        Returns:
            List of latest OHLC records
        """
        try:
            logger.info(f"Fetching latest {count} OHLC records for {symbol}")
            
            # Calculate date range for latest records
            end_date = datetime.now()
            if interval == '1D':
                start_date = end_date - timedelta(days=count * 2)  # Buffer for weekends
            elif interval == '1W':
                start_date = end_date - timedelta(weeks=count)
            elif interval == '1M':
                start_date = end_date - timedelta(days=count * 32)
            else:
                start_date = end_date - timedelta(days=count)
            
            ohlc_data = await self.get_ohlc(symbol, start_date, end_date, interval)
            
            if ohlc_data:
                # Return latest records
                return ohlc_data[-count:]
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get latest OHLC data for {symbol}: {e}")
            return None
    
    async def calculate_technical_indicators(self, ohlc_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate basic technical indicators from OHLC data
        
        Args:
            ohlc_data: List of OHLC records
            
        Returns:
            Dict containing calculated indicators
        """
        try:
            if not ohlc_data:
                return {}
            
            # Convert to DataFrame for easier calculation
            df = pd.DataFrame(ohlc_data)
            df['datetime'] = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)
            
            indicators = {}
            
            # Simple Moving Averages
            if len(df) >= 20:
                indicators['sma_20'] = df['close'].rolling(window=20).mean().iloc[-1]
            if len(df) >= 50:
                indicators['sma_50'] = df['close'].rolling(window=50).mean().iloc[-1]
            
            # Price change metrics
            if len(df) >= 2:
                indicators['price_change'] = df['close'].iloc[-1] - df['close'].iloc[-2]
                indicators['price_change_percent'] = (indicators['price_change'] / df['close'].iloc[-2]) * 100
            
            # Volume metrics
            if len(df) >= 20:
                indicators['avg_volume_20'] = df['volume'].rolling(window=20).mean().iloc[-1]
            
            # High/Low metrics
            if len(df) >= 52:
                indicators['52_week_high'] = df['high'].rolling(window=252).max().iloc[-1]
                indicators['52_week_low'] = df['low'].rolling(window=252).min().iloc[-1]
            
            logger.info(f"Calculated {len(indicators)} technical indicators")
            return indicators
            
        except Exception as e:
            logger.error(f"Failed to calculate technical indicators: {e}")
            return {}


# Example usage and testing
async def main():
    """Example usage of HistoricalInterface"""
    config = Config()
    auth_manager = AuthManager(config)
    historical = HistoricalInterface(config, auth_manager)
    
    # Define date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Get OHLC data
    ohlc_data = await historical.get_ohlc('AAPL', start_date, end_date, '1D')
    print(f"OHLC data for AAPL: {len(ohlc_data) if ohlc_data else 0} records")
    
    # Get latest OHLC
    latest_ohlc = await historical.get_latest_ohlc('AAPL', '1D', 5)
    print(f"Latest OHLC: {len(latest_ohlc) if latest_ohlc else 0} records")
    
    # Calculate technical indicators
    if ohlc_data:
        indicators = await historical.calculate_technical_indicators(ohlc_data)
        print(f"Technical indicators: {indicators}")


if __name__ == "__main__":
    asyncio.run(main())
