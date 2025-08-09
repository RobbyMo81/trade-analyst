"""Options data schema definitions"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd
from dataclasses import dataclass
from enum import Enum


class OptionType(Enum):
    """Option type enumeration"""
    CALL = "call"
    PUT = "put"


class Moneyness(Enum):
    """Option moneyness enumeration"""
    ITM = "ITM"  # In the Money
    ATM = "ATM"  # At the Money
    OTM = "OTM"  # Out of the Money


@dataclass
class OptionRecord:
    """Individual option record"""
    symbol: str
    underlying_symbol: str
    option_type: OptionType
    strike: float
    expiration: datetime
    bid: float
    ask: float
    last: float
    volume: int
    open_interest: int
    implied_volatility: float
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    rho: Optional[float] = None


# Pandas DataFrame schema definition
OPTIONS_SCHEMA = {
    'symbol': 'string',
    'underlying_symbol': 'string',
    'option_type': 'string',
    'strike': 'float64',
    'expiration': 'datetime64[ns]',
    'bid': 'float64',
    'ask': 'float64',
    'last': 'float64',
    'volume': 'int64',
    'open_interest': 'int64',
    'implied_volatility': 'float64',
    'delta': 'float64',
    'gamma': 'float64',
    'theta': 'float64',
    'vega': 'float64',
    'rho': 'float64',
    'timestamp': 'datetime64[ns]',
    'underlying_price': 'float64',
    'days_to_expiration': 'int64',
    'moneyness': 'string'
}

# Required columns for options data
REQUIRED_OPTIONS_COLUMNS = [
    'symbol', 'underlying_symbol', 'option_type', 'strike', 'expiration',
    'bid', 'ask', 'last', 'volume', 'open_interest', 'implied_volatility'
]

# Optional columns (Greeks and additional metrics)
OPTIONAL_OPTIONS_COLUMNS = [
    'delta', 'gamma', 'theta', 'vega', 'rho', 'timestamp',
    'underlying_price', 'days_to_expiration', 'moneyness'
]


def validate_options_data(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate options data structure and values
    
    Args:
        data: List of option records
        
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
        for field in REQUIRED_OPTIONS_COLUMNS:
            if field not in record:
                validation_result['errors'].append(f"Record {i}: Missing required field '{field}'")
                validation_result['is_valid'] = False
        
        # Validate option type
        if 'option_type' in record:
            if record['option_type'].lower() not in ['call', 'put']:
                validation_result['errors'].append(f"Record {i}: Invalid option type '{record['option_type']}'")
                validation_result['is_valid'] = False
        
        # Validate prices
        price_fields = ['bid', 'ask', 'last', 'strike']
        for field in price_fields:
            if field in record:
                try:
                    price = float(record[field])
                    if price < 0:
                        validation_result['errors'].append(f"Record {i}: {field} cannot be negative")
                        validation_result['is_valid'] = False
                except (ValueError, TypeError):
                    validation_result['errors'].append(f"Record {i}: Invalid {field} data type")
                    validation_result['is_valid'] = False
        
        # Validate bid/ask spread
        if 'bid' in record and 'ask' in record:
            try:
                bid = float(record['bid'])
                ask = float(record['ask'])
                if bid > ask:
                    validation_result['warnings'].append(f"Record {i}: Bid price higher than ask price")
            except (ValueError, TypeError):
                pass  # Already reported above
        
        # Validate volume and open interest
        for field in ['volume', 'open_interest']:
            if field in record:
                try:
                    value = int(record[field])
                    if value < 0:
                        validation_result['warnings'].append(f"Record {i}: Negative {field}")
                except (ValueError, TypeError):
                    validation_result['errors'].append(f"Record {i}: Invalid {field} data type")
                    validation_result['is_valid'] = False
        
        # Validate implied volatility
        if 'implied_volatility' in record:
            try:
                iv = float(record['implied_volatility'])
                if iv < 0:
                    validation_result['warnings'].append(f"Record {i}: Negative implied volatility")
                elif iv > 5.0:  # 500%
                    validation_result['warnings'].append(f"Record {i}: Very high implied volatility")
            except (ValueError, TypeError):
                validation_result['errors'].append(f"Record {i}: Invalid implied volatility data type")
                validation_result['is_valid'] = False
        
        # Validate Greeks (if present)
        greeks = ['delta', 'gamma', 'theta', 'vega', 'rho']
        for greek in greeks:
            if greek in record and record[greek] is not None:
                try:
                    value = float(record[greek])
                    # Basic range checks for Greeks
                    if greek == 'delta' and not -1 <= value <= 1:
                        validation_result['warnings'].append(f"Record {i}: Delta out of expected range [-1, 1]")
                    elif greek == 'gamma' and value < 0:
                        validation_result['warnings'].append(f"Record {i}: Gamma should be non-negative")
                except (ValueError, TypeError):
                    validation_result['errors'].append(f"Record {i}: Invalid {greek} data type")
                    validation_result['is_valid'] = False
    
    return validation_result


def normalize_options_data(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize options data to standard format
    
    Args:
        data: List of option records
        
    Returns:
        List of normalized option records
    """
    normalized_data = []
    
    for record in data:
        normalized_record = {}
        
        # Copy required fields
        for field in REQUIRED_OPTIONS_COLUMNS:
            if field in record:
                if field == 'option_type':
                    # Normalize option type
                    normalized_record[field] = record[field].lower()
                elif field == 'expiration':
                    # Ensure expiration is in ISO format
                    if isinstance(record[field], str):
                        normalized_record[field] = record[field]
                    elif isinstance(record[field], datetime):
                        normalized_record[field] = record[field].isoformat()
                elif field in ['bid', 'ask', 'last', 'strike', 'implied_volatility']:
                    # Ensure prices and IV are floats
                    normalized_record[field] = float(record[field])
                elif field in ['volume', 'open_interest']:
                    # Ensure volume and OI are ints
                    normalized_record[field] = int(record[field])
                else:
                    normalized_record[field] = record[field]
        
        # Copy optional fields if present
        for field in OPTIONAL_OPTIONS_COLUMNS:
            if field in record and record[field] is not None:
                if field == 'timestamp':
                    if isinstance(record[field], str):
                        normalized_record[field] = record[field]
                    elif isinstance(record[field], datetime):
                        normalized_record[field] = record[field].isoformat()
                elif field in ['delta', 'gamma', 'theta', 'vega', 'rho', 'underlying_price']:
                    normalized_record[field] = float(record[field])
                elif field == 'days_to_expiration':
                    normalized_record[field] = int(record[field])
                else:
                    normalized_record[field] = record[field]
        
        # Add timestamp if not present
        if 'timestamp' not in normalized_record:
            normalized_record['timestamp'] = datetime.now().isoformat()
        
        normalized_data.append(normalized_record)
    
    return normalized_data


