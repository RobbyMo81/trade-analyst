"""Type definitions and enums for trade analysis"""

from typing import TypeVar, Union, Optional, Dict, List, Any, Tuple, Callable
from enum import Enum, IntEnum
from dataclasses import dataclass
from datetime import datetime, date, time


# Generic type variables
T = TypeVar('T')
DataRecord = Dict[str, Any]
DataBatch = List[DataRecord]
Price = Union[int, float]
Volume = Union[int, float]
Timestamp = Union[str, datetime]


class OptionType(Enum):
    """Option types"""
    CALL = "call"
    PUT = "put"


class TradeSide(Enum):
    """Trade side for time and sales"""
    BUY = "buy"
    SELL = "sell"
    UNKNOWN = "unknown"


class OrderSide(Enum):
    """Order side for quotes"""
    BID = "bid"
    ASK = "ask"


class Exchange(Enum):
    """Trading venues/exchanges"""
    NYSE = "NYSE"
    NASDAQ = "NASDAQ"
    ARCA = "ARCA"
    BATS = "BATS"
    IEX = "IEX"
    CBOE = "CBOE"
    PSX = "PSX"
    BX = "BX"
    BYX = "BYX"
    EDGA = "EDGA"
    EDGX = "EDGX"
    CHX = "CHX"
    NSX = "NSX"
    OTHER = "OTHER"


class AssetClass(Enum):
    """Asset classes"""
    EQUITY = "equity"
    OPTION = "option"
    FUTURE = "future"
    FOREX = "forex"
    CRYPTO = "crypto"
    BOND = "bond"
    COMMODITY = "commodity"


class DataFrequency(Enum):
    """Data frequency/interval types"""
    TICK = "tick"
    SECOND = "second"
    MINUTE = "minute"
    FIVE_MINUTE = "5min"
    FIFTEEN_MINUTE = "15min"
    THIRTY_MINUTE = "30min"
    HOUR = "hour"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class MarketSession(Enum):
    """Market session types"""
    PRE_MARKET = "pre_market"
    REGULAR = "regular"
    AFTER_HOURS = "after_hours"
    EXTENDED = "extended"


class SecurityType(Enum):
    """Security types"""
    COMMON_STOCK = "common_stock"
    PREFERRED_STOCK = "preferred_stock"
    ETF = "etf"
    MUTUAL_FUND = "mutual_fund"
    INDEX = "index"
    WARRANT = "warrant"
    RIGHT = "right"
    ADR = "adr"


class QuoteCondition(Enum):
    """Quote condition codes"""
    REGULAR = "A"
    SLOW_ON_BID_ASK = "B"
    CLOSING = "C"
    FAST_TRADING = "F"
    SLOW_ON_BID = "E"
    SLOW_ON_ASK = "G"
    NON_FIRM = "N"
    OPENING = "O"
    REGULAR_TWO_SIDED_OPEN = "R"
    SLOW_ON_BID_ASK_TWO_SIDED = "W"


class TradeCondition(Enum):
    """Trade condition codes"""
    REGULAR = "R"
    OPENING = "O"
    CLOSING = "C"
    LAST = "L"
    EXTENDED_HOURS = "T"
    BLOCK = "B"
    INTERMARKET_SWEEP = "I"
    CROSS = "X"
    SOLD_OUT_OF_SEQUENCE = "Z"
    PRIOR_REFERENCE_PRICE = "P"
    MARKET_CENTER_OFFICIAL_CLOSE = "Q"
    AVERAGE_PRICE = "W"
    NEXT_DAY = "N"
    MARKET_CENTER_OFFICIAL_OPEN = "M"
    EXTENDED_HOURS_SOLD_OOS = "U"


class SizeCategory(Enum):
    """Trade size categories"""
    ODD_LOT = "odd_lot"           # < 100 shares
    ROUND_LOT = "round_lot"       # 100-999 shares
    LARGE = "large"               # 1,000-9,999 shares
    BLOCK = "block"               # 10,000-49,999 shares
    LARGE_BLOCK = "large_block"   # 50,000-99,999 shares
    INSTITUTIONAL = "institutional" # 100,000+ shares


class Moneyness(Enum):
    """Option moneyness"""
    ITM = "ITM"  # In the Money
    ATM = "ATM"  # At the Money
    OTM = "OTM"  # Out of the Money


class TimeInForce(Enum):
    """Order time in force"""
    DAY = "day"
    GTC = "gtc"
    IOC = "ioc"
    FOK = "fok"
    GTD = "gtd"


class OrderType(Enum):
    """Order types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"


class DataSource(Enum):
    """Data source providers"""
    POLYGON = "polygon"
    ALPHA_VANTAGE = "alpha_vantage"
    IEX = "iex"
    YAHOO = "yahoo"
    QUANDL = "quandl"
    BLOOMBERG = "bloomberg"
    REUTERS = "reuters"
    INTERNAL = "internal"


class DataQuality(IntEnum):
    """Data quality levels"""
    UNKNOWN = 0
    POOR = 1
    FAIR = 2
    GOOD = 3
    EXCELLENT = 4


class ProcessingStatus(Enum):
    """Data processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# Type aliases for complex types
