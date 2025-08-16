"""Integration tests demonstrating exchange calendar functionality with futures translation."""

import pytest
from datetime import date, datetime
from unittest.mock import patch

from app.utils.futures import translate_root_to_front_month, _nearest_quarterly_contract
from app.utils.exchange_calendar import (
    get_contract_expiry_date, 
    is_business_day,
    get_trading_days_until_expiry
)


class TestExchangeCalendarIntegration:
    """Test integration between futures translation and exchange calendar."""
    
    def test_futures_translation_uses_exchange_calendar(self):
        """Verify futures translation uses proper expiry dates."""
        # Mock current date to be in early 2025
        with patch('app.utils.futures.datetime') as mock_datetime:
            # Create a mock datetime object with proper date() method
            mock_dt = datetime(2025, 1, 15)
            mock_datetime.utcnow.return_value = mock_dt
            
            # Translate ES root symbol
            result = translate_root_to_front_month('ES')
            
            # Should pick March 2025 contract (ESH25)
            # because January is too early for March expiry
            assert result == 'ESH25'  # H = March, 25 = 2025
    
    def test_expiry_date_accuracy_with_holidays(self):
        """Test that expiry dates are accurate considering holidays."""
        # Get expiry date for ES March 2024 contract
        expiry_date = get_contract_expiry_date('ES', 2024, 3)
        
        # March 2024 third Friday is March 15
        expected = date(2024, 3, 15)
        assert expiry_date == expected
        
        # Verify it's a business day (not a holiday)
        assert is_business_day(expiry_date)
    
    def test_holiday_adjustment_scenario(self):
        """Test scenario where expiry date adjustment is needed."""
        # Create a mock scenario where third Friday is a holiday
        mock_holidays = {date(2024, 6, 21): "Mock Holiday"}
        
        with patch('app.utils.exchange_calendar._FEDERAL_HOLIDAYS_2024_2030', mock_holidays):
            # June 2024 - third Friday (June 21) is now a "holiday"
            expiry_date = get_contract_expiry_date('ES', 2024, 6)
            
            # Should move to prior business day (June 20, Thursday)
            expected = date(2024, 6, 20)
            assert expiry_date == expected
            assert is_business_day(expiry_date)
    
    def test_trading_days_calculation(self):
        """Test trading days calculation for contract selection."""
        # Test scenario: current date is Monday, expiry is Friday same week
        current_date = date(2024, 6, 10)  # Monday
        expiry_date = date(2024, 6, 14)    # Friday
        
        trading_days = get_trading_days_until_expiry(current_date, expiry_date)
        # Should be 4 days: Tue, Wed, Thu, Fri
        assert trading_days == 4
    
    def test_good_friday_handling(self):
        """Test that Good Friday is properly handled as non-business day."""
        # Good Friday 2024 is March 29
        good_friday = date(2024, 3, 29)
        
        # Should not be a business day
        assert not is_business_day(good_friday)
        
        # If a contract expired on Good Friday, it should move to Thursday
        # (This is a hypothetical scenario for testing)
        mock_holidays = {date(2024, 6, 21): "Good Friday"}
        
        with patch('app.utils.exchange_calendar._FEDERAL_HOLIDAYS_2024_2030', mock_holidays):
            expiry_date = get_contract_expiry_date('ES', 2024, 6)
            expected = date(2024, 6, 20)  # Thursday
            assert expiry_date == expected
    
    def test_quarter_end_expiry_logic(self):
        """Test expiry logic for quarterly contracts."""
        # Test all quarterly months
        quarterly_months = [3, 6, 9, 12]  # Mar, Jun, Sep, Dec
        
        for month in quarterly_months:
            expiry_date = get_contract_expiry_date('ES', 2024, month)
            
            # Should be third Friday of the month
            # Verify it's a Friday
            assert expiry_date.weekday() == 4  # Friday = 4
            
            # Verify it's in the correct month
            assert expiry_date.month == month
            assert expiry_date.year == 2024
    
    def test_contract_selection_logic(self):
        """Test that nearest contract selection uses accurate expiry dates."""
        # Mock date in February 2024
        with patch('app.utils.futures.datetime') as mock_datetime:
            mock_dt = datetime(2024, 2, 15)
            mock_datetime.utcnow.return_value = mock_dt
            
            # Should select March 2024 contract
            result = _nearest_quarterly_contract('ES')
            assert result == 'ESH24'  # H = March, 24 = 2024
        
        # Mock date in late March (after expiry)
        with patch('app.utils.futures.datetime') as mock_datetime:
            mock_dt = datetime(2024, 3, 20)
            mock_datetime.utcnow.return_value = mock_dt
            
            # Should select June 2024 contract (next quarterly)
            result = _nearest_quarterly_contract('ES')
            assert result == 'ESM24'  # M = June, 24 = 2024
    
    def test_year_rollover_with_exchange_calendar(self):
        """Test year rollover scenarios with proper expiry calculation."""
        # Mock date in late December
        with patch('app.utils.futures.datetime') as mock_datetime:
            mock_dt = datetime(2024, 12, 25)
            mock_datetime.utcnow.return_value = mock_dt
            
            # December 2024 expiry has passed (Dec 20), should pick March 2025
            result = _nearest_quarterly_contract('NQ')
            assert result == 'NQH25'  # H = March, 25 = 2025
    
    def test_multiple_contract_roots(self):
        """Test that different contract roots use appropriate expiry logic."""
        # Test both ES and NQ for same month
        es_expiry = get_contract_expiry_date('ES', 2024, 6)
        nq_expiry = get_contract_expiry_date('NQ', 2024, 6)
        
        # Both should have same expiry (third Friday of June 2024)
        assert es_expiry == nq_expiry
        expected = date(2024, 6, 21)  # Third Friday of June 2024
        assert es_expiry == expected
    
    def test_fallback_behavior_with_exchange_calendar(self):
        """Test fallback behavior when primary logic fails."""
        # Mock an exception in the main logic to trigger fallback
        with patch('app.utils.futures._nearest_quarterly_contract', side_effect=Exception("Mock error")):
            # Should fall back to simple heuristic but still use exchange calendar
            result = translate_root_to_front_month('ES')
            
            # Should still return a valid futures contract code
            assert len(result) == 5  # Format: ESUXY where XY is year
            assert result.startswith('ES')
            assert result[2] in 'HJMUZ'  # Valid quarterly month codes


