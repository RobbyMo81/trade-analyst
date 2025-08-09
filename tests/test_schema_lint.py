"""Test schema linting and validation"""

import pytest
import json
import pandas as pd
from datetime import datetime, date
from app.schemas.quotes import (
    validate_quote_data,
    normalize_quote_data,
    create_quotes_dataframe,
    calculate_quote_metrics
)
from app.schemas.ohlc import (
    validate_ohlc_data,
    normalize_ohlc_data,
    create_ohlc_dataframe,
    calculate_ohlc_metrics
)
from app.schemas.options import (
    validate_options_data,
    normalize_options_data,
    create_options_dataframe,
    calculate_options_metrics
)
from app.schemas.timesales import (
    validate_timesales_data,
    normalize_timesales_data,
    create_timesales_dataframe,
    calculate_timesales_metrics
)


class TestQuoteSchema:
    """Test quote schema functionality"""
    
    def setup_method(self):
        """Setup test data"""
        self.valid_quote_data = [
            {
                'symbol': 'AAPL',
                'bid': 150.25,
                'ask': 150.30,
                'bid_size': 1000,
                'ask_size': 800,
                'timestamp': '2024-01-01T10:00:00'
            },
            {
                'symbol': 'MSFT',
                'bid': 300.50,
                'ask': 300.55,
                'bid_size': 500,
                'ask_size': 600,
                'timestamp': '2024-01-01T10:00:01'
            }
        ]
        
        self.invalid_quote_data = [
            {
                'symbol': '',  # Invalid symbol
                'bid': -1,     # Invalid price
                'ask': 150.30,
                'timestamp': 'invalid_date'  # Invalid timestamp
            }
        ]
    
    def test_validate_valid_quotes(self):
        """Test validation of valid quote data"""
        result = validate_quote_data(self.valid_quote_data)
        assert result['is_valid'] is True
        assert result['record_count'] == 2
        assert len(result['errors']) == 0
    
    def test_validate_invalid_quotes(self):
        """Test validation of invalid quote data"""
        result = validate_quote_data(self.invalid_quote_data)
        assert result['is_valid'] is False
        assert len(result['errors']) > 0
    
    def test_normalize_quotes(self):
        """Test quote data normalization"""
        normalized = normalize_quote_data(self.valid_quote_data)
        assert len(normalized) == len(self.valid_quote_data)
        
        # Check that all required fields are present
        for quote in normalized:
            assert 'symbol' in quote
            assert 'bid' in quote
            assert 'ask' in quote
            assert 'timestamp' in quote
    
    def test_create_quotes_dataframe(self):
        """Test creating DataFrame from quote data"""
        df = create_quotes_dataframe(self.valid_quote_data)
        assert not df.empty
        assert len(df) == 2
        assert 'symbol' in df.columns
        assert 'bid' in df.columns
        assert 'ask' in df.columns
    
    def test_calculate_quote_metrics(self):
        """Test quote metrics calculation"""
        df = create_quotes_dataframe(self.valid_quote_data)
        metrics = calculate_quote_metrics(df)
        
        assert 'record_count' in metrics
        assert 'unique_symbols' in metrics
        assert metrics['record_count'] == 2


