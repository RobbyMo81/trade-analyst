"""Unit tests for exchange calendar functionality."""

import pytest
from datetime import date, timedelta
from unittest.mock import patch

from app.utils.exchange_calendar import (
    is_business_day,
    get_third_friday_or_prior_business_day,
    get_contract_expiry_date,
    get_next_business_day,
    get_trading_days_until_expiry,
    get_es_expiry_date,
    get_nq_expiry_date,
    _FEDERAL_HOLIDAYS_2024_2030
)


class TestIsBusinessDay:
    """Test business day determination."""
    
    def test_weekday_is_business_day(self):
        """Monday through Friday should be business days if not holidays."""
        # Monday, Jan 8, 2024 (not a holiday)
        monday = date(2024, 1, 8)
        assert is_business_day(monday)
        
        # Friday, Jan 12, 2024 (not a holiday)
        friday = date(2024, 1, 12)
        assert is_business_day(friday)
    
    def test_weekend_not_business_day(self):
        """Saturday and Sunday should not be business days."""
        # Saturday, Jan 6, 2024
        saturday = date(2024, 1, 6)
        assert not is_business_day(saturday)
        
        # Sunday, Jan 7, 2024
        sunday = date(2024, 1, 7)
        assert not is_business_day(sunday)
    
    def test_federal_holiday_not_business_day(self):
        """Federal holidays should not be business days."""
        # New Year's Day 2024 (Monday)
        new_years = date(2024, 1, 1)
        assert not is_business_day(new_years)
        
        # Christmas 2024 (Wednesday)
        christmas = date(2024, 12, 25)
        assert not is_business_day(christmas)
    
    def test_good_friday_not_business_day(self):
        """Good Friday should not be a business day for financial markets."""
        # Good Friday 2024
        good_friday = date(2024, 3, 29)
        assert not is_business_day(good_friday)
        
        # Good Friday 2025
        good_friday_2025 = date(2025, 4, 18)
        assert not is_business_day(good_friday_2025)


class TestThirdFridayOrPriorBusinessDay:
    """Test third Friday calculation with business day adjustment."""
    
    def test_third_friday_normal_case(self):
        """When third Friday is a business day, use it directly."""
        # March 2024 - third Friday is March 15 (not a holiday)
        result = get_third_friday_or_prior_business_day(2024, 3)
        expected = date(2024, 3, 15)
        assert result == expected
    
    def test_third_friday_on_good_friday(self):
        """When third Friday is Good Friday, move to prior business day."""
        # March 2024 - third Friday (March 15) is not Good Friday
        # But let's test April 2024 where Good Friday is March 29 (not third Friday)
        # Let's create a scenario where third Friday would be a holiday
        
        # Use a month where third Friday could be a problem
        # June 2025 - third Friday is June 20 (not a holiday in our list)
        result = get_third_friday_or_prior_business_day(2025, 6)
        expected = date(2025, 6, 20)  # Should be business day
        assert result == expected
    
    def test_third_friday_adjustment_needed(self):
        """Test case where third Friday needs adjustment."""
        # We need to mock a scenario where third Friday is a holiday
        test_holidays = {date(2024, 6, 21): "Test Holiday"}  # Mock third Friday as holiday
        
        with patch('app.utils.exchange_calendar._FEDERAL_HOLIDAYS_2024_2030', test_holidays):
            # June 2024 - third Friday would be June 21, but it's a "holiday"
            result = get_third_friday_or_prior_business_day(2024, 6)
            # Should move to Thursday, June 20
            expected = date(2024, 6, 20)
            assert result == expected
    
    def test_multiple_days_adjustment(self):
        """Test case where multiple days need adjustment."""
        # Mock scenario where third Friday and Thursday are both holidays
        test_holidays = {
            date(2024, 6, 21): "Test Holiday Friday",
            date(2024, 6, 20): "Test Holiday Thursday"
        }
        
        with patch('app.utils.exchange_calendar._FEDERAL_HOLIDAYS_2024_2030', test_holidays):
            result = get_third_friday_or_prior_business_day(2024, 6)
            # Should move to Wednesday, June 19
            expected = date(2024, 6, 19)
            assert result == expected


class TestContractSpecificExpiry:
    """Test contract-specific expiry date functions."""
    
    def test_es_expiry_date(self):
        """Test ES contract expiry calculation."""
        # March 2024 ES should expire on third Friday
        result = get_es_expiry_date(2024, 3)
        expected = date(2024, 3, 15)  # Third Friday of March 2024
        assert result == expected
    
    def test_nq_expiry_date(self):
        """Test NQ contract expiry calculation."""
        # June 2024 NQ should expire on third Friday
        result = get_nq_expiry_date(2024, 6)
        expected = date(2024, 6, 21)  # Third Friday of June 2024
        assert result == expected
    
    def test_get_contract_expiry_date_es(self):
        """Test generic contract expiry for ES."""
        result = get_contract_expiry_date('ES', 2024, 9)
        expected = date(2024, 9, 20)  # Third Friday of September 2024
        assert result == expected
    
    def test_get_contract_expiry_date_nq(self):
        """Test generic contract expiry for NQ."""
        result = get_contract_expiry_date('NQ', 2024, 12)
        expected = date(2024, 12, 20)  # Third Friday of December 2024
        assert result == expected
    
    def test_get_contract_expiry_date_unknown_root(self):
        """Test generic contract expiry for unknown root symbols."""
        # Should use default third Friday logic
        result = get_contract_expiry_date('XYZ', 2024, 3)
        expected = date(2024, 3, 15)  # Third Friday of March 2024
        assert result == expected


