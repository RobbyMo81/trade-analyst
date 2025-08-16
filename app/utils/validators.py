"""Data validation utilities for trade analysis"""

from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime, date
import re
import logging

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom validation error"""
    pass


class ValidationResult:
    """Validation result container"""
    
    def __init__(self):
        self.is_valid = True
        self.errors = []
        self.warnings = []
        self.field_errors = {}
    
    def add_error(self, message: str, field: Optional[str] = None):
        """Add an error"""
        self.is_valid = False
        self.errors.append(message)
        if field:
            if field not in self.field_errors:
                self.field_errors[field] = []
            self.field_errors[field].append(message)
    
    def add_warning(self, message: str, field: Optional[str] = None):
        """Add a warning"""
        self.warnings.append(message)
        if field:
            if field not in self.field_errors:
                self.field_errors[field] = []
            self.field_errors[field].append(f"Warning: {message}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'is_valid': self.is_valid,
            'errors': self.errors,
            'warnings': self.warnings,
            'field_errors': self.field_errors
        }


def validate_symbol(symbol: str) -> bool:
    """
    Validate stock symbol format
    
    Args:
        symbol: Stock symbol to validate
        
    Returns:
        True if valid symbol format
    """
    if not isinstance(symbol, str):
        return False
    # Reject empty and lowercase originals (tests expect 'lower' invalid)
    if symbol == '' or symbol != symbol.upper():
        return False
    # Basic symbol pattern: 1-6 uppercase letters, optionally followed by dot and suffix
    pattern = r'^[A-Z]{1,6}(\.[A-Z]{1,3})?$'
    return bool(re.match(pattern, symbol))


def validate_price(price: Union[int, float], min_price: float = 0.0, max_price: float = 1000000.0) -> bool:
    """
    Validate price value
    
    Args:
        price: Price to validate
        min_price: Minimum allowed price
        max_price: Maximum allowed price
        
    Returns:
        True if valid price
    """
    try:
        price_val = float(price)
        # Enforce strictly > 0 (tests treat 0 as invalid) unless caller raises min_price
        if price_val <= 0:
            return False
        return min_price < price_val <= max_price
    except (ValueError, TypeError):
        return False


def validate_volume(volume: Union[int, float], min_volume: int = 0, max_volume: int = 1000000000) -> bool:
    """
    Validate volume value
    
    Args:
        volume: Volume to validate
        min_volume: Minimum allowed volume
        max_volume: Maximum allowed volume
        
    Returns:
        True if valid volume
    """
    try:
        volume_val = int(volume)
        return min_volume <= volume_val <= max_volume
    except (ValueError, TypeError):
        return False


def validate_timestamp(timestamp: Union[str, datetime], 
                      allow_future: bool = False,
                      max_age_days: Optional[int] = None) -> bool:
    """
    Validate timestamp
    
    Args:
        timestamp: Timestamp to validate
        allow_future: Whether to allow future timestamps
        max_age_days: Maximum age in days
        
    Returns:
        True if valid timestamp
    """
    try:
        if isinstance(timestamp, str):
            # Try to parse ISO format
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        elif isinstance(timestamp, datetime):
            dt = timestamp
        else:
            return False
        
        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
        
        # Check future timestamps
        if not allow_future and dt > now:
            return False
        
        # Check age
        if max_age_days is not None:
            age_days = (now - dt).days
            if age_days > max_age_days:
                return False
        
        return True
        
    except (ValueError, TypeError):
        return False


def validate_exchange(exchange: str) -> bool:
    """
    Validate exchange code
    
    Args:
        exchange: Exchange code to validate
        
    Returns:
        True if valid exchange
    """
    if not isinstance(exchange, str):
        return False
    
    valid_exchanges = {
        'NYSE', 'NASDAQ', 'ARCA', 'BATS', 'IEX', 'CBOE',
        'PSX', 'BX', 'BYX', 'EDGA', 'EDGX', 'CHX', 'NSX'
    }
    
    return exchange.upper() in valid_exchanges


def validate_option_symbol(symbol: str) -> bool:
    """
    Validate option symbol format (OCC format)
    
    Args:
        symbol: Option symbol to validate
        
    Returns:
        True if valid option symbol format
    """
    if not isinstance(symbol, str):
        return False
    
    # OCC format: ROOT + YYMMDD + C/P + 00000000 (strike * 1000)
    # Example: AAPL240119C00150000
    pattern = r'^[A-Z]{1,6}\d{6}[CP]\d{8}$'
    return bool(re.match(pattern, symbol.upper()))


def validate_strike_price(strike: Union[int, float], 
                         underlying_price: Optional[float] = None,
                         max_ratio: float = 10.0) -> bool:
    """
    Validate option strike price
    
    Args:
        strike: Strike price to validate
        underlying_price: Current underlying price
        max_ratio: Maximum strike/underlying ratio
        
    Returns:
        True if valid strike price
    """
    try:
        strike_val = float(strike)
        
        if strike_val <= 0:
            return False
        
        # Check ratio to underlying if provided
        if underlying_price is not None:
            ratio = max(strike_val / underlying_price, underlying_price / strike_val)
            if ratio > max_ratio:
                return False
        
        return True
        
    except (ValueError, TypeError):
        return False


def validate_implied_volatility(iv: Union[int, float]) -> bool:
    """
    Validate implied volatility value
    
    Args:
        iv: Implied volatility to validate
        
    Returns:
        True if valid IV
    """
    try:
        iv_val = float(iv)
        # IV should be between 0 and 10 (1000%)
        return 0 <= iv_val <= 10
    except (ValueError, TypeError):
        return False


def validate_greeks(greeks: Dict[str, Union[int, float]]) -> Dict[str, bool]:
    """
    Validate option Greeks
    
    Args:
        greeks: Dictionary of Greeks to validate
        
    Returns:
        Dict of validation results for each Greek
    """
    results = {}
    
    # Delta: -1 to 1
    if 'delta' in greeks:
        try:
            delta = float(greeks['delta'])
            results['delta'] = -1 <= delta <= 1
        except (ValueError, TypeError):
            results['delta'] = False
    
    # Gamma: 0 to positive
    if 'gamma' in greeks:
        try:
            gamma = float(greeks['gamma'])
            results['gamma'] = gamma >= 0
        except (ValueError, TypeError):
            results['gamma'] = False
    
    # Theta: typically negative for long positions
    if 'theta' in greeks:
        try:
            theta = float(greeks['theta'])
            results['theta'] = -100 <= theta <= 100  # Reasonable range
        except (ValueError, TypeError):
            results['theta'] = False
    
    # Vega: 0 to positive
    if 'vega' in greeks:
        try:
            vega = float(greeks['vega'])
            results['vega'] = vega >= 0
        except (ValueError, TypeError):
            results['vega'] = False
    
    # Rho: can be positive or negative
    if 'rho' in greeks:
        try:
            rho = float(greeks['rho'])
            results['rho'] = -100 <= rho <= 100  # Reasonable range
        except (ValueError, TypeError):
            results['rho'] = False
    
    return results


def validate_ohlc_consistency(open_price: float, high_price: float, 
                             low_price: float, close_price: float) -> List[str]:
    """
    Validate OHLC price consistency
    
    Args:
        open_price: Opening price
        high_price: High price
        low_price: Low price
        close_price: Closing price
        
    Returns:
        List of validation error messages
    """
    errors = []
    
    try:
        o, h, l, c = float(open_price), float(high_price), float(low_price), float(close_price)
        
        # High should be >= all other prices
        if h < o:
            errors.append("High price is less than open price")
        if h < l:
            errors.append("High price is less than low price")
        if h < c:
            errors.append("High price is less than close price")
        
        # Low should be <= all other prices
        if l > o:
            errors.append("Low price is greater than open price")
        if l > h:
            errors.append("Low price is greater than high price")
        if l > c:
            errors.append("Low price is greater than close price")
        
        # All prices should be positive
        if any(price <= 0 for price in [o, h, l, c]):
            errors.append("All prices must be positive")
        
    except (ValueError, TypeError):
        errors.append("Invalid price data types")
    
    return errors


def validate_bid_ask_spread(bid: float, ask: float, max_spread_pct: float = 50.0) -> List[str]:
    """
    Validate bid/ask spread
    
    Args:
        bid: Bid price
        ask: Ask price
        max_spread_pct: Maximum spread as percentage of mid price
        
    Returns:
        List of validation error messages
    """
    errors = []
    
    try:
        bid_val, ask_val = float(bid), float(ask)
        
        if bid_val <= 0 or ask_val <= 0:
            errors.append("Bid and ask prices must be positive")
            return errors
        
        if bid_val > ask_val:
            errors.append("Bid price is higher than ask price")
        
        # Check spread percentage
        mid = (bid_val + ask_val) / 2
        spread_pct = ((ask_val - bid_val) / mid) * 100
        
        if spread_pct > max_spread_pct:
            errors.append(f"Spread too wide: {spread_pct:.2f}% > {max_spread_pct}%")
        
    except (ValueError, TypeError):
        errors.append("Invalid bid/ask data types")
    
    return errors


def validate_trade_conditions(conditions: List[str]) -> List[str]:
    """
    Validate trade condition codes
    
    Args:
        conditions: List of condition codes
        
    Returns:
        List of invalid condition codes
    """
    valid_conditions = {
        'R', 'O', 'C', 'L', 'T', 'B', 'I', 'X', 'Z', 'P',
        'Q', 'W', 'N', 'M', 'F', 'U', 'H', 'K', 'Y', 'V'
    }
    
    invalid_conditions = []
    
    for condition in conditions:
        if condition not in valid_conditions:
            invalid_conditions.append(condition)
    
    return invalid_conditions


class SchemaValidator:
    """Generic schema validator"""
    
    def __init__(self, schema: Dict[str, Dict[str, Any]]):
        """
        Initialize validator with schema
        
        Args:
            schema: Field validation schema
        """
        self.schema = schema
    
    def validate_record(self, record: Dict[str, Any]) -> ValidationResult:
        """
        Validate a single record against schema
        
        Args:
            record: Record to validate
            
        Returns:
            ValidationResult
        """
        result = ValidationResult()
        
        # Check required fields
        for field_name, field_config in self.schema.items():
            if field_config.get('required', False) and field_name not in record:
                result.add_error(f"Missing required field: {field_name}", field_name)
        
        # Validate present fields
        for field_name, value in record.items():
            if field_name in self.schema:
                field_config = self.schema[field_name]
                
                # Type validation
                expected_type = field_config.get('type')
                if expected_type and not isinstance(value, expected_type):
                    result.add_error(f"Invalid type for {field_name}: expected {expected_type.__name__}", field_name)
                    continue
                
                # Custom validator
                validator = field_config.get('validator')
                if validator and callable(validator):
                    try:
                        if not validator(value):
                            result.add_error(f"Validation failed for {field_name}", field_name)
                    except Exception as e:
                        result.add_error(f"Validator error for {field_name}: {str(e)}", field_name)
                
                # Range validation
                min_val = field_config.get('min')
                max_val = field_config.get('max')
                if min_val is not None or max_val is not None:
                    try:
                        num_val = float(value)
                        if min_val is not None and num_val < min_val:
                            result.add_error(f"{field_name} below minimum: {num_val} < {min_val}", field_name)
                        if max_val is not None and num_val > max_val:
                            result.add_error(f"{field_name} above maximum: {num_val} > {max_val}", field_name)
                    except (ValueError, TypeError):
                        pass  # Type error already reported
        
        return result
    
    def validate_batch(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate a batch of records
        
        Args:
            records: List of records to validate
            
        Returns:
            Dictionary with batch validation results
        """
        batch_result = {
            'total_records': len(records),
            'valid_records': 0,
            'invalid_records': 0,
            'errors': [],
            'warnings': [],
            'record_results': []
        }
        
        for i, record in enumerate(records):
            record_result = self.validate_record(record)
            
            if record_result.is_valid:
                batch_result['valid_records'] += 1
            else:
                batch_result['invalid_records'] += 1
                batch_result['errors'].extend([f"Record {i}: {error}" for error in record_result.errors])
            
            batch_result['warnings'].extend([f"Record {i}: {warning}" for warning in record_result.warnings])
            batch_result['record_results'].append(record_result.to_dict())
        
        return batch_result

