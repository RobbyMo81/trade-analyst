"""OHLC (Open, High, Low, Close) data schema definitions"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd
from dataclasses import dataclass


@dataclass
class OHLCRecord:
    """Individual OHLC record"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    interval: str = '1D'  # 1m, 5m, 15m, 1h, 1D, 1W, 1M
    vwap: Optional[float] = None
    adj_close: Optional[float] = None
    dividend: Optional[float] = None
    split_coefficient: Optional[float] = None


# Pandas DataFrame schema definition
OHLC_SCHEMA = {
    'symbol': 'string',
    'timestamp': 'datetime64[ns]',
    'open': 'float64',
    'high': 'float64',
    'low': 'float64',
    'close': 'float64',
    'volume': 'int64',
    'interval': 'string',
    'vwap': 'float64',
    'adj_close': 'float64',
    'dividend': 'float64',
    'split_coefficient': 'float64'
}

# Required columns for OHLC data
REQUIRED_OHLC_COLUMNS = [
    'symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume'
]

# Optional columns
OPTIONAL_OHLC_COLUMNS = [
    'interval', 'vwap', 'adj_close', 'dividend', 'split_coefficient'
]


def validate_ohlc_data(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate OHLC data structure and values
    
    Args:
        data: List of OHLC records
        
    Returns:
        Dict containing validation results
    """
    validation_result = {
        'is_valid': True,
        'errors': [],
        'warnings': [],
        'record_count': len(data)
    }
    
    if not data:
        validation_result['errors'].append("No data provided")
        validation_result['is_valid'] = False
        return validation_result
    
    for i, record in enumerate(data):
        # Check required fields
        for field in REQUIRED_OHLC_COLUMNS:
            if field not in record:
                validation_result['errors'].append(f"Record {i}: Missing required field '{field}'")
                validation_result['is_valid'] = False
        
        # Validate data types and values
        if 'open' in record and 'high' in record and 'low' in record and 'close' in record:
            try:
                open_price = float(record['open'])
                high_price = float(record['high'])
                low_price = float(record['low'])
                close_price = float(record['close'])
                
                # OHLC logic validation
                if high_price < max(open_price, close_price):
                    validation_result['warnings'].append(f"Record {i}: High price lower than open/close")
                
                if low_price > min(open_price, close_price):
                    validation_result['warnings'].append(f"Record {i}: Low price higher than open/close")
                
                if any(price <= 0 for price in [open_price, high_price, low_price, close_price]):
                    validation_result['errors'].append(f"Record {i}: Prices must be positive")
                    validation_result['is_valid'] = False
                    
            except (ValueError, TypeError):
                validation_result['errors'].append(f"Record {i}: Invalid price data types")
                validation_result['is_valid'] = False
        
        # Validate volume
        if 'volume' in record:
            try:
                volume = int(record['volume'])
                if volume < 0:
                    validation_result['warnings'].append(f"Record {i}: Negative volume")
            except (ValueError, TypeError):
                validation_result['errors'].append(f"Record {i}: Invalid volume data type")
                validation_result['is_valid'] = False
        
        # Validate timestamp
        if 'timestamp' in record:
            if not isinstance(record['timestamp'], (str, datetime)):
                validation_result['errors'].append(f"Record {i}: Invalid timestamp format")
                validation_result['is_valid'] = False
    
    return validation_result


def normalize_ohlc_data(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize OHLC data to standard format
    
    Args:
        data: List of OHLC records
        
    Returns:
        List of normalized OHLC records
    """
    normalized_data = []
    
    for record in data:
        normalized_record = {}
        
        # Copy required fields
        for field in REQUIRED_OHLC_COLUMNS:
            if field in record:
                if field == 'timestamp':
                    # Ensure timestamp is in ISO format
                    if isinstance(record[field], str):
                        normalized_record[field] = record[field]
                    elif isinstance(record[field], datetime):
                        normalized_record[field] = record[field].isoformat()
                elif field in ['open', 'high', 'low', 'close']:
                    # Ensure prices are floats
                    normalized_record[field] = float(record[field])
                elif field == 'volume':
                    # Ensure volume is int
                    normalized_record[field] = int(record[field])
                else:
                    normalized_record[field] = record[field]
        
        # Copy optional fields if present
        for field in OPTIONAL_OHLC_COLUMNS:
            if field in record and record[field] is not None:
                if field in ['vwap', 'adj_close', 'dividend', 'split_coefficient']:
                    normalized_record[field] = float(record[field])
                else:
                    normalized_record[field] = record[field]
        
        # Set default interval if not provided
        if 'interval' not in normalized_record:
            normalized_record['interval'] = '1D'
        
        normalized_data.append(normalized_record)
    
    return normalized_data


def create_ohlc_dataframe(data: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Create a pandas DataFrame from OHLC data with proper schema
    
    Args:
        data: List of OHLC records
        
    Returns:
        pandas DataFrame with OHLC data
    """
    if not data:
        # Return empty DataFrame with schema
        df = pd.DataFrame(columns=list(OHLC_SCHEMA.keys()))
        return df.astype(OHLC_SCHEMA)
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Convert timestamp column
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Apply schema
    for column, dtype in OHLC_SCHEMA.items():
        if column in df.columns:
            try:
                if dtype == 'string':
                    df[column] = df[column].astype('string')
                else:
                    df[column] = df[column].astype(dtype)
            except (ValueError, TypeError):
                # Handle conversion errors gracefully
                pass
    
    return df


def calculate_ohlc_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate basic metrics from OHLC data
    
    Args:
        df: DataFrame with OHLC data
        
    Returns:
        Dict containing calculated metrics
    """
    if df.empty:
        return {}
    
    metrics = {}
    
    try:
        # Price metrics
        metrics['price_range'] = {
            'high': float(df['high'].max()),
            'low': float(df['low'].min()),
            'first_open': float(df.iloc[0]['open']),
            'last_close': float(df.iloc[-1]['close'])
        }
        
        # Volume metrics
        metrics['volume'] = {
            'total': int(df['volume'].sum()),
            'average': float(df['volume'].mean()),
            'max': int(df['volume'].max()),
            'min': int(df['volume'].min())
        }
        
        # Calculate returns if we have close prices
        if len(df) > 1:
            returns = df['close'].pct_change().dropna()
            metrics['returns'] = {
                'mean': float(returns.mean()),
                'std': float(returns.std()),
                'min': float(returns.min()),
                'max': float(returns.max())
            }
        
        # VWAP if available
        if 'vwap' in df.columns and not df['vwap'].isna().all():
            metrics['vwap'] = {
                'average': float(df['vwap'].mean()),
                'last': float(df['vwap'].iloc[-1])
            }
        
        # Calculate simple moving averages
        if len(df) >= 20:
            metrics['sma_20'] = float(df['close'].rolling(window=20).mean().iloc[-1])
        
        if len(df) >= 50:
            metrics['sma_50'] = float(df['close'].rolling(window=50).mean().iloc[-1])
        
        metrics['record_count'] = len(df)
        
    except Exception as e:
        metrics['calculation_error'] = str(e)
    
    return metrics


# Example usage
def example_ohlc_usage():
    """Example usage of OHLC schema functions"""
    
    # Sample OHLC data
    sample_data = [
        {
            'symbol': 'AAPL',
            'timestamp': '2024-01-01T09:30:00',
            'open': 150.0,
            'high': 152.0,
            'low': 149.0,
            'close': 151.0,
            'volume': 1000000,
            'interval': '1D'
        },
        {
            'symbol': 'AAPL',
            'timestamp': '2024-01-02T09:30:00',
            'open': 151.0,
            'high': 153.0,
            'low': 150.0,
            'close': 152.0,
            'volume': 1100000,
            'interval': '1D'
        }
    ]
    
    # Validate data
    validation_result = validate_ohlc_data(sample_data)
    print(f"Validation result: {validation_result}")
    
    # Normalize data
    normalized_data = normalize_ohlc_data(sample_data)
    print(f"Normalized {len(normalized_data)} records")
    
    # Create DataFrame
    df = create_ohlc_dataframe(normalized_data)
    print(f"Created DataFrame with shape: {df.shape}")
    
    # Calculate metrics
    metrics = calculate_ohlc_metrics(df)
    print(f"Calculated metrics: {metrics}")


if __name__ == "__main__":
    example_ohlc_usage()
