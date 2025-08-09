"""Time utilities for trading applications"""

from typing import Optional, List, Union, Tuple
from datetime import datetime, date, time, timedelta, timezone
import pytz
from enum import Enum
import calendar
import logging

logger = logging.getLogger(__name__)


class TimeZone(Enum):
    """Common timezone definitions"""
    UTC = "UTC"
    EST = "US/Eastern"
    CST = "US/Central"
    MST = "US/Mountain"
    PST = "US/Pacific"
    LONDON = "Europe/London"
    TOKYO = "Asia/Tokyo"
    HONG_KONG = "Asia/Hong_Kong"
    SYDNEY = "Australia/Sydney"


class MarketHours:
    """Market hours configuration"""
    
    def __init__(self, 
                 pre_market_start: time = time(4, 0, 0),
                 market_open: time = time(9, 30, 0),
                 market_close: time = time(16, 0, 0),
                 after_hours_end: time = time(20, 0, 0),
                 timezone: str = "US/Eastern"):
        """
        Initialize market hours
        
        Args:
            pre_market_start: Pre-market start time
            market_open: Regular market open time
            market_close: Regular market close time
            after_hours_end: After-hours end time
            timezone: Market timezone
        """
        self.pre_market_start = pre_market_start
        self.market_open = market_open
        self.market_close = market_close
        self.after_hours_end = after_hours_end
        self.timezone = pytz.timezone(timezone)
    
    def is_regular_hours(self, dt: datetime) -> bool:
        """Check if datetime is during regular market hours"""
        market_dt = self.to_market_time(dt)
        return self.market_open <= market_dt.time() <= self.market_close
    
    def is_pre_market(self, dt: datetime) -> bool:
        """Check if datetime is during pre-market hours"""
        market_dt = self.to_market_time(dt)
        return self.pre_market_start <= market_dt.time() < self.market_open
    
    def is_after_hours(self, dt: datetime) -> bool:
        """Check if datetime is during after-hours"""
        market_dt = self.to_market_time(dt)
        return self.market_close < market_dt.time() <= self.after_hours_end
    
    def is_extended_hours(self, dt: datetime) -> bool:
        """Check if datetime is during extended hours (pre + after)"""
        return self.is_pre_market(dt) or self.is_after_hours(dt)
    
    def is_market_open(self, dt: datetime, include_extended: bool = False) -> bool:
        """Check if market is open at given datetime"""
        if include_extended:
            return (self.is_regular_hours(dt) or 
                   self.is_pre_market(dt) or 
                   self.is_after_hours(dt))
        return self.is_regular_hours(dt)
    
    def to_market_time(self, dt: datetime) -> datetime:
        """Convert datetime to market timezone"""
        if dt.tzinfo is None:
            # Assume UTC if no timezone
            dt = pytz.UTC.localize(dt)
        return dt.astimezone(self.timezone)
    
    def get_next_market_open(self, from_dt: Optional[datetime] = None) -> datetime:
        """Get next market open datetime"""
        if from_dt is None:
            from_dt = datetime.now(self.timezone)
        else:
            from_dt = self.to_market_time(from_dt)
        
        # Start from current date
        current_date = from_dt.date()
        
        # Check if market is already open today
        market_open_today = self.timezone.localize(
            datetime.combine(current_date, self.market_open)
        )
        
        if from_dt < market_open_today and not is_market_holiday(current_date):
            return market_open_today
        
        # Find next business day
        next_date = current_date + timedelta(days=1)
        while is_weekend(next_date) or is_market_holiday(next_date):
            next_date += timedelta(days=1)
        
        return self.timezone.localize(
            datetime.combine(next_date, self.market_open)
        )
    
    def get_next_market_close(self, from_dt: Optional[datetime] = None) -> datetime:
        """Get next market close datetime"""
        if from_dt is None:
            from_dt = datetime.now(self.timezone)
        else:
            from_dt = self.to_market_time(from_dt)
        
        current_date = from_dt.date()
        
        # Check if market closes today
        market_close_today = self.timezone.localize(
            datetime.combine(current_date, self.market_close)
        )
        
        if (from_dt < market_close_today and 
            not is_weekend(current_date) and 
            not is_market_holiday(current_date)):
            return market_close_today
        
        # Find next business day close
        next_date = current_date + timedelta(days=1)
        while is_weekend(next_date) or is_market_holiday(next_date):
            next_date += timedelta(days=1)
        
        return self.timezone.localize(
            datetime.combine(next_date, self.market_close)
        )


# Market holidays for 2024 (can be extended or loaded from external source)
MARKET_HOLIDAYS_2024 = [
    date(2024, 1, 1),   # New Year's Day
    date(2024, 1, 15),  # Martin Luther King Jr. Day
    date(2024, 2, 19),  # Presidents' Day
    date(2024, 3, 29),  # Good Friday
    date(2024, 5, 27),  # Memorial Day
    date(2024, 6, 19),  # Juneteenth
    date(2024, 7, 4),   # Independence Day
    date(2024, 9, 2),   # Labor Day
    date(2024, 11, 28), # Thanksgiving
    date(2024, 12, 25), # Christmas
]