class TestOHLCSchema:
    """Test OHLC schema functionality"""
    
    def setup_method(self):
        """Setup test data"""
        self.valid_ohlc_data = [
            {
                'symbol': 'AAPL',
                'open': 150.00,
                'high': 152.50,
                'low': 149.50,
                'close': 151.25,
                'volume': 1000000,
                'timestamp': '2024-01-01T16:00:00'
            }
        ]
        
        self.invalid_ohlc_data = [
            {
                'symbol': 'AAPL',
                'open': 150.00,
                'high': 148.00,  # High less than open
                'low': 153.00,   # Low greater than open
                'close': 151.25,
                'volume': -1000,  # Negative volume
                'timestamp': '2024-01-01T16:00:00'
            }
        ]
    
    def test_validate_valid_ohlc(self):
        """Test validation of valid OHLC data"""
        result = validate_ohlc_data(self.valid_ohlc_data)
        assert result['is_valid'] is True
    
    def test_validate_invalid_ohlc(self):
        """Test validation of invalid OHLC data"""
        result = validate_ohlc_data(self.invalid_ohlc_data)
        assert result['is_valid'] is False
        assert len(result['errors']) > 0
    
    def test_normalize_ohlc(self):
        """Test OHLC data normalization"""
        normalized = normalize_ohlc_data(self.valid_ohlc_data)
        assert len(normalized) == 1
        
        ohlc = normalized[0]
        assert all(isinstance(ohlc[field], float) for field in ['open', 'high', 'low', 'close'])
    
    def test_create_ohlc_dataframe(self):
        """Test creating DataFrame from OHLC data"""
        df = create_ohlc_dataframe(self.valid_ohlc_data)
        assert not df.empty
        assert 'symbol' in df.columns
        assert all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume'])
    
    def test_calculate_ohlc_metrics(self):
        """Test OHLC metrics calculation"""
        df = create_ohlc_dataframe(self.valid_ohlc_data)
        metrics = calculate_ohlc_metrics(df)
        
        assert 'record_count' in metrics
        assert 'price_range' in metrics


class TestOptionsSchema:
    """Test options schema functionality"""
    
    def setup_method(self):
        """Setup test data"""
        self.valid_options_data = [
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
                'implied_volatility': 0.25
            }
        ]
        
        self.invalid_options_data = [
            {
                'symbol': 'INVALID',
                'underlying_symbol': 'AAPL',
                'option_type': 'invalid_type',  # Invalid option type
                'strike': -150.0,  # Negative strike
                'bid': 2.65,  # Bid higher than ask
                'ask': 2.50,
                'implied_volatility': -0.1  # Negative IV
            }
        ]
    
    def test_validate_valid_options(self):
        """Test validation of valid options data"""
        result = validate_options_data(self.valid_options_data)
        assert result['is_valid'] is True
    
    def test_validate_invalid_options(self):
        """Test validation of invalid options data"""
        result = validate_options_data(self.invalid_options_data)
        assert result['is_valid'] is False
        assert len(result['errors']) > 0
    
    def test_normalize_options(self):
        """Test options data normalization"""
        normalized = normalize_options_data(self.valid_options_data)
        assert len(normalized) == 1
        
        option = normalized[0]
        assert option['option_type'] in ['call', 'put']
        assert isinstance(option['strike'], float)
    
    def test_create_options_dataframe(self):
        """Test creating DataFrame from options data"""
        df = create_options_dataframe(self.valid_options_data)
        assert not df.empty
        assert 'symbol' in df.columns
        assert 'underlying_symbol' in df.columns
        assert 'option_type' in df.columns
    
    def test_calculate_options_metrics(self):
        """Test options metrics calculation"""
        df = create_options_dataframe(self.valid_options_data)
        metrics = calculate_options_metrics(df)
        
        assert 'record_count' in metrics
        assert 'unique_strikes' in metrics


class TestTimeSalesSchema:
    """Test time and sales schema functionality"""
    
    def setup_method(self):
        """Setup test data"""
        self.valid_timesales_data = [
            {
                'symbol': 'AAPL',
                'timestamp': '2024-01-01T10:00:00',
                'price': 150.25,
                'size': 100,
                'exchange': 'NASDAQ',
                'side': 'buy',
                'conditions': ['R']
            }
        ]
        
        self.invalid_timesales_data = [
            {
                'symbol': '',  # Empty symbol
                'price': -150.25,  # Negative price
                'size': 0,  # Zero size
                'exchange': 'INVALID',  # Invalid exchange
                'timestamp': 'invalid'  # Invalid timestamp
            }
        ]
    
    def test_validate_valid_timesales(self):
        """Test validation of valid time and sales data"""
        result = validate_timesales_data(self.valid_timesales_data)
        assert result['is_valid'] is True
    
    def test_validate_invalid_timesales(self):
        """Test validation of invalid time and sales data"""
        result = validate_timesales_data(self.invalid_timesales_data)
        assert result['is_valid'] is False
        assert len(result['errors']) > 0
    
    def test_normalize_timesales(self):
        """Test time and sales data normalization"""
        normalized = normalize_timesales_data(self.valid_timesales_data)
        assert len(normalized) == 1
        
        trade = normalized[0]
        assert isinstance(trade['price'], float)
        assert isinstance(trade['size'], int)
    
    def test_create_timesales_dataframe(self):
        """Test creating DataFrame from time and sales data"""
        df = create_timesales_dataframe(self.valid_timesales_data)
        assert not df.empty
        assert 'symbol' in df.columns
        assert 'price' in df.columns
        assert 'size' in df.columns
    
    def test_calculate_timesales_metrics(self):
        """Test time and sales metrics calculation"""
        df = create_timesales_dataframe(self.valid_timesales_data)
        metrics = calculate_timesales_metrics(df)
        
        assert 'record_count' in metrics
        assert 'volume' in metrics


