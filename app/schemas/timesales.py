"""Time and sales (tick) data schema definitions"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd
from dataclasses import dataclass
from enum import Enum


class TradeSide(Enum):
    """Trade side enumeration"""
    BUY = "buy"
    SELL = "sell"
    UNKNOWN = "unknown"


class Exchange(Enum):
    """Common exchanges"""
    NYSE = "NYSE"
    NASDAQ = "NASDAQ"
    ARCA = "ARCA"
    BATS = "BATS"
    IEX = "IEX"
    OTHER = "OTHER"


@dataclass
class TimeSalesRecord:
    """Individual time and sales record"""
    symbol: str
    timestamp: datetime
    price: float
    size: int
    exchange: str
    side: TradeSide
    conditions: List[str]
    sequence: int


# Pandas DataFrame schema definition
TIMESALES_SCHEMA = {
    'symbol': 'string',
    'timestamp': 'datetime64[ns]',
    'price': 'float64',
    'size': 'int64',
    'exchange': 'string',
    'side': 'string',
    'conditions': 'object',  # List of strings
    'sequence': 'int64',
    'trade_id': 'string',
    'is_regular_hours': 'bool',
    'is_block_trade': 'bool',
    'cumulative_volume': 'int64'
}

# Required columns for time and sales data
REQUIRED_TIMESALES_COLUMNS = [
    'symbol', 'timestamp', 'price', 'size', 'exchange'
]

# Optional columns
OPTIONAL_TIMESALES_COLUMNS = [
    'side', 'conditions', 'sequence', 'trade_id', 
    'is_regular_hours', 'is_block_trade', 'cumulative_volume'
]

# Common trade conditions
TRADE_CONDITIONS = {
    'R': 'Regular Trade',
    'O': 'Opening Trade',
    'C': 'Closing Trade',
    'L': 'Last Trade',
    'T': 'Extended Hours Trade',
    'B': 'Block Trade',
    'I': 'Intermarket Sweep',
    'X': 'Cross Trade',
    'Z': 'Sold (Out of Sequence)',
    'P': 'Prior Reference Price',
    'Q': 'Market Center Official Close',
    'W': 'Average Price Trade',
    'N': 'Next Day Trade',
    'M': 'Market Center Official Open',
    'F': 'Intermarket Sweep',
    'U': 'Extended Trading Hours (Sold Out of Sequence)'
}


def validate_timesales_data(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate time and sales data structure and values
    
    Args:
        data: List of time and sales records
        
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
        for field in REQUIRED_TIMESALES_COLUMNS:
            if field not in record:
                validation_result['errors'].append(f"Record {i}: Missing required field '{field}'")
                validation_result['is_valid'] = False
        
        # Validate price
        if 'price' in record:
            try:
                price = float(record['price'])
                if price <= 0:
                    validation_result['errors'].append(f"Record {i}: Price must be positive")
                    validation_result['is_valid'] = False
            except (ValueError, TypeError):
                validation_result['errors'].append(f"Record {i}: Invalid price data type")
                validation_result['is_valid'] = False
        
        # Validate size
        if 'size' in record:
            try:
                size = int(record['size'])
                if size <= 0:
                    validation_result['errors'].append(f"Record {i}: Size must be positive")
                    validation_result['is_valid'] = False
                elif size > 10000000:  # 10M shares seems excessive for most trades
                    validation_result['warnings'].append(f"Record {i}: Very large trade size")
            except (ValueError, TypeError):
                validation_result['errors'].append(f"Record {i}: Invalid size data type")
                validation_result['is_valid'] = False
        
        # Validate timestamp
        if 'timestamp' in record:
            if not isinstance(record['timestamp'], (str, datetime)):
                validation_result['errors'].append(f"Record {i}: Invalid timestamp format")
                validation_result['is_valid'] = False
        
        # Validate exchange
        if 'exchange' in record:
            if not isinstance(record['exchange'], str):
                validation_result['errors'].append(f"Record {i}: Exchange must be a string")
                validation_result['is_valid'] = False
        
        # Validate side
        if 'side' in record and record['side'] is not None:
            valid_sides = [side.value for side in TradeSide]
            if record['side'].lower() not in valid_sides:
                validation_result['warnings'].append(f"Record {i}: Unknown trade side '{record['side']}'")
        
        # Validate conditions
        if 'conditions' in record and record['conditions'] is not None:
            if not isinstance(record['conditions'], list):
                validation_result['warnings'].append(f"Record {i}: Conditions should be a list")
        
        # Validate sequence
        if 'sequence' in record and record['sequence'] is not None:
            try:
                sequence = int(record['sequence'])
                if sequence < 0:
                    validation_result['warnings'].append(f"Record {i}: Negative sequence number")
            except (ValueError, TypeError):
                validation_result['warnings'].append(f"Record {i}: Invalid sequence data type")
    
    return validation_result


def normalize_timesales_data(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize time and sales data to standard format
    
    Args:
        data: List of time and sales records
        
    Returns:
        List of normalized records
    """
    normalized_data = []
    
    for record in data:
        normalized_record = {}
        
        # Copy required fields
        for field in REQUIRED_TIMESALES_COLUMNS:
            if field in record:
                if field == 'timestamp':
                    # Ensure timestamp is in ISO format
                    if isinstance(record[field], str):
                        normalized_record[field] = record[field]
                    elif isinstance(record[field], datetime):
                        normalized_record[field] = record[field].isoformat()
                elif field == 'price':
                    # Ensure price is float
                    normalized_record[field] = float(record[field])
                elif field == 'size':
                    # Ensure size is int
                    normalized_record[field] = int(record[field])
                else:
                    normalized_record[field] = record[field]
        
        # Copy optional fields if present
        for field in OPTIONAL_TIMESALES_COLUMNS:
            if field in record and record[field] is not None:
                if field == 'side':
                    # Normalize side
                    normalized_record[field] = record[field].lower()
                elif field == 'sequence':
                    normalized_record[field] = int(record[field])
                elif field in ['is_regular_hours', 'is_block_trade']:
                    normalized_record[field] = bool(record[field])
                elif field == 'cumulative_volume':
                    normalized_record[field] = int(record[field])
                elif field == 'conditions':
                    # Ensure conditions is a list
                    if isinstance(record[field], list):
                        normalized_record[field] = record[field]
                    elif isinstance(record[field], str):
                        normalized_record[field] = [record[field]]
                    else:
                        normalized_record[field] = []
                else:
                    normalized_record[field] = record[field]
        
        # Set defaults for optional fields
        if 'side' not in normalized_record:
            normalized_record['side'] = TradeSide.UNKNOWN.value
        
        if 'conditions' not in normalized_record:
            normalized_record['conditions'] = []
        
        if 'sequence' not in normalized_record:
            normalized_record['sequence'] = 0
        
        normalized_data.append(normalized_record)
    
    return normalized_data