class TestRealWorldScenarios:
    """Test real-world scenarios with actual market conditions."""
    
    def test_current_date_translation(self):
        """Test futures translation with current system date."""
        # This test uses actual current date
        result_es = translate_root_to_front_month('ES')
        result_nq = translate_root_to_front_month('NQ')
        
        # Should return valid contract codes
        assert len(result_es) == 5
        assert result_es.startswith('ES')
        assert len(result_nq) == 5
        assert result_nq.startswith('NQ')
        
        # Verify month codes are quarterly
        es_month_code = result_es[2]
        nq_month_code = result_nq[2]
        quarterly_codes = {'H', 'M', 'U', 'Z'}  # Mar, Jun, Sep, Dec
        
        assert es_month_code in quarterly_codes
        assert nq_month_code in quarterly_codes
    
    def test_holiday_calendar_coverage(self):
        """Test that our holiday calendar covers typical trading scenarios."""
        # Test major holidays that affect futures expiry
        
        # New Year's Day (should not be business day)
        new_years_2024 = date(2024, 1, 1)
        assert not is_business_day(new_years_2024)
        
        # Good Friday (should not be business day)
        good_friday_2024 = date(2024, 3, 29)
        assert not is_business_day(good_friday_2024)
        
        # Christmas (should not be business day)
        christmas_2024 = date(2024, 12, 25)
        assert not is_business_day(christmas_2024)
        
        # Regular trading day (should be business day)
        regular_day = date(2024, 6, 12)  # Wednesday, not a holiday
        assert is_business_day(regular_day)
    
    def test_contract_expiry_boundaries(self):
        """Test contract expiry around critical dates."""
        # Test expiry dates for 2024-2025 quarterly contracts
        test_cases = [
            (2024, 3, date(2024, 3, 15)),  # March 2024
            (2024, 6, date(2024, 6, 21)),  # June 2024
            (2024, 9, date(2024, 9, 20)),  # September 2024
            (2024, 12, date(2024, 12, 20)), # December 2024
            (2025, 3, date(2025, 3, 21)),  # March 2025
        ]
        
        for year, month, expected_date in test_cases:
            actual_date = get_contract_expiry_date('ES', year, month)
            assert actual_date == expected_date, f"Failed for {year}-{month}: expected {expected_date}, got {actual_date}"
            
            # Verify it's a Friday
            assert actual_date.weekday() == 4, f"Expiry {actual_date} is not a Friday"
            
            # Verify it's a business day
            assert is_business_day(actual_date), f"Expiry {actual_date} is not a business day"