class TestSchemaConsistency:
    """Test consistency across schemas"""
    
    def test_empty_data_handling(self):
        """Test all schemas handle empty data gracefully"""
        schemas = [
            (validate_quote_data, create_quotes_dataframe),
            (validate_ohlc_data, create_ohlc_dataframe),
            (validate_options_data, create_options_dataframe),
            (validate_timesales_data, create_timesales_dataframe)
        ]
        
        for validate_func, create_df_func in schemas:
            # Test empty list
            result = validate_func([])
            assert result['is_valid'] is False
            
            # Test empty DataFrame creation
            df = create_df_func([])
            assert df.empty
    
    def test_timestamp_formats(self):
        """Test timestamp format consistency"""
        timestamp_formats = [
            '2024-01-01T10:00:00',
            '2024-01-01T10:00:00Z',
            '2024-01-01T10:00:00+00:00'
        ]
        
        for ts_format in timestamp_formats:
            quote_data = [{
                'symbol': 'AAPL',
                'bid': 150.0,
                'ask': 150.5,
                'timestamp': ts_format
            }]
            
            result = validate_quote_data(quote_data)
            # Should not fail on valid timestamp formats
            assert 'timestamp' not in str(result.get('errors', []))
    
    def test_numeric_type_handling(self):
        """Test numeric type handling consistency"""
        # Test with integers and floats
        numeric_values = [100, 100.0, 100.5]
        
        for price in numeric_values:
            quote_data = [{
                'symbol': 'AAPL',
                'bid': price,
                'ask': price + 0.5,
                'timestamp': '2024-01-01T10:00:00'
            }]
            
            normalized = normalize_quote_data(quote_data)
            assert isinstance(normalized[0]['bid'], (int, float))


class TestPerformance:
    """Test schema performance with larger datasets"""
    
    def test_large_dataset_validation(self):
        """Test validation performance with larger datasets"""
        # Create 1000 quote records
        large_dataset = []
        for i in range(1000):
            large_dataset.append({
                'symbol': f'SYM{i:03d}',
                'bid': 100.0 + i * 0.01,
                'ask': 100.05 + i * 0.01,
                'timestamp': f'2024-01-01T{i % 24:02d}:00:00'
            })
        
        result = validate_quote_data(large_dataset)
        assert result['record_count'] == 1000
        
        # Should complete in reasonable time
        df = create_quotes_dataframe(large_dataset)
        assert len(df) == 1000
    
    def test_dataframe_memory_usage(self):
        """Test DataFrame memory efficiency"""
        # Create dataset and check memory usage
        data = []
        for i in range(100):
            data.append({
                'symbol': 'AAPL',
                'bid': 150.0,
                'ask': 150.5,
                'timestamp': '2024-01-01T10:00:00'
            })
        
        df = create_quotes_dataframe(data)
        memory_usage = df.memory_usage(deep=True).sum()
        
        # Should be reasonable memory usage (less than 1MB for 100 records)
        assert memory_usage < 1024 * 1024


if __name__ == "__main__":
    pytest.main([__file__])