def calculate_moneyness(strike: float, underlying_price: float, option_type: str) -> str:
    """
    Calculate option moneyness
    
    Args:
        strike: Strike price
        underlying_price: Current underlying price
        option_type: 'call' or 'put'
        
    Returns:
        Moneyness string ('ITM', 'ATM', 'OTM')
    """
    if abs(strike - underlying_price) < 0.01:  # Very close to ATM
        return Moneyness.ATM.value
    
    if option_type.lower() == 'call':
        if underlying_price > strike:
            return Moneyness.ITM.value
        else:
            return Moneyness.OTM.value
    else:  # put
        if underlying_price < strike:
            return Moneyness.ITM.value
        else:
            return Moneyness.OTM.value


def calculate_days_to_expiration(expiration_date: datetime) -> int:
    """Calculate days to expiration from current date"""
    if isinstance(expiration_date, str):
        expiration_date = datetime.fromisoformat(expiration_date.replace('Z', '+00:00'))
    
    days = (expiration_date - datetime.now()).days
    return max(0, days)  # Don't return negative days


def enrich_options_data(data: List[Dict[str, Any]], underlying_price: Optional[float] = None) -> List[Dict[str, Any]]:
    """
    Enrich options data with calculated fields
    
    Args:
        data: List of option records
        underlying_price: Current underlying price (if available)
        
    Returns:
        List of enriched option records
    """
    enriched_data = []
    
    for record in data.copy():
        # Calculate days to expiration
        if 'expiration' in record:
            expiration_date = record['expiration']
            if isinstance(expiration_date, str):
                expiration_date = datetime.fromisoformat(expiration_date.replace('Z', '+00:00'))
            record['days_to_expiration'] = calculate_days_to_expiration(expiration_date)
        
        # Calculate moneyness if underlying price is available
        if underlying_price and 'strike' in record and 'option_type' in record:
            record['moneyness'] = calculate_moneyness(
                record['strike'], 
                underlying_price, 
                record['option_type']
            )
            record['underlying_price'] = underlying_price
        
        # Calculate mid price
        if 'bid' in record and 'ask' in record:
            record['mid'] = (record['bid'] + record['ask']) / 2
        
        # Calculate spread
        if 'bid' in record and 'ask' in record:
            record['spread'] = record['ask'] - record['bid']
            record['spread_pct'] = (record['spread'] / record['ask']) * 100 if record['ask'] > 0 else 0
        
        enriched_data.append(record)
    
    return enriched_data