# --- Additional URI / callback hygiene helpers (module level) ---
import urllib.parse as _urllib_parse

def is_valid_redirect_format(uri: str) -> bool:
    """Basic structural validation for redirect URIs.

    Rules (hardened):
    - https is accepted when netloc and path exist
    - http is NOT accepted (tests enforce https-only hygiene)
    """
    try:
        p = _urllib_parse.urlparse(uri)
        if not (bool(p.netloc) and bool(p.path)):
            return False
        if p.scheme == "https":
            return True
        return False
    except Exception:
        return False

def exact_match(redirect: str, registered: List[str]) -> bool:  # noqa: D401
    """Return True if redirect exactly equals one of the registered URIs."""
    return redirect in set(registered)


# Example schema definitions
QUOTE_SCHEMA = {
    'symbol': {
        'type': str,
        'required': True,
        'validator': validate_symbol
    },
    'bid': {
        'type': (int, float),
        'required': True,
        'min': 0,
        'validator': lambda x: validate_price(x)
    },
    'ask': {
        'type': (int, float),
        'required': True,
        'min': 0,
        'validator': lambda x: validate_price(x)
    },
    'timestamp': {
        'type': str,
        'required': True,
        'validator': lambda x: validate_timestamp(x)
    }
}

OHLC_SCHEMA = {
    'symbol': {
        'type': str,
        'required': True,
        'validator': validate_symbol
    },
    'open': {
        'type': (int, float),
        'required': True,
        'min': 0,
        'validator': lambda x: validate_price(x)
    },
    'high': {
        'type': (int, float),
        'required': True,
        'min': 0,
        'validator': lambda x: validate_price(x)
    },
    'low': {
        'type': (int, float),
        'required': True,
        'min': 0,
        'validator': lambda x: validate_price(x)
    },
    'close': {
        'type': (int, float),
        'required': True,
        'min': 0,
        'validator': lambda x: validate_price(x)
    },
    'volume': {
        'type': int,
        'required': True,
        'min': 0,
        'validator': lambda x: validate_volume(x)
    }
}