def classify_trade_size(size: int) -> str:
    """
    Classify trade size into categories
    
    Args:
        size: Trade size in shares
        
    Returns:
        Trade size category
    """
    if size >= 100000:
        return 'institutional'
    elif size >= 50000:
        return 'large_block'
    elif size >= 10000:
        return 'block'
    elif size >= 1000:
        return 'large'
    elif size >= 100:
        return 'round_lot'
    else:
        return 'odd_lot'


def determine_regular_hours(timestamp: datetime, 
                           market_open: str = "09:30:00", 
                           market_close: str = "16:00:00") -> bool:
    """
    Determine if trade occurred during regular market hours
    
    Args:
        timestamp: Trade timestamp
        market_open: Market open time (HH:MM:SS)
        market_close: Market close time (HH:MM:SS)
        
    Returns:
        True if during regular hours
    """
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    
    trade_time = timestamp.time()
    
    from datetime import time
    open_time = time.fromisoformat(market_open)
    close_time = time.fromisoformat(market_close)
    
    return open_time <= trade_time <= close_time


def enrich_timesales_data(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enrich time and sales data with calculated fields
    
    Args:
        data: List of time and sales records
        
    Returns:
        List of enriched records
    """
    enriched_data = []
    cumulative_volume = 0
    
    for record in data.copy():
        # Add trade size classification
        if 'size' in record:
            record['size_category'] = classify_trade_size(record['size'])
            record['is_block_trade'] = record['size'] >= 10000
        
        # Add regular hours flag
        if 'timestamp' in record:
            timestamp = record['timestamp']
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            record['is_regular_hours'] = determine_regular_hours(timestamp)
        
        # Add cumulative volume
        if 'size' in record:
            cumulative_volume += record['size']
            record['cumulative_volume'] = cumulative_volume
        
        # Generate trade ID if not present
        if 'trade_id' not in record:
            # Simple trade ID generation
            import hashlib
            trade_data = f"{record.get('symbol', '')}{record.get('timestamp', '')}{record.get('price', '')}{record.get('size', '')}"
            record['trade_id'] = hashlib.md5(trade_data.encode()).hexdigest()[:12]
        
        # Decode trade conditions
        if 'conditions' in record and record['conditions']:
            decoded_conditions = []
            for condition in record['conditions']:
                if condition in TRADE_CONDITIONS:
                    decoded_conditions.append(TRADE_CONDITIONS[condition])
                else:
                    decoded_conditions.append(condition)
            record['decoded_conditions'] = decoded_conditions
        
        enriched_data.append(record)
    
    return enriched_data


def create_timesales_dataframe(data: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Create a pandas DataFrame from time and sales data with proper schema
    
    Args:
        data: List of time and sales records
        
    Returns:
        pandas DataFrame with time and sales data
    """
    if not data:
        # Return empty DataFrame with schema
        df = pd.DataFrame(columns=list(TIMESALES_SCHEMA.keys()))
        return df.astype({k: v for k, v in TIMESALES_SCHEMA.items() if k in df.columns})
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Convert timestamp column
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Apply schema
    for column, dtype in TIMESALES_SCHEMA.items():
        if column in df.columns:
            try:
                if dtype == 'string':
                    df[column] = df[column].astype('string')
                elif dtype != 'object':  # Skip object columns (like conditions list)
                    df[column] = df[column].astype(dtype)
            except (ValueError, TypeError):
                # Handle conversion errors gracefully
                pass
    
    return df


def calculate_timesales_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate metrics from time and sales data
    
    Args:
        df: DataFrame with time and sales data
        
    Returns:
        Dict containing calculated metrics
    """
    if df.empty:
        return {}
    
    metrics = {}
    
    try:
        # Basic statistics
        metrics['record_count'] = len(df)
        metrics['unique_prices'] = len(df['price'].unique()) if 'price' in df.columns else 0
        
        # Volume metrics
        if 'size' in df.columns:
            metrics['volume'] = {
                'total': int(df['size'].sum()),
                'average': float(df['size'].mean()),
                'median': float(df['size'].median()),
                'max': int(df['size'].max()),
                'min': int(df['size'].min())
            }
        
        # Price metrics
        if 'price' in df.columns:
            metrics['price'] = {
                'high': float(df['price'].max()),
                'low': float(df['price'].min()),
                'first': float(df['price'].iloc[0]),
                'last': float(df['price'].iloc[-1]),
                'average': float(df['price'].mean())
            }
            
            # Calculate VWAP
            if 'size' in df.columns:
                total_volume = df['size'].sum()
                if total_volume > 0:
                    vwap = (df['price'] * df['size']).sum() / total_volume
                    metrics['vwap'] = float(vwap)
        
        # Trade side distribution
        if 'side' in df.columns:
            side_counts = df['side'].value_counts().to_dict()
            metrics['side_distribution'] = side_counts
            
            # Buy/sell volume
            if 'size' in df.columns:
                buy_volume = df[df['side'] == 'buy']['size'].sum() if 'buy' in side_counts else 0
                sell_volume = df[df['side'] == 'sell']['size'].sum() if 'sell' in side_counts else 0
                metrics['buy_volume'] = int(buy_volume)
                metrics['sell_volume'] = int(sell_volume)
                
                if sell_volume > 0:
                    metrics['buy_sell_ratio'] = float(buy_volume / sell_volume)
        
        # Exchange distribution
        if 'exchange' in df.columns:
            exchange_counts = df['exchange'].value_counts().to_dict()
            metrics['exchange_distribution'] = exchange_counts
        
        # Trade size classification
        if 'size_category' in df.columns:
            size_category_counts = df['size_category'].value_counts().to_dict()
            metrics['size_category_distribution'] = size_category_counts
        
        # Block trades
        if 'is_block_trade' in df.columns:
            block_trades = df[df['is_block_trade'] == True]
            metrics['block_trades'] = {
                'count': len(block_trades),
                'volume': int(block_trades['size'].sum()) if 'size' in df.columns else 0,
                'percentage': float(len(block_trades) / len(df) * 100)
            }
        
        # Regular hours vs extended hours
        if 'is_regular_hours' in df.columns:
            regular_hours_trades = df[df['is_regular_hours'] == True]
            extended_hours_trades = df[df['is_regular_hours'] == False]
            
            metrics['trading_hours'] = {
                'regular_hours_count': len(regular_hours_trades),
                'extended_hours_count': len(extended_hours_trades),
                'regular_hours_volume': int(regular_hours_trades['size'].sum()) if 'size' in df.columns else 0,
                'extended_hours_volume': int(extended_hours_trades['size'].sum()) if 'size' in df.columns else 0
            }
        
        # Time range
        if 'timestamp' in df.columns:
            timestamps = pd.to_datetime(df['timestamp'])
            metrics['time_range'] = {
                'start': timestamps.min().isoformat(),
                'end': timestamps.max().isoformat(),
                'duration_minutes': float((timestamps.max() - timestamps.min()).total_seconds() / 60)
            }
            
            # Trade frequency
            if metrics['time_range']['duration_minutes'] > 0:
                metrics['trades_per_minute'] = float(len(df) / metrics['time_range']['duration_minutes'])
        
    except Exception as e:
        metrics['calculation_error'] = str(e)
    
    return metrics


# Example usage
def example_timesales_usage():
    """Example usage of time and sales schema functions"""
    
    # Sample time and sales data
    sample_data = [
        {
            'symbol': 'AAPL',
            'timestamp': '2024-01-01T10:00:00',
            'price': 150.25,
            'size': 100,
            'exchange': 'NASDAQ',
            'side': 'buy',
            'conditions': ['R'],
            'sequence': 1
        },
        {
            'symbol': 'AAPL',
            'timestamp': '2024-01-01T10:00:01',
            'price': 150.30,
            'size': 50000,
            'exchange': 'NYSE',
            'side': 'sell',
            'conditions': ['R', 'B'],
            'sequence': 2
        }
    ]
    
    # Validate data
    validation_result = validate_timesales_data(sample_data)
    print(f"Validation result: {validation_result}")
    
    # Normalize data
    normalized_data = normalize_timesales_data(sample_data)
    print(f"Normalized {len(normalized_data)} records")
    
    # Enrich data
    enriched_data = enrich_timesales_data(normalized_data)
    print(f"Enriched data with size category: {enriched_data[1].get('size_category')}")
    
    # Create DataFrame
    df = create_timesales_dataframe(enriched_data)
    print(f"Created DataFrame with shape: {df.shape}")
    
    # Calculate metrics
    metrics = calculate_timesales_metrics(df)
    print(f"Calculated metrics: {metrics}")


if __name__ == "__main__":
    example_timesales_usage()