SymbolList = List[str]
PriceLevel = Tuple[Price, Volume]
BookLevel = Dict[str, List[PriceLevel]]
Greeks = Dict[str, float]
OptionChain = Dict[str, List[DataRecord]]
Metrics = Dict[str, Union[int, float, str]]


@dataclass
class TimeRange:
    """Time range specification"""
    start: datetime
    end: datetime
    
    def __post_init__(self):
        if self.start >= self.end:
            raise ValueError("Start time must be before end time")
    
    @property
    def duration_seconds(self) -> float:
        """Duration in seconds"""
        return (self.end - self.start).total_seconds()
    
    @property
    def duration_minutes(self) -> float:
        """Duration in minutes"""
        return self.duration_seconds / 60
    
    @property
    def duration_hours(self) -> float:
        """Duration in hours"""
        return self.duration_minutes / 60


@dataclass
class PriceRange:
    """Price range specification"""
    low: Price
    high: Price
    
    def __post_init__(self):
        if self.low >= self.high:
            raise ValueError("Low price must be less than high price")
    
    @property
    def spread(self) -> float:
        """Price spread"""
        return float(self.high - self.low)
    
    @property
    def midpoint(self) -> float:
        """Midpoint price"""
        return (float(self.low) + float(self.high)) / 2
    
    def contains(self, price: Price) -> bool:
        """Check if price is within range"""
        return self.low <= price <= self.high


@dataclass
class VolumeRange:
    """Volume range specification"""
    min_volume: Volume
    max_volume: Volume
    
    def __post_init__(self):
        if self.min_volume > self.max_volume:
            raise ValueError("Min volume must be less than or equal to max volume")
    
    def contains(self, volume: Volume) -> bool:
        """Check if volume is within range"""
        return self.min_volume <= volume <= self.max_volume


@dataclass
class QuoteData:
    """Quote data structure"""
    symbol: str
    bid: Price
    ask: Price
    bid_size: Volume
    ask_size: Volume
    timestamp: datetime
    exchange: Optional[Exchange] = None
    conditions: Optional[List[str]] = None


@dataclass
class TradeData:
    """Trade data structure"""
    symbol: str
    price: Price
    size: Volume
    timestamp: datetime
    exchange: Exchange
    side: Optional[TradeSide] = None
    conditions: Optional[List[str]] = None
    trade_id: Optional[str] = None


@dataclass
class OHLCData:
    """OHLC bar data structure"""
    symbol: str
    open: Price
    high: Price
    low: Price
    close: Price
    volume: Volume
    timestamp: datetime
    frequency: DataFrequency
    vwap: Optional[Price] = None
    trade_count: Optional[int] = None


@dataclass
class OptionData:
    """Option data structure"""
    symbol: str
    underlying_symbol: str
    option_type: OptionType
    strike: Price
    expiration: date
    bid: Price
    ask: Price
    last: Price
    volume: Volume
    open_interest: int
    implied_volatility: float
    timestamp: datetime
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    rho: Optional[float] = None


@dataclass
class DataSourceConfig:
    """Data source configuration"""
    source: DataSource
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    rate_limit: Optional[int] = None
    timeout: Optional[int] = None
    retry_count: Optional[int] = None
    authentication: Optional[Dict[str, str]] = None


@dataclass
class ValidationConfig:
    """Data validation configuration"""
    strict_mode: bool = False
    allow_future_timestamps: bool = False
    max_price: Price = 1000000.0
    min_price: Price = 0.01
    max_volume: Volume = 1000000000
    max_age_days: Optional[int] = None
    required_fields: Optional[List[str]] = None


@dataclass
class ProcessingConfig:
    """Data processing configuration"""
    batch_size: int = 1000
    parallel_workers: int = 4
    timeout_seconds: int = 300
    retry_attempts: int = 3
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600


# Function type aliases
ValidatorFunc = Callable[[Any], bool]
ProcessorFunc = Callable[[DataRecord], DataRecord]
AggregatorFunc = Callable[[DataBatch], DataRecord]
FilterFunc = Callable[[DataRecord], bool]
MapperFunc = Callable[[DataRecord], DataRecord]


# Error types
class TradeAnalystError(Exception):
    """Base exception for trade analyst errors"""
    pass


class DataValidationError(TradeAnalystError):
    """Data validation error"""
    pass


class DataProcessingError(TradeAnalystError):
    """Data processing error"""
    pass


class DataSourceError(TradeAnalystError):
    """Data source error"""
    pass


class ConfigurationError(TradeAnalystError):
    """Configuration error"""
    pass


class AuthenticationError(TradeAnalystError):
    """Authentication error"""
    pass


