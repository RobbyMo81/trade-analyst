"""Test validators module functionality"""

import pytest
from datetime import datetime, date
from app.utils.validators import (
    ValidationResult,
    ValidationError,
    SchemaValidator,
    validate_symbol,
    validate_price,
    validate_volume,
    validate_timestamp,
    validate_exchange,
    validate_option_symbol,
    validate_strike_price,
    validate_implied_volatility,
    validate_greeks,
    validate_ohlc_consistency,
    validate_bid_ask_spread,
    validate_trade_conditions,
    QUOTE_SCHEMA,
    OHLC_SCHEMA,
    TIMESALES_SCHEMA
)


class TestValidationResult:
    """Test ValidationResult class"""
    
    def test_initialization(self):
        """Test ValidationResult initialization"""
        result = ValidationResult()
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.field_errors == {}
    
    def test_add_error(self):
        """Test adding errors"""
        result = ValidationResult()
        result.add_error("Test error", "test_field")
        
        assert result.is_valid is False
        assert "Test error" in result.errors
        assert "test_field" in result.field_errors
        assert "Test error" in result.field_errors["test_field"]
    
    def test_add_warning(self):
        """Test adding warnings"""
        result = ValidationResult()
        result.add_warning("Test warning", "test_field")
        
        assert result.is_valid is True  # Warnings don't make invalid
        assert "Test warning" in result.warnings
        assert "test_field" in result.field_errors
    
    def test_to_dict(self):
        """Test converting to dictionary"""
        result = ValidationResult()
        result.add_error("Error message")
        result.add_warning("Warning message")
        
        result_dict = result.to_dict()
        assert "is_valid" in result_dict
        assert "errors" in result_dict
        assert "warnings" in result_dict
        assert "field_errors" in result_dict


class TestSymbolValidation:
    """Test symbol validation functions"""
    
    def test_valid_symbols(self):
        """Test valid stock symbols"""
        valid_symbols = ["AAPL", "MSFT", "GOOGL", "BRK.A", "SPY"]
        for symbol in valid_symbols:
            assert validate_symbol(symbol) is True
    
    def test_invalid_symbols(self):
        """Test invalid stock symbols"""
        invalid_symbols = ["", "12345", "toolong", "lower", "INVALID.LONG"]
        for symbol in invalid_symbols:
            assert validate_symbol(symbol) is False
    
    def test_option_symbols(self):
        """Test option symbol validation"""
        valid_options = ["AAPL240119C00150000", "SPY240315P00400000"]
        invalid_options = ["AAPL", "AAPL240119", "INVALID"]
        
        for symbol in valid_options:
            assert validate_option_symbol(symbol) is True
        
        for symbol in invalid_options:
            assert validate_option_symbol(symbol) is False


class TestPriceValidation:
    """Test price validation functions"""
    
    def test_valid_prices(self):
        """Test valid price values"""
        valid_prices = [100.0, 50.25, 1.0, 0.01]
        for price in valid_prices:
            assert validate_price(price) is True
    
    def test_invalid_prices(self):
        """Test invalid price values"""
        invalid_prices = [-1, 0, "not_a_number", None]
        for price in invalid_prices:
            assert validate_price(price) is False
    
    def test_price_ranges(self):
        """Test price range validation"""
        assert validate_price(50, min_price=10, max_price=100) is True
        assert validate_price(5, min_price=10, max_price=100) is False
        assert validate_price(150, min_price=10, max_price=100) is False


class TestVolumeValidation:
    """Test volume validation functions"""
    
    def test_valid_volumes(self):
        """Test valid volume values"""
        valid_volumes = [100, 1000, 1, 500.0]
        for volume in valid_volumes:
            assert validate_volume(volume) is True
    
    def test_invalid_volumes(self):
        """Test invalid volume values"""
        invalid_volumes = [-1, "not_a_number", None]
        for volume in invalid_volumes:
            assert validate_volume(volume) is False


class TestTimestampValidation:
    """Test timestamp validation functions"""
    
    def test_valid_timestamps(self):
        """Test valid timestamp formats"""
        valid_timestamps = [
            "2024-01-01T10:00:00",
            "2024-01-01T10:00:00Z",
            "2024-01-01T10:00:00+00:00",
            datetime.now()
        ]
        for timestamp in valid_timestamps:
            assert validate_timestamp(timestamp) is True
    
    def test_invalid_timestamps(self):
        """Test invalid timestamp formats"""
        invalid_timestamps = ["not_a_date", 12345, None]
        for timestamp in invalid_timestamps:
            assert validate_timestamp(timestamp) is False
    
    def test_future_timestamps(self):
        """Test future timestamp validation"""
        future_time = datetime.now().replace(year=2030)
        assert validate_timestamp(future_time, allow_future=True) is True
        assert validate_timestamp(future_time, allow_future=False) is False


class TestExchangeValidation:
    """Test exchange validation"""
    
    def test_valid_exchanges(self):
        """Test valid exchange codes"""
        valid_exchanges = ["NYSE", "NASDAQ", "ARCA", "BATS", "IEX"]
        for exchange in valid_exchanges:
            assert validate_exchange(exchange) is True
    
    def test_invalid_exchanges(self):
        """Test invalid exchange codes"""
        invalid_exchanges = ["INVALID", "", 123, None]
        for exchange in invalid_exchanges:
            assert validate_exchange(exchange) is False


