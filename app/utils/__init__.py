"""Package initialization for utils module"""

from .validators import (
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

from .types import (
    # Type aliases
    DataRecord,
    DataBatch,
    Price,
    Volume,
    Timestamp,
    SymbolList,
    PriceLevel,
    BookLevel,
    Greeks,
    OptionChain,
    Metrics,
    
    # Enums
    OptionType,
    TradeSide,
    OrderSide,
    Exchange,
    AssetClass,
    DataFrequency,
    MarketSession,
    SecurityType,
    QuoteCondition,
    TradeCondition,
    SizeCategory,
    Moneyness,
    TimeInForce,
    OrderType,
    DataSource,
    DataQuality,
    ProcessingStatus,
    
    # Data classes
    TimeRange,
    PriceRange,
    VolumeRange,
    QuoteData,
    TradeData,
    OHLCData,
    OptionData,
    DataSourceConfig,
    ValidationConfig,
    ProcessingConfig,
    
    # Functions
    is_market_holiday,
    is_market_open,
    get_lot_size,
    get_price_precision,
    format_price,
    classify_trade_size,
    
    # Constants
    DEFAULT_MARKET_HOURS,
    MARKET_HOLIDAYS_2024,
    STANDARD_LOT_SIZES,
    PRICE_PRECISION,
    EQUITY_EXCHANGES,
    OPTIONS_EXCHANGES,
    
    # Exceptions
    TradeAnalystError,
    DataValidationError,
    DataProcessingError,
    DataSourceError,
    ConfigurationError,
    AuthenticationError
)

from .hashing import (
    hash_string,
    hash_dict,
    hash_list,
    hash_dataframe,
    hash_file,
    create_content_hash,
    generate_trade_hash,
    generate_quote_hash,
    generate_ohlc_hash,
    generate_option_hash,
    batch_hash_records,
    find_duplicate_hashes,
    remove_duplicate_records,
    verify_data_integrity,
    HashManager,
    DataIntegrityChecker,
    hash_trade_batch,
    hash_quote_batch,
    hash_ohlc_batch,
    hash_option_batch
)

from .timeutils import (
    TimeZone,
    MarketHours,
    is_weekend,
    is_market_holiday,
    is_business_day,
    get_business_days,
    get_next_business_day,
    get_previous_business_day,
    convert_timezone,
    utc_to_market_time,
    market_time_to_utc,
    parse_timestamp,
    format_timestamp,
    get_trading_session,
    get_time_range_boundaries,
    calculate_time_metrics,
    get_market_calendar,
    TimeRangeIterator,
    DEFAULT_MARKET_HOURS
)

__version__ = "1.0.0"
__author__ = "Trade Analyst Team"

# Convenience imports for common use cases
__all__ = [
    # Validators
    'ValidationResult',
    'ValidationError', 
    'SchemaValidator',
    'validate_symbol',
    'validate_price',
    'validate_volume',
    'validate_timestamp',
    
    # Types
    'DataRecord',
    'DataBatch',
    'Price',
    'Volume',
    'Timestamp',
    'OptionType',
    'TradeSide',
    'Exchange',
    'AssetClass',
    'QuoteData',
    'TradeData',
    'OHLCData',
    'OptionData',
    
    # Hashing
    'create_content_hash',
    'generate_trade_hash',
    'generate_quote_hash',
    'HashManager',
    'DataIntegrityChecker',
    
    # Time utilities
    'MarketHours',
    'is_business_day',
    'get_next_business_day',
    'utc_to_market_time',
    'market_time_to_utc',
    'parse_timestamp',
    'format_timestamp',
    'get_trading_session'
]