# Constants
DEFAULT_MARKET_HOURS = {
    'pre_market_start': time(4, 0, 0),    # 4:00 AM
    'market_open': time(9, 30, 0),       # 9:30 AM
    'market_close': time(16, 0, 0),      # 4:00 PM
    'after_hours_end': time(20, 0, 0),   # 8:00 PM
}

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

# Standard lot sizes
STANDARD_LOT_SIZES = {
    AssetClass.EQUITY: 100,
    AssetClass.OPTION: 100,
    AssetClass.FUTURE: 1,
    AssetClass.FOREX: 100000,
    AssetClass.CRYPTO: 1,
}

# Decimal precision by asset class
PRICE_PRECISION = {
    AssetClass.EQUITY: 2,
    AssetClass.OPTION: 2,
    AssetClass.FUTURE: 4,
    AssetClass.FOREX: 5,
    AssetClass.CRYPTO: 8,
}

# Common stock exchanges
EQUITY_EXCHANGES = [
    Exchange.NYSE,
    Exchange.NASDAQ,
    Exchange.ARCA,
    Exchange.BATS,
    Exchange.IEX,
]

# Options exchanges
OPTIONS_EXCHANGES = [
    Exchange.CBOE,
    Exchange.NASDAQ,
    Exchange.NYSE,
    Exchange.ARCA,
]


def is_market_holiday(check_date: date) -> bool:
    """Check if date is a market holiday"""
    return check_date in MARKET_HOLIDAYS_2024


def is_market_open(check_time: time, session: MarketSession = MarketSession.REGULAR) -> bool:
    """Check if market is open at given time"""
    if session == MarketSession.REGULAR:
        return DEFAULT_MARKET_HOURS['market_open'] <= check_time <= DEFAULT_MARKET_HOURS['market_close']
    elif session == MarketSession.PRE_MARKET:
        return DEFAULT_MARKET_HOURS['pre_market_start'] <= check_time < DEFAULT_MARKET_HOURS['market_open']
    elif session == MarketSession.AFTER_HOURS:
        return DEFAULT_MARKET_HOURS['market_close'] < check_time <= DEFAULT_MARKET_HOURS['after_hours_end']
    elif session == MarketSession.EXTENDED:
        return DEFAULT_MARKET_HOURS['pre_market_start'] <= check_time <= DEFAULT_MARKET_HOURS['after_hours_end']
    return False


def get_lot_size(asset_class: AssetClass) -> int:
    """Get standard lot size for asset class"""
    return STANDARD_LOT_SIZES.get(asset_class, 1)


def get_price_precision(asset_class: AssetClass) -> int:
    """Get price precision for asset class"""
    return PRICE_PRECISION.get(asset_class, 2)


def format_price(price: Price, asset_class: AssetClass) -> str:
    """Format price with appropriate precision"""
    precision = get_price_precision(asset_class)
    return f"{float(price):.{precision}f}"


def classify_trade_size(size: Volume, asset_class: AssetClass = AssetClass.EQUITY) -> SizeCategory:
    """Classify trade size into category"""
    lot_size = get_lot_size(asset_class)
    
    if size < lot_size:
        return SizeCategory.ODD_LOT
    elif size < 10 * lot_size:
        return SizeCategory.ROUND_LOT
    elif size < 100 * lot_size:
        return SizeCategory.LARGE
    elif size < 500 * lot_size:
        return SizeCategory.BLOCK
    elif size < 1000 * lot_size:
        return SizeCategory.LARGE_BLOCK
    else:
        return SizeCategory.INSTITUTIONAL


# Example usage
if __name__ == "__main__":
    # Example data structures
    quote = QuoteData(
        symbol="AAPL",
        bid=150.25,
        ask=150.30,
        bid_size=1000,
        ask_size=800,
        timestamp=datetime.now(),
        exchange=Exchange.NASDAQ
    )
    
    trade = TradeData(
        symbol="AAPL",
        price=150.28,
        size=500,
        timestamp=datetime.now(),
        exchange=Exchange.NASDAQ,
        side=TradeSide.BUY
    )
    
    option = OptionData(
        symbol="AAPL240119C00150000",
        underlying_symbol="AAPL",
        option_type=OptionType.CALL,
        strike=150.0,
        expiration=date(2024, 1, 19),
        bid=2.50,
        ask=2.65,
        last=2.55,
        volume=1500,
        open_interest=5000,
        implied_volatility=0.25,
        timestamp=datetime.now(),
        delta=0.52
    )
    
    print(f"Quote: {quote}")
    print(f"Trade size category: {classify_trade_size(trade.size)}")
    print(f"Option moneyness: {Moneyness.ITM if trade.price > option.strike else Moneyness.OTM}")
    print(f"Formatted price: {format_price(trade.price, AssetClass.EQUITY)}")
    print(f"Market open: {is_market_open(datetime.now().time())}")