def is_weekend(check_date: date) -> bool:
    """Check if date is a weekend"""
    return check_date.weekday() >= 5  # Saturday=5, Sunday=6


def is_market_holiday(check_date: date, holidays: Optional[List[date]] = None) -> bool:
    """Check if date is a market holiday"""
    if holidays is None:
        holidays = MARKET_HOLIDAYS_2024
    return check_date in holidays


def is_business_day(check_date: date, holidays: Optional[List[date]] = None) -> bool:
    """Check if date is a business day"""
    return not is_weekend(check_date) and not is_market_holiday(check_date, holidays)


def get_business_days(start_date: date, end_date: date, 
                     holidays: Optional[List[date]] = None) -> List[date]:
    """Get list of business days between start and end dates"""
    business_days = []
    current_date = start_date
    
    while current_date <= end_date:
        if is_business_day(current_date, holidays):
            business_days.append(current_date)
        current_date += timedelta(days=1)
    
    return business_days


def get_next_business_day(from_date: date, holidays: Optional[List[date]] = None) -> date:
    """Get next business day from given date"""
    next_date = from_date + timedelta(days=1)
    while not is_business_day(next_date, holidays):
        next_date += timedelta(days=1)
    return next_date


def get_previous_business_day(from_date: date, holidays: Optional[List[date]] = None) -> date:
    """Get previous business day from given date"""
    prev_date = from_date - timedelta(days=1)
    while not is_business_day(prev_date, holidays):
        prev_date -= timedelta(days=1)
    return prev_date


def convert_timezone(dt: datetime, from_tz: str, to_tz: str) -> datetime:
    """
    Convert datetime from one timezone to another
    
    Args:
        dt: Datetime to convert
        from_tz: Source timezone string
        to_tz: Target timezone string
        
    Returns:
        Converted datetime
    """
    from_timezone = pytz.timezone(from_tz)
    to_timezone = pytz.timezone(to_tz)
    
    # Localize if naive
    if dt.tzinfo is None:
        dt = from_timezone.localize(dt)
    
    return dt.astimezone(to_timezone)


def utc_to_market_time(utc_dt: datetime, market_tz: str = "US/Eastern") -> datetime:
    """Convert UTC datetime to market timezone"""
    if utc_dt.tzinfo is None:
        utc_dt = pytz.UTC.localize(utc_dt)
    
    market_timezone = pytz.timezone(market_tz)
    return utc_dt.astimezone(market_timezone)


def market_time_to_utc(market_dt: datetime, market_tz: str = "US/Eastern") -> datetime:
    """Convert market timezone datetime to UTC"""
    if market_dt.tzinfo is None:
        market_timezone = pytz.timezone(market_tz)
        market_dt = market_timezone.localize(market_dt)
    
    return market_dt.astimezone(pytz.UTC)


def parse_timestamp(timestamp: Union[str, datetime, int, float], 
                   default_tz: Optional[str] = None) -> datetime:
    """
    Parse various timestamp formats into datetime
    
    Args:
        timestamp: Timestamp to parse
        default_tz: Default timezone if none specified
        
    Returns:
        Parsed datetime
    """
    if isinstance(timestamp, datetime):
        return timestamp
    
    if isinstance(timestamp, (int, float)):
        # Unix timestamp
        return datetime.fromtimestamp(timestamp, tz=pytz.UTC)
    
    if isinstance(timestamp, str):
        # Try various string formats
        try:
            # ISO format
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt
        except ValueError:
            pass
        
        try:
            # Common formats
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M:%S.%f',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%d',
                '%m/%d/%Y %H:%M:%S',
                '%m/%d/%Y'
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(timestamp, fmt)
                    if default_tz:
                        tz = pytz.timezone(default_tz)
                        dt = tz.localize(dt)
                    return dt
                except ValueError:
                    continue
        except Exception:
            pass
    
    raise ValueError(f"Unable to parse timestamp: {timestamp}")


def format_timestamp(dt: datetime, format_type: str = 'iso') -> str:
    """
    Format datetime into string
    
    Args:
        dt: Datetime to format
        format_type: Format type ('iso', 'market', 'date', 'time')
        
    Returns:
        Formatted timestamp string
    """
    if format_type == 'iso':
        return dt.isoformat()
    elif format_type == 'market':
        return dt.strftime('%Y-%m-%d %H:%M:%S %Z')
    elif format_type == 'date':
        return dt.strftime('%Y-%m-%d')
    elif format_type == 'time':
        return dt.strftime('%H:%M:%S')
    else:
        return str(dt)


