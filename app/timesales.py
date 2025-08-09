"""Interface for time and sales (tick tape) data"""

import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime, timedelta
import asyncio
from .config import Config
from .auth import AuthManager

logger = logging.getLogger(__name__)


class TimeSalesInterface:
    """Interface for retrieving time and sales (tick) data"""
    
    def __init__(self, config: Config, auth_manager: AuthManager):
        self.config = config
        self.auth_manager = auth_manager
        self.base_url = config.get('timesales_api_url', 'https://api.example.com/timesales')
        self.websocket_url = config.get('timesales_ws_url', 'wss://api.example.com/timesales')
    
    async def get_time_sales(self, 
                            symbol: str, 
                            start_time: datetime, 
                            end_time: datetime) -> Optional[List[Dict[str, Any]]]:
        """
        Get historical time and sales data for a symbol
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'MSFT')
            start_time: Start time for time and sales data
            end_time: End time for time and sales data
            
        Returns:
            List of time and sales records or None if error
        """
        try:
            logger.info(f"Fetching time and sales for {symbol} from {start_time} to {end_time}")
            
            # Get authentication token
            token = await self.auth_manager.get_access_token('timesales_provider')
            if not token:
                logger.error("No valid authentication token available")
                return None
            
            # Validate time range
            if start_time >= end_time:
                logger.error("Start time must be before end time")
                return None
            
            # TODO: Implement actual API call
            # This is a stub implementation
            time_sales_data = []
            current_time = start_time
            base_price = 150.00
            
            while current_time <= end_time:
                # Generate mock tick data
                for i in range(10):  # 10 ticks per minute
                    tick_time = current_time + timedelta(seconds=i * 6)
                    if tick_time > end_time:
                        break
                    
                    price_change = (i % 3 - 1) * 0.01  # Small price movements
                    tick = {
                        'symbol': symbol,
                        'timestamp': tick_time.isoformat(),
                        'price': base_price + price_change,
                        'size': 100 + (i * 50),
                        'exchange': 'NASDAQ' if i % 2 == 0 else 'NYSE',
                        'side': 'buy' if i % 2 == 0 else 'sell',
                        'conditions': ['R'] if i % 5 == 0 else [],  # Regular trade
                        'sequence': len(time_sales_data) + 1
                    }
                    time_sales_data.append(tick)
                
                current_time += timedelta(minutes=1)
                base_price += (len(time_sales_data) % 10 - 5) * 0.001  # Trend
            
            logger.info(f"Retrieved {len(time_sales_data)} time and sales records for {symbol}")
            return time_sales_data
            
        except Exception as e:
            logger.error(f"Failed to get time and sales for {symbol}: {e}")
            return None
    
    async def get_latest_trades(self, symbol: str, count: int = 100) -> Optional[List[Dict[str, Any]]]:
        """
        Get the latest trades for a symbol
        
        Args:
            symbol: Stock symbol
            count: Number of latest trades to retrieve
            
        Returns:
            List of latest trade records
        """
        try:
            logger.info(f"Fetching latest {count} trades for {symbol}")
            
            # Get authentication token
            token = await self.auth_manager.get_access_token('timesales_provider')
            if not token:
                logger.error("No valid authentication token available")
                return None
            
            # Get recent time range
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=1)  # Last hour
            
            # Get time and sales data
            time_sales_data = await self.get_time_sales(symbol, start_time, end_time)
            
            if time_sales_data:
                # Return latest trades
                return time_sales_data[-count:]
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get latest trades for {symbol}: {e}")
            return None
    
    async def stream_time_sales(self, symbols: List[str], callback=None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream real-time time and sales data
        
        Args:
            symbols: List of symbols to stream
            callback: Optional callback function for each tick
            
        Yields:
            Dict: Time and sales tick data
        """
        try:
            logger.info(f"Starting time and sales stream for {len(symbols)} symbols")
            
            # Get authentication token
            token = await self.auth_manager.get_access_token('timesales_provider')
            if not token:
                logger.error("No valid authentication token available")
                return
            
            # TODO: Implement WebSocket streaming
            # This is a stub implementation that simulates streaming
            while True:
                for symbol in symbols:
                    # Generate mock tick data
                    tick = {
                        'symbol': symbol,
                        'timestamp': datetime.now().isoformat(),
                        'price': 150.00 + (datetime.now().second % 10 * 0.01),
                        'size': 100 + (datetime.now().second * 10),
                        'exchange': 'NASDAQ',
                        'side': 'buy' if datetime.now().second % 2 == 0 else 'sell',
                        'conditions': [],
                        'sequence': datetime.now().microsecond
                    }
                    
                    if callback:
                        await callback(tick)
                    
                    yield tick
                
                # Wait before next batch
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Time and sales streaming failed: {e}")
    
    async def get_trade_analytics(self, 
                                 symbol: str, 
                                 start_time: datetime, 
                                 end_time: datetime) -> Optional[Dict[str, Any]]:
        """
        Get trade analytics for time and sales data
        
        Args:
            symbol: Stock symbol
            start_time: Start time for analysis
            end_time: End time for analysis
            
        Returns:
            Dict containing trade analytics
        """
        try:
            logger.info(f"Calculating trade analytics for {symbol}")
            
            # Get time and sales data
            time_sales_data = await self.get_time_sales(symbol, start_time, end_time)
            if not time_sales_data:
                return None
            
            # Calculate analytics
            total_trades = len(time_sales_data)
            total_volume = sum(trade['size'] for trade in time_sales_data)
            
            prices = [trade['price'] for trade in time_sales_data]
            vwap = sum(trade['price'] * trade['size'] for trade in time_sales_data) / total_volume if total_volume > 0 else 0
            
            buy_trades = [trade for trade in time_sales_data if trade['side'] == 'buy']
            sell_trades = [trade for trade in time_sales_data if trade['side'] == 'sell']
            
            buy_volume = sum(trade['size'] for trade in buy_trades)
            sell_volume = sum(trade['size'] for trade in sell_trades)
            
            analytics = {
                'symbol': symbol,
                'period_start': start_time.isoformat(),
                'period_end': end_time.isoformat(),
                'total_trades': total_trades,
                'total_volume': total_volume,
                'buy_trades': len(buy_trades),
                'sell_trades': len(sell_trades),
                'buy_volume': buy_volume,
                'sell_volume': sell_volume,
                'buy_sell_ratio': buy_volume / sell_volume if sell_volume > 0 else float('inf'),
                'vwap': round(vwap, 2),
                'price_range': {
                    'high': max(prices) if prices else 0,
                    'low': min(prices) if prices else 0,
                    'first': prices[0] if prices else 0,
                    'last': prices[-1] if prices else 0
                },
                'average_trade_size': total_volume / total_trades if total_trades > 0 else 0,
                'trade_frequency': total_trades / ((end_time - start_time).total_seconds() / 60) if (end_time - start_time).total_seconds() > 0 else 0,  # trades per minute
                'calculated_at': datetime.now().isoformat()
            }
            
            logger.info(f"Trade analytics calculated for {symbol}: {total_trades} trades, {total_volume:,} volume")
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to calculate trade analytics for {symbol}: {e}")
            return None
    
    async def get_block_trades(self, 
                              symbol: str, 
                              min_size: int = 10000, 
                              start_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Get block trades (large trades) for a symbol
        
        Args:
            symbol: Stock symbol
            min_size: Minimum trade size to be considered a block trade
            start_time: Start time for search (default: last 24 hours)
            
        Returns:
            List of block trade records
        """
        try:
            logger.info(f"Fetching block trades for {symbol} (min size: {min_size:,})")
            
            if not start_time:
                start_time = datetime.now() - timedelta(days=1)
            end_time = datetime.now()
            
            # Get time and sales data
            time_sales_data = await self.get_time_sales(symbol, start_time, end_time)
            if not time_sales_data:
                return []
            
            # Filter for block trades
            block_trades = [
                trade for trade in time_sales_data 
                if trade['size'] >= min_size
            ]
            
            # Add additional metrics to block trades
            for trade in block_trades:
                trade['is_block_trade'] = True
                trade['size_category'] = self._categorize_trade_size(trade['size'])
            
            logger.info(f"Found {len(block_trades)} block trades for {symbol}")
            return block_trades
            
        except Exception as e:
            logger.error(f"Failed to get block trades for {symbol}: {e}")
            return []
    
    def _categorize_trade_size(self, size: int) -> str:
        """Categorize trade size"""
        if size >= 100000:
            return 'institutional'
        elif size >= 50000:
            return 'large_block'
        elif size >= 10000:
            return 'block'
        else:
            return 'normal'


# Example usage and testing
async def main():
    """Example usage of TimeSalesInterface"""
    config = Config()
    auth_manager = AuthManager(config)
    timesales = TimeSalesInterface(config, auth_manager)
    
    # Define time range
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=1)
    
    # Get time and sales data
    time_sales_data = await timesales.get_time_sales('AAPL', start_time, end_time)
    print(f"Time and sales for AAPL: {len(time_sales_data) if time_sales_data else 0} ticks")
    
    # Get latest trades
    latest_trades = await timesales.get_latest_trades('AAPL', 10)
    print(f"Latest trades: {len(latest_trades) if latest_trades else 0} trades")
    
    # Get trade analytics
    if time_sales_data:
        analytics = await timesales.get_trade_analytics('AAPL', start_time, end_time)
        print(f"Trade analytics: {analytics['total_trades'] if analytics else 0} trades, VWAP: {analytics['vwap'] if analytics else 'N/A'}")
    
    # Get block trades
    block_trades = await timesales.get_block_trades('AAPL', min_size=5000)
    print(f"Block trades: {len(block_trades)} trades")


if __name__ == "__main__":
    asyncio.run(main())