TIMESALES_SCHEMA = {
    'symbol': {
        'type': str,
        'required': True,
        'validator': validate_symbol
    },
    'price': {
        'type': (int, float),
        'required': True,
        'min': 0,
        'validator': lambda x: validate_price(x)
    },
    'size': {
        'type': int,
        'required': True,
        'min': 1,
        'validator': lambda x: validate_volume(x)
    },
    'timestamp': {
        'type': str,
        'required': True,
        'validator': lambda x: validate_timestamp(x)
    },
    'exchange': {
        'type': str,
        'required': True,
        'validator': validate_exchange
    }
}


# Example usage
def example_validator_usage():
    """Example usage of validators"""
    
    # Create validator
    quote_validator = SchemaValidator(QUOTE_SCHEMA)
    
    # Sample data
    quote_data = {
        'symbol': 'AAPL',
        'bid': 150.25,
        'ask': 150.30,
        'timestamp': '2024-01-01T10:00:00'
    }
    
    # Validate
    result = quote_validator.validate_record(quote_data)
    print(f"Validation result: {result.to_dict()}")
    
    # Batch validation
    batch_data = [quote_data, {'symbol': 'INVALID', 'bid': -1}]
    batch_result = quote_validator.validate_batch(batch_data)
    print(f"Batch validation: {batch_result}")


if __name__ == "__main__":
    example_validator_usage()