def get_trading_session(dt: datetime, market_hours: Optional[MarketHours] = None) -> str:
    """
    Get trading session for datetime
    
    Args:
        dt: Datetime to check
        market_hours: Market hours configuration
        
    Returns:
        Session name ('pre_market', 'regular', 'after_hours', 'closed')
    """
    if market_hours is None:
        market_hours = MarketHours()
    
    if market_hours.is_regular_hours(dt):
        return 'regular'
    elif market_hours.is_pre_market(dt):
        return 'pre_market'
    elif market_hours.is_after_hours(dt):
        return 'after_hours'
    else:
        return 'closed'


def get_time_range_boundaries(start: datetime, end: datetime, 
                            interval: str = 'day') -> List[datetime]:
    """
    Get time boundaries for a range at specified interval
    
    Args:
        start: Start datetime
        end: End datetime
        interval: Interval type ('minute', 'hour', 'day', 'week', 'month')
        
    Returns:
        List of boundary datetimes
    """
    boundaries = []
    current = start
    
    if interval == 'minute':
        delta = timedelta(minutes=1)
    elif interval == 'hour':
        delta = timedelta(hours=1)
    elif interval == 'day':
        delta = timedelta(days=1)
    elif interval == 'week':
        delta = timedelta(weeks=1)
    elif interval == 'month':
        # Handle months separately
        while current <= end:
            boundaries.append(current)
            # Add one month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        return boundaries
    else:
        raise ValueError(f"Unsupported interval: {interval}")
    
    while current <= end:
        boundaries.append(current)
        current += delta
    
    return boundaries


def calculate_time_metrics(timestamps: List[datetime]) -> dict:
    """
    Calculate time-related metrics from timestamps
    
    Args:
        timestamps: List of timestamps
        
    Returns:
        Dictionary of metrics
    """
    if not timestamps:
        return {}
    
    sorted_timestamps = sorted(timestamps)
    
    metrics = {
        'count': len(timestamps),
        'start_time': sorted_timestamps[0],
        'end_time': sorted_timestamps[-1],
        'duration_seconds': (sorted_timestamps[-1] - sorted_timestamps[0]).total_seconds(),
    }
    
    # Calculate intervals between timestamps
    if len(sorted_timestamps) > 1:
        intervals = []
        for i in range(1, len(sorted_timestamps)):
            interval = (sorted_timestamps[i] - sorted_timestamps[i-1]).total_seconds()
            intervals.append(interval)
        
        metrics.update({
            'average_interval_seconds': sum(intervals) / len(intervals),
            'min_interval_seconds': min(intervals),
            'max_interval_seconds': max(intervals),
            'frequency_per_minute': len(timestamps) / (metrics['duration_seconds'] / 60) if metrics['duration_seconds'] > 0 else 0
        })
    
    return metrics


def get_market_calendar(year: int, holidays: Optional[List[date]] = None) -> List[date]:
    """
    Get market calendar (business days) for a year
    
    Args:
        year: Year to get calendar for
        holidays: List of holidays to exclude
        
    Returns:
        List of business days
    """
    if holidays is None:
        holidays = MARKET_HOLIDAYS_2024
    
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)
    
    return get_business_days(start_date, end_date, holidays)


class TimeRangeIterator:
    """Iterator for time ranges"""
    
    def __init__(self, start: datetime, end: datetime, step: timedelta):
        """
        Initialize time range iterator
        
        Args:
            start: Start datetime
            end: End datetime
            step: Time step
        """
        self.start = start
        self.end = end
        self.step = step
        self.current = start
    
    def __iter__(self):
        return self
    
    def __next__(self):
        if self.current > self.end:
            raise StopIteration
        
        result = self.current
        self.current += self.step
        return result


# Default market hours instance
DEFAULT_MARKET_HOURS = MarketHours()


# Example usage
def example_time_utils_usage():
    """Example usage of time utilities"""
    
    # Current time
    now = datetime.now()
    print(f"Current time: {now}")
    
    # Market hours checking
    market_hours = MarketHours()
    print(f"Is regular hours: {market_hours.is_regular_hours(now)}")
    print(f"Trading session: {get_trading_session(now)}")
    
    # Next market events
    next_open = market_hours.get_next_market_open()
    next_close = market_hours.get_next_market_close()
    print(f"Next market open: {next_open}")
    print(f"Next market close: {next_close}")
    
    # Business days
    today = date.today()
    next_bday = get_next_business_day(today)
    print(f"Next business day: {next_bday}")
    
    # Timezone conversion
    utc_time = datetime.now(pytz.UTC)
    market_time = utc_to_market_time(utc_time)
    print(f"UTC: {utc_time}, Market: {market_time}")
    
    # Time range
    start = datetime(2024, 1, 1, 9, 30)
    end = datetime(2024, 1, 1, 16, 0)
    
    for dt in TimeRangeIterator(start, end, timedelta(hours=1)):
        print(f"Hour boundary: {dt}")


if __name__ == "__main__":
    example_time_utils_usage()