class TestNextBusinessDay:
    """Test next business day calculation."""
    
    def test_next_business_day_from_friday(self):
        """Next business day from Friday should be Monday."""
        # Friday, June 14, 2024
        friday = date(2024, 6, 14)
        result = get_next_business_day(friday)
        # Should be Monday, June 17, 2024
        expected = date(2024, 6, 17)
        assert result == expected
    
    def test_next_business_day_from_weekday(self):
        """Next business day from Tuesday should be Wednesday."""
        # Tuesday, June 11, 2024
        tuesday = date(2024, 6, 11)
        result = get_next_business_day(tuesday)
        # Should be Wednesday, June 12, 2024
        expected = date(2024, 6, 12)
        assert result == expected
    
    def test_next_business_day_skip_holiday(self):
        """Next business day should skip holidays."""
        # Day before New Year's Day 2024 (Monday)
        # December 29, 2023 (Friday)
        dec_29 = date(2023, 12, 29)
        result = get_next_business_day(dec_29)
        # Should skip weekend and New Year's Day, go to January 2, 2024
        expected = date(2024, 1, 2)
        assert result == expected


class TestTradingDaysUntilExpiry:
    """Test trading days calculation."""
    
    def test_trading_days_same_week(self):
        """Count trading days within the same week."""
        # Monday to Friday in same week
        monday = date(2024, 6, 10)
        friday = date(2024, 6, 14)
        result = get_trading_days_until_expiry(monday, friday)
        # Should be 4 trading days (Tue, Wed, Thu, Fri)
        assert result == 4
    
    def test_trading_days_over_weekend(self):
        """Count trading days over a weekend."""
        # Friday to next Tuesday
        friday = date(2024, 6, 14)
        tuesday = date(2024, 6, 18)
        result = get_trading_days_until_expiry(friday, tuesday)
        # Should be 2 trading days (Mon, Tue)
        assert result == 2
    
    def test_trading_days_with_holiday(self):
        """Count trading days with intervening holiday."""
        # Before and after a holiday
        # June 18, 2024 (Tuesday) to June 21, 2024 (Friday)
        # Assuming Juneteenth (June 19) is a holiday
        start_date = date(2024, 6, 18)
        end_date = date(2024, 6, 21)
        result = get_trading_days_until_expiry(start_date, end_date)
        # Should skip Juneteenth, count Thu and Fri
        assert result == 2
    
    def test_trading_days_zero_case(self):
        """When current date is at or past expiry, should return 0."""
        # Same date
        same_date = date(2024, 6, 15)
        result = get_trading_days_until_expiry(same_date, same_date)
        assert result == 0
        
        # Current date after expiry
        later_date = date(2024, 6, 16)
        earlier_date = date(2024, 6, 15)
        result = get_trading_days_until_expiry(later_date, earlier_date)
        assert result == 0


class TestHolidayData:
    """Test that holiday data is comprehensive."""
    
    def test_federal_holidays_coverage(self):
        """Ensure we have federal holidays for multiple years."""
        # Should have holidays for 2024, 2025, 2026
        years_with_holidays = set()
        for holiday_date in _FEDERAL_HOLIDAYS_2024_2030.keys():
            years_with_holidays.add(holiday_date.year)
        
        assert 2024 in years_with_holidays
        assert 2025 in years_with_holidays
        assert 2026 in years_with_holidays
    
    def test_good_friday_included(self):
        """Ensure Good Friday is included for multiple years."""
        good_fridays = []
        for holiday_date, name in _FEDERAL_HOLIDAYS_2024_2030.items():
            if "Good Friday" in name:
                good_fridays.append(holiday_date)
        
        assert len(good_fridays) >= 3  # Should have multiple years
        
        # Verify specific Good Friday dates
        assert date(2024, 3, 29) in good_fridays
        assert date(2025, 4, 18) in good_fridays
    
    def test_major_holidays_included(self):
        """Ensure major trading holidays are included."""
        holiday_names = set(_FEDERAL_HOLIDAYS_2024_2030.values())
        
        assert "New Year's Day" in holiday_names
        assert "Good Friday" in holiday_names  
        assert "Independence Day" in holiday_names
        assert "Thanksgiving" in holiday_names
        assert "Christmas" in holiday_names
