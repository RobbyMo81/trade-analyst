"""Exchange calendar utilities for accurate futures expiry calculations."""

from datetime import date, timedelta
from typing import Set, Dict, Callable


# US federal holidays that affect exchange calendars
_FEDERAL_HOLIDAYS_2024_2030 = {
    # 2024
    date(2024, 1, 1): "New Year's Day",
    date(2024, 1, 15): "Martin Luther King Jr. Day",
    date(2024, 2, 19): "Presidents Day",
    date(2024, 3, 29): "Good Friday",
    date(2024, 5, 27): "Memorial Day",
    date(2024, 6, 19): "Juneteenth",
    date(2024, 7, 4): "Independence Day",
    date(2024, 9, 2): "Labor Day",
    date(2024, 10, 14): "Columbus Day",
    date(2024, 11, 11): "Veterans Day",
    date(2024, 11, 28): "Thanksgiving",
    date(2024, 12, 25): "Christmas",
    
    # 2025
    date(2025, 1, 1): "New Year's Day",
    date(2025, 1, 20): "Martin Luther King Jr. Day",
    date(2025, 2, 17): "Presidents Day",
    date(2025, 4, 18): "Good Friday",
    date(2025, 5, 26): "Memorial Day",
    date(2025, 6, 19): "Juneteenth",
    date(2025, 7, 4): "Independence Day",
    date(2025, 9, 1): "Labor Day",
    date(2025, 10, 13): "Columbus Day",
    date(2025, 11, 11): "Veterans Day",
    date(2025, 11, 27): "Thanksgiving",
    date(2025, 12, 25): "Christmas",
    
    # 2026
    date(2026, 1, 1): "New Year's Day",
    date(2026, 1, 19): "Martin Luther King Jr. Day",
    date(2026, 2, 16): "Presidents Day",
    date(2026, 4, 3): "Good Friday",
    date(2026, 5, 25): "Memorial Day",
    date(2026, 6, 19): "Juneteenth",
    date(2026, 7, 4): "Independence Day", # Saturday, observed Friday 7/3
    date(2026, 9, 7): "Labor Day",
    date(2026, 10, 12): "Columbus Day",
    date(2026, 11, 11): "Veterans Day",
    date(2026, 11, 26): "Thanksgiving",
    date(2026, 12, 25): "Christmas",
}

# CME Group specific holidays (additional to federal holidays)
_CME_ADDITIONAL_HOLIDAYS = {
    # Add CME-specific closures here
}


def is_business_day(dt: date, exchange: str = 'CME') -> bool:
    """Check if a given date is a business day for the specified exchange.
    
    Args:
        dt: Date to check
        exchange: Exchange identifier ('CME', 'CBOT', etc.)
        
    Returns:
        True if the date is a business day (Monday-Friday, not a holiday)
    """
    # Weekend check
    if dt.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    
    # Holiday check
    holidays = _FEDERAL_HOLIDAYS_2024_2030
    if exchange.upper() == 'CME':
        holidays = {**holidays, **_CME_ADDITIONAL_HOLIDAYS}
    
    return dt not in holidays


def get_third_friday_or_prior_business_day(year: int, month: int, exchange: str = 'CME') -> date:
    """Get the actual expiry date, accounting for holidays.
    
    For most futures, expiry is the third Friday. If that's a holiday,
    it moves to the prior business day.
    
    Args:
        year: Year
        month: Month
        exchange: Exchange identifier
        
    Returns:
        Actual expiry date
    """
    # Calculate third Friday
    first_day = date(year, month, 1)
    first_friday_offset = (4 - first_day.weekday() + 7) % 7
    first_friday = first_day + timedelta(days=first_friday_offset)
    third_friday = first_friday + timedelta(days=14)
    
    # If third Friday is a business day, use it
    if is_business_day(third_friday, exchange):
        return third_friday
    
    # Otherwise, move to prior business day
    candidate = third_friday
    while not is_business_day(candidate, exchange):
        candidate -= timedelta(days=1)
    
    return candidate


def get_es_expiry_date(year: int, month: int) -> date:
    """Get E-mini S&P 500 (ES) contract expiry date.
    
    ES expires on the third Friday of the contract month.
    If that's a holiday, it moves to the prior business day.
    """
    return get_third_friday_or_prior_business_day(year, month, 'CME')


def get_nq_expiry_date(year: int, month: int) -> date:
    """Get E-mini NASDAQ-100 (NQ) contract expiry date.
    
    NQ expires on the third Friday of the contract month.
    If that's a holiday, it moves to the prior business day.
    """
    return get_third_friday_or_prior_business_day(year, month, 'CME')


# Contract-specific expiry rules
_CONTRACT_EXPIRY_RULES: Dict[str, Callable[[int, int], date]] = {
    'ES': get_es_expiry_date,
    'NQ': get_nq_expiry_date,
}


def get_contract_expiry_date(root: str, year: int, month: int) -> date:
    """Get expiry date for a specific contract root.
    
    Args:
        root: Contract root symbol (e.g., 'ES', 'NQ')
        year: Contract year
        month: Contract month
        
    Returns:
        Expiry date for the contract
    """
    if root in _CONTRACT_EXPIRY_RULES:
        return _CONTRACT_EXPIRY_RULES[root](year, month)
    else:
        # Default to third Friday with holiday adjustment
        return get_third_friday_or_prior_business_day(year, month)


def get_next_business_day(dt: date, exchange: str = 'CME') -> date:
    """Get the next business day after the given date."""
    candidate = dt + timedelta(days=1)
    while not is_business_day(candidate, exchange):
        candidate += timedelta(days=1)
    return candidate


def get_trading_days_until_expiry(current_date: date, expiry_date: date, 
                                 exchange: str = 'CME') -> int:
    """Count trading days between current date and expiry date."""
    if current_date >= expiry_date:
        return 0
    
    count = 0
    candidate = current_date
    while candidate < expiry_date:
        candidate = get_next_business_day(candidate, exchange)
        if candidate <= expiry_date:
            count += 1
    
    return count
