"""Unit tests for futures translator functionality."""

import pytest
from datetime import date, datetime
from unittest.mock import patch
from app.utils.futures import (
    translate_root_to_front_month,
    _third_friday,
    _nearest_quarterly_contract,
    _MONTH_CODES
)


class TestThirdFriday:
    """Test third Friday calculation."""
    
    def test_third_friday_march_2025(self):
        """March 2025: third Friday should be March 21."""
        result = _third_friday(2025, 3)
        expected = date(2025, 3, 21)
        assert result == expected
    
    def test_third_friday_june_2025(self):
        """June 2025: third Friday should be June 20."""
        result = _third_friday(2025, 6)
        expected = date(2025, 6, 20)
        assert result == expected
    
    def test_third_friday_september_2025(self):
        """September 2025: third Friday should be September 19."""
        result = _third_friday(2025, 9)
        expected = date(2025, 9, 19)
        assert result == expected
    
    def test_third_friday_december_2025(self):
        """December 2025: third Friday should be December 19."""
        result = _third_friday(2025, 12)
        expected = date(2025, 12, 19)
        assert result == expected
    
    def test_third_friday_february_2024(self):
        """February 2024: third Friday should be February 16."""
        result = _third_friday(2024, 2)
        expected = date(2024, 2, 16)
        assert result == expected


class TestNearestQuarterlyContract:
    """Test nearest quarterly contract selection."""
    
    def test_es_early_march(self):
        """Early March should pick March contract if not expired."""
        with patch('app.utils.futures.datetime') as mock_dt:
            mock_dt.utcnow.return_value.date.return_value = date(2025, 3, 1)
            result = _nearest_quarterly_contract('ES')
            assert result == 'ESH25'  # March
    
    def test_es_late_march(self):
        """Late March (after expiry) should pick June contract."""
        with patch('app.utils.futures.datetime') as mock_dt:
            mock_dt.utcnow.return_value.date.return_value = date(2025, 3, 22)
            result = _nearest_quarterly_contract('ES')
            assert result == 'ESM25'  # June
    
    def test_nq_august(self):
        """August should pick September contract."""
        with patch('app.utils.futures.datetime') as mock_dt:
            mock_dt.utcnow.return_value.date.return_value = date(2025, 8, 15)
            result = _nearest_quarterly_contract('NQ')
            assert result == 'NQU25'  # September
    
    def test_year_rollover(self):
        """December (after expiry) should roll to next year's March."""
        with patch('app.utils.futures.datetime') as mock_dt:
            mock_dt.utcnow.return_value.date.return_value = date(2025, 12, 25)
            result = _nearest_quarterly_contract('ES')
            assert result == 'ESH26'  # March 2026
    
    def test_january_picks_march(self):
        """January should pick March of same year."""
        with patch('app.utils.futures.datetime') as mock_dt:
            mock_dt.utcnow.return_value.date.return_value = date(2025, 1, 15)
            result = _nearest_quarterly_contract('NQ')
            assert result == 'NQH25'  # March 2025


class TestTranslateRootToFrontMonth:
    """Test the main translation function."""
    
    def test_es_translation(self):
        """ES should be translated to front-month contract."""
        with patch('app.utils.futures.datetime') as mock_dt:
            mock_dt.utcnow.return_value.date.return_value = date(2025, 8, 15)
            result = translate_root_to_front_month('ES')
            assert result == 'ESU25'  # September 2025
    
    def test_nq_translation(self):
        """NQ should be translated to front-month contract."""
        with patch('app.utils.futures.datetime') as mock_dt:
            mock_dt.utcnow.return_value.date.return_value = date(2025, 8, 15)
            result = translate_root_to_front_month('NQ')
            assert result == 'NQU25'  # September 2025
    
    def test_case_insensitive(self):
        """Translation should work with lowercase input."""
        with patch('app.utils.futures.datetime') as mock_dt:
            mock_dt.utcnow.return_value.date.return_value = date(2025, 8, 15)
            result = translate_root_to_front_month('es')
            assert result == 'ESU25'
    
    def test_non_futures_passthrough(self):
        """Non-futures symbols should pass through unchanged."""
        assert translate_root_to_front_month('SPY') == 'SPY'
        assert translate_root_to_front_month('AAPL') == 'AAPL'
        assert translate_root_to_front_month('QQQ') == 'QQQ'
    
    def test_empty_string(self):
        """Empty string should return unchanged."""
        assert translate_root_to_front_month('') == ''
    
    def test_numeric_input(self):
        """Numeric input should return unchanged."""
        assert translate_root_to_front_month('123') == '123'
    
    def test_fallback_on_exception(self):
        """Should fall back to simple heuristic if calculation fails."""
        with patch('app.utils.futures._nearest_quarterly_contract') as mock_calc:
            mock_calc.side_effect = Exception("Test error")
            with patch('app.utils.futures.datetime') as mock_dt:
                mock_dt.utcnow.return_value.year = 2025
                mock_dt.utcnow.return_value.month = 8
                result = translate_root_to_front_month('ES')
                # Fallback should pick September (next quarter >= August)
                assert result == 'ESU25'


class TestMonthCodes:
    """Test month code mapping."""
    
    def test_all_month_codes_present(self):
        """All 12 months should have codes."""
        assert len(_MONTH_CODES) == 12
        for month in range(1, 13):
            assert month in _MONTH_CODES
    
    def test_quarterly_months(self):
        """Quarterly months should have expected codes."""
        assert _MONTH_CODES[3] == 'H'   # March
        assert _MONTH_CODES[6] == 'M'   # June
        assert _MONTH_CODES[9] == 'U'   # September
        assert _MONTH_CODES[12] == 'Z'  # December


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_leap_year_february(self):
        """Leap year shouldn't affect third Friday calculation."""
        # 2024 is a leap year
        result = _third_friday(2024, 2)
        expected = date(2024, 2, 16)
        assert result == expected
    
    def test_month_boundary(self):
        """Test behavior at month boundaries."""
        # Test last day of month
        with patch('app.utils.futures.datetime') as mock_dt:
            mock_dt.utcnow.return_value.date.return_value = date(2025, 2, 28)
            result = translate_root_to_front_month('ES')
            assert result.startswith('ES')
    
    def test_year_boundary(self):
        """Test behavior at year boundaries."""
        with patch('app.utils.futures.datetime') as mock_dt:
            mock_dt.utcnow.return_value.date.return_value = date(2025, 12, 31)
            result = translate_root_to_front_month('NQ')
            # Should roll to next year
            assert '26' in result  # 2026
    
    def test_multiple_symbols(self):
        """Test translating multiple symbols."""
        with patch('app.utils.futures.datetime') as mock_dt:
            mock_dt.utcnow.return_value.date.return_value = date(2025, 8, 15)
            
            symbols = ['ES', 'NQ', 'SPY', 'AAPL']
            results = [translate_root_to_front_month(s) for s in symbols]
            
            assert results[0] == 'ESU25'  # ES -> front month
            assert results[1] == 'NQU25'  # NQ -> front month
            assert results[2] == 'SPY'    # SPY unchanged
            assert results[3] == 'AAPL'   # AAPL unchanged


if __name__ == '__main__':
    pytest.main([__file__])