def create_options_dataframe(data: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Create a pandas DataFrame from options data with proper schema
    
    Args:
        data: List of option records
        
    Returns:
        pandas DataFrame with options data
    """
    if not data:
        # Return empty DataFrame with schema
        df = pd.DataFrame(columns=list(OPTIONS_SCHEMA.keys()))
        return df.astype({k: v for k, v in OPTIONS_SCHEMA.items() if k in df.columns})
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Convert timestamp columns
    for col in ['timestamp', 'expiration']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])
    
    # Apply schema
    for column, dtype in OPTIONS_SCHEMA.items():
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


def calculate_options_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate metrics from options data
    
    Args:
        df: DataFrame with options data
        
    Returns:
        Dict containing calculated metrics
    """
    if df.empty:
        return {}
    
    metrics = {}
    
    try:
        # Basic statistics
        metrics['record_count'] = len(df)
        metrics['unique_strikes'] = len(df['strike'].unique()) if 'strike' in df.columns else 0
        metrics['unique_expirations'] = len(df['expiration'].unique()) if 'expiration' in df.columns else 0
        
        # Option type distribution
        if 'option_type' in df.columns:
            type_counts = df['option_type'].value_counts().to_dict()
            metrics['option_type_distribution'] = type_counts
        
        # Volume and open interest
        if 'volume' in df.columns:
            metrics['volume'] = {
                'total': int(df['volume'].sum()),
                'average': float(df['volume'].mean()),
                'max': int(df['volume'].max()),
                'min': int(df['volume'].min())
            }
        
        if 'open_interest' in df.columns:
            metrics['open_interest'] = {
                'total': int(df['open_interest'].sum()),
                'average': float(df['open_interest'].mean()),
                'max': int(df['open_interest'].max()),
                'min': int(df['open_interest'].min())
            }
        
        # Implied volatility statistics
        if 'implied_volatility' in df.columns:
            iv_data = df['implied_volatility'].dropna()
            if not iv_data.empty:
                metrics['implied_volatility'] = {
                    'mean': float(iv_data.mean()),
                    'median': float(iv_data.median()),
                    'std': float(iv_data.std()),
                    'min': float(iv_data.min()),
                    'max': float(iv_data.max())
                }
        
        # Moneyness distribution
        if 'moneyness' in df.columns:
            moneyness_counts = df['moneyness'].value_counts().to_dict()
            metrics['moneyness_distribution'] = moneyness_counts
        
        # Put/Call ratio
        if 'option_type' in df.columns and 'volume' in df.columns:
            call_volume = df[df['option_type'] == 'call']['volume'].sum()
            put_volume = df[df['option_type'] == 'put']['volume'].sum()
            if call_volume > 0:
                metrics['put_call_ratio'] = float(put_volume / call_volume)
        
        # Days to expiration distribution
        if 'days_to_expiration' in df.columns:
            dte_data = df['days_to_expiration'].dropna()
            if not dte_data.empty:
                metrics['days_to_expiration'] = {
                    'mean': float(dte_data.mean()),
                    'median': float(dte_data.median()),
                    'min': int(dte_data.min()),
                    'max': int(dte_data.max())
                }
        
    except Exception as e:
        metrics['calculation_error'] = str(e)
    
    return metrics


# Example usage
def example_options_usage():
    """Example usage of options schema functions"""
    
    # Sample options data
    sample_data = [
        {
            'symbol': 'AAPL240119C00150000',
            'underlying_symbol': 'AAPL',
            'option_type': 'call',
            'strike': 150.0,
            'expiration': '2024-01-19T16:00:00',
            'bid': 2.50,
            'ask': 2.65,
            'last': 2.55,
            'volume': 1500,
            'open_interest': 5000,
            'implied_volatility': 0.25,
            'delta': 0.52
        },
        {
            'symbol': 'AAPL240119P00150000',
            'underlying_symbol': 'AAPL',
            'option_type': 'put',
            'strike': 150.0,
            'expiration': '2024-01-19T16:00:00',
            'bid': 2.20,
            'ask': 2.35,
            'last': 2.25,
            'volume': 800,
            'open_interest': 3000,
            'implied_volatility': 0.23,
            'delta': -0.48
        }
    ]
    
    # Validate data
    validation_result = validate_options_data(sample_data)
    print(f"Validation result: {validation_result}")
    
    # Normalize data
    normalized_data = normalize_options_data(sample_data)
    print(f"Normalized {len(normalized_data)} records")
    
    # Enrich data
    enriched_data = enrich_options_data(normalized_data, underlying_price=152.5)
    print(f"Enriched data with moneyness: {enriched_data[0].get('moneyness')}")
    
    # Create DataFrame
    df = create_options_dataframe(enriched_data)
    print(f"Created DataFrame with shape: {df.shape}")
    
    # Calculate metrics
    metrics = calculate_options_metrics(df)
    print(f"Calculated metrics: {metrics}")


if __name__ == "__main__":
    example_options_usage()