class TestStrikePriceValidation:
    """Test strike price validation"""
    
    def test_valid_strikes(self):
        """Test valid strike prices"""
        assert validate_strike_price(100.0) is True
        assert validate_strike_price(50.0, underlying_price=100.0) is True
    
    def test_invalid_strikes(self):
        """Test invalid strike prices"""
        assert validate_strike_price(0) is False
        assert validate_strike_price(-10) is False
        assert validate_strike_price("not_a_number") is False
    
    def test_strike_ratio(self):
        """Test strike price ratio validation"""
        # Very far OTM should fail with default ratio
        assert validate_strike_price(1000.0, underlying_price=100.0, max_ratio=5.0) is False
        assert validate_strike_price(1000.0, underlying_price=100.0, max_ratio=20.0) is True


class TestImpliedVolatilityValidation:
    """Test implied volatility validation"""
    
    def test_valid_iv(self):
        """Test valid IV values"""
        valid_ivs = [0.25, 0.5, 1.0, 0.01]
        for iv in valid_ivs:
            assert validate_implied_volatility(iv) is True
    
    def test_invalid_iv(self):
        """Test invalid IV values"""
        invalid_ivs = [-0.1, 15.0, "not_a_number", None]
        for iv in invalid_ivs:
            assert validate_implied_volatility(iv) is False


class TestGreeksValidation:
    """Test Greeks validation"""
    
    def test_valid_greeks(self):
        """Test valid Greeks"""
        greeks = {
            'delta': 0.5,
            'gamma': 0.1,
            'theta': -0.05,
            'vega': 0.2,
            'rho': 0.1
        }
        results = validate_greeks(greeks)
        assert all(results.values())
    
    def test_invalid_greeks(self):
        """Test invalid Greeks"""
        invalid_greeks = {
            'delta': 2.0,  # Outside [-1, 1]
            'gamma': -0.1,  # Negative gamma
            'theta': 200,   # Outside reasonable range
            'vega': -0.1,   # Negative vega
            'rho': 200      # Outside reasonable range
        }
        results = validate_greeks(invalid_greeks)
        assert not all(results.values())


class TestOHLCConsistency:
    """Test OHLC consistency validation"""
    
    def test_valid_ohlc(self):
        """Test valid OHLC data"""
        errors = validate_ohlc_consistency(100.0, 105.0, 95.0, 102.0)
        assert len(errors) == 0
    
    def test_invalid_ohlc(self):
        """Test invalid OHLC data"""
        # High less than open
        errors = validate_ohlc_consistency(100.0, 95.0, 90.0, 98.0)
        assert len(errors) > 0
        
        # Low greater than close
        errors = validate_ohlc_consistency(100.0, 105.0, 103.0, 102.0)
        assert len(errors) > 0


class TestBidAskSpread:
    """Test bid/ask spread validation"""
    
    def test_valid_spread(self):
        """Test valid bid/ask spreads"""
        errors = validate_bid_ask_spread(100.0, 100.5)
        assert len(errors) == 0
    
    def test_invalid_spread(self):
        """Test invalid bid/ask spreads"""
        # Bid higher than ask
        errors = validate_bid_ask_spread(100.5, 100.0)
        assert len(errors) > 0
        
        # Negative prices
        errors = validate_bid_ask_spread(-1.0, 100.0)
        assert len(errors) > 0


class TestTradeConditions:
    """Test trade condition validation"""
    
    def test_valid_conditions(self):
        """Test valid trade conditions"""
        valid_conditions = ['R', 'O', 'C', 'L', 'T']
        invalid = validate_trade_conditions(valid_conditions)
        assert len(invalid) == 0
    
    def test_invalid_conditions(self):
        """Test invalid trade conditions"""
        invalid_conditions = ['INVALID', 'X123', '']
        invalid = validate_trade_conditions(invalid_conditions)
        assert len(invalid) > 0


class TestSchemaValidator:
    """Test SchemaValidator class"""
    
    def test_quote_validation(self):
        """Test quote schema validation"""
        validator = SchemaValidator(QUOTE_SCHEMA)
        
        valid_quote = {
            'symbol': 'AAPL',
            'bid': 150.0,
            'ask': 150.5,
            'timestamp': '2024-01-01T10:00:00'
        }
        
        result = validator.validate_record(valid_quote)
        assert result.is_valid is True
    
    def test_missing_required_field(self):
        """Test validation with missing required field"""
        validator = SchemaValidator(QUOTE_SCHEMA)
        
        invalid_quote = {
            'symbol': 'AAPL',
            'bid': 150.0
            # Missing required 'ask' and 'timestamp'
        }
        
        result = validator.validate_record(invalid_quote)
        assert result.is_valid is False
        assert len(result.errors) > 0
    
    def test_batch_validation(self):
        """Test batch validation"""
        validator = SchemaValidator(QUOTE_SCHEMA)
        
        records = [
            {
                'symbol': 'AAPL',
                'bid': 150.0,
                'ask': 150.5,
                'timestamp': '2024-01-01T10:00:00'
            },
            {
                'symbol': 'INVALID',
                'bid': -1  # Invalid price
                # Missing required fields
            }
        ]
        
        batch_result = validator.validate_batch(records)
        assert batch_result['valid_records'] == 1
        assert batch_result['invalid_records'] == 1


if __name__ == "__main__":
    pytest.main([__file__])
