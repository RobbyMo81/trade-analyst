"""
Enhanced Futures Symbol Handling

Provides comprehensive futures symbol parsing, validation, and translation
based on the standard futures symbol schema.
"""
from dataclasses import dataclass
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
import re
from enum import Enum

# Futures month codes mapping (month number to letter code)
MONTH_CODES = {
    1: 'F', 2: 'G', 3: 'H', 4: 'J', 5: 'K', 6: 'M',
    7: 'N', 8: 'Q', 9: 'U', 10: 'V', 11: 'X', 12: 'Z'
}

# Reverse mapping (letter code to month number)
CODE_TO_MONTH = {v: k for k, v in MONTH_CODES.items()}

class FuturesCategory(Enum):
    INDICES = "Indices"
    ENERGY = "Energy"
    INTEREST_RATES = "Interest Rates"
    CURRENCY = "Currency"
    METALS = "Metals"
    HOUSING = "Housing"
    LIVESTOCK = "Livestock"
    GRAINS = "Grains"
    MINI_GRAINS = "Mini Grains"
    FOOD_FIBER = "Food & Fiber"

@dataclass
class FuturesSymbol:
    """
    Represents a futures symbol according to the standard schema.
    """
    symbol: str  # Full symbol (e.g., "ESZ25")
    root: str  # Root symbol (e.g., "ES")
    month_code: str  # Month code (e.g., "Z")
    year: int  # Last two digits of year (e.g., 25)
    category: FuturesCategory
    description: str
    
    @property
    def full_year(self) -> int:
        """Convert 2-digit year to 4-digit year."""
        # Assume 20XX for years 00-49, 19XX for years 50-99
        if self.year <= 49:
            return 2000 + self.year
        else:
            return 1900 + self.year
    
    @property
    def month_number(self) -> int:
        """Get month number from month code."""
        return CODE_TO_MONTH.get(self.month_code, 0)
    
    @property
    def expiry_month_year(self) -> Tuple[int, int]:
        """Get (month, year) tuple for expiry."""
        return (self.month_number, self.full_year)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary format matching the JSON schema."""
        return {
            "symbol": self.symbol,
            "root": self.root,
            "monthCode": self.month_code,
            "year": self.year,
            "category": self.category.value,
            "description": self.description
        }

# Known futures symbols database
FUTURES_DATABASE = {
    # Indices
    "ES": FuturesSymbol("", "ES", "", 0, FuturesCategory.INDICES, "E-mini S&P 500"),
    "NQ": FuturesSymbol("", "NQ", "", 0, FuturesCategory.INDICES, "E-mini NASDAQ 100"),
    "YM": FuturesSymbol("", "YM", "", 0, FuturesCategory.INDICES, "E-mini Dow Jones"),
    "RTY": FuturesSymbol("", "RTY", "", 0, FuturesCategory.INDICES, "E-mini Russell 2000"),
    
    # Energy
    "CL": FuturesSymbol("", "CL", "", 0, FuturesCategory.ENERGY, "Crude Oil"),
    "NG": FuturesSymbol("", "NG", "", 0, FuturesCategory.ENERGY, "Natural Gas"),
    "RB": FuturesSymbol("", "RB", "", 0, FuturesCategory.ENERGY, "RBOB Gasoline"),
    "HO": FuturesSymbol("", "HO", "", 0, FuturesCategory.ENERGY, "Heating Oil"),
    
    # Metals
    "GC": FuturesSymbol("", "GC", "", 0, FuturesCategory.METALS, "Gold"),
    "SI": FuturesSymbol("", "SI", "", 0, FuturesCategory.METALS, "Silver"),
    "HG": FuturesSymbol("", "HG", "", 0, FuturesCategory.METALS, "Copper"),
    "PL": FuturesSymbol("", "PL", "", 0, FuturesCategory.METALS, "Platinum"),
    
    # Currency
    "6E": FuturesSymbol("", "6E", "", 0, FuturesCategory.CURRENCY, "Euro"),
    "6B": FuturesSymbol("", "6B", "", 0, FuturesCategory.CURRENCY, "British Pound"),
    "6J": FuturesSymbol("", "6J", "", 0, FuturesCategory.CURRENCY, "Japanese Yen"),
    "6C": FuturesSymbol("", "6C", "", 0, FuturesCategory.CURRENCY, "Canadian Dollar"),
    
    # Interest Rates
    "ZB": FuturesSymbol("", "ZB", "", 0, FuturesCategory.INTEREST_RATES, "30-Year Treasury Bond"),
    "ZN": FuturesSymbol("", "ZN", "", 0, FuturesCategory.INTEREST_RATES, "10-Year Treasury Note"),
    "ZF": FuturesSymbol("", "ZF", "", 0, FuturesCategory.INTEREST_RATES, "5-Year Treasury Note"),
    
    # Grains
    "ZC": FuturesSymbol("", "ZC", "", 0, FuturesCategory.GRAINS, "Corn"),
    "ZS": FuturesSymbol("", "ZS", "", 0, FuturesCategory.GRAINS, "Soybeans"),
    "ZW": FuturesSymbol("", "ZW", "", 0, FuturesCategory.GRAINS, "Wheat"),
    
    # Livestock
    "LE": FuturesSymbol("", "LE", "", 0, FuturesCategory.LIVESTOCK, "Live Cattle"),
    "HE": FuturesSymbol("", "HE", "", 0, FuturesCategory.LIVESTOCK, "Lean Hogs"),
}

def parse_futures_symbol(symbol: str) -> Optional[FuturesSymbol]:
    """
    Parse a futures symbol string into FuturesSymbol object.
    
    Args:
        symbol: Futures symbol like "ESZ25", "/ESZ25", "ES", "/ES"
        
    Returns:
        FuturesSymbol object or None if parsing fails
    """
    if not symbol:
        return None
    
    # Remove leading slash if present
    clean_symbol = symbol.lstrip('/')
    
    # Pattern: ROOT + MONTH_CODE + YY (e.g., ESZ25)
    match = re.match(r'^([A-Z]{1,3})([FGHJKMNQUVXZ])(\d{2})$', clean_symbol.upper())
    
    if match:
        root, month_code, year_str = match.groups()
        year = int(year_str)
        
        # Look up root in database
        if root in FUTURES_DATABASE:
            template = FUTURES_DATABASE[root]
            return FuturesSymbol(
                symbol=clean_symbol.upper(),
                root=root,
                month_code=month_code,
                year=year,
                category=template.category,
                description=template.description
            )
    
    # If no month/year, try to match just the root
    root = clean_symbol.upper()
    if root in FUTURES_DATABASE:
        template = FUTURES_DATABASE[root]
        return FuturesSymbol(
            symbol="",  # Will be filled by front month calculation
            root=root,
            month_code="",  # Will be filled by front month calculation
            year=0,  # Will be filled by front month calculation
            category=template.category,
            description=template.description
        )
    
    return None

def get_front_month_contract(root: str, reference_date: Optional[date] = None) -> Optional[FuturesSymbol]:
    """
    Get the front month contract for a given futures root.
    
    Args:
        root: Futures root symbol (e.g., "ES", "NQ")
        reference_date: Date to calculate from (default: today)
        
    Returns:
        FuturesSymbol for front month contract or None
    """
    if reference_date is None:
        reference_date = datetime.utcnow().date()
    
    if root not in FUTURES_DATABASE:
        return None
    
    template = FUTURES_DATABASE[root]
    
    # For quarterly contracts (ES, NQ, etc.), find next quarterly month
    quarterly_months = [3, 6, 9, 12]  # Mar, Jun, Sep, Dec
    
    current_year = reference_date.year
    current_month = reference_date.month
    
    # Find next quarterly month
    next_quarter_month = None
    next_quarter_year = current_year
    
    for quarter in quarterly_months:
        if quarter >= current_month:
            next_quarter_month = quarter
            break
    
    if next_quarter_month is None:
        next_quarter_month = 3  # March of next year
        next_quarter_year += 1
    
    month_code = MONTH_CODES[next_quarter_month]
    year_suffix = str(next_quarter_year)[-2:]
    full_symbol = f"{root}{month_code}{year_suffix}"
    
    return FuturesSymbol(
        symbol=full_symbol,
        root=root,
        month_code=month_code,
        year=int(year_suffix),
        category=template.category,
        description=template.description
    )

def enhanced_translate_root_to_front_month(symbol: str) -> str:
    """
    Enhanced translation using the new futures symbol system.
    
    Args:
        symbol: Input symbol (e.g., "/ES", "NQ", "ESZ25")
        
    Returns:
        Front month contract symbol (e.g., "ESZ25")
    """
    parsed = parse_futures_symbol(symbol)
    
    if not parsed:
        return symbol  # Return original if not recognized
    
    # If already has month/year, return as is
    if parsed.month_code and parsed.year:
        return parsed.symbol
    
    # Get front month contract
    front_month = get_front_month_contract(parsed.root)
    if front_month:
        return front_month.symbol
    
    return symbol  # Fallback to original

def get_futures_info(symbol: str) -> Optional[FuturesSymbol]:
    """
    Get comprehensive information about a futures symbol.
    
    Args:
        symbol: Futures symbol (e.g., "ESZ25", "/NQ")
        
    Returns:
        FuturesSymbol with complete information or None
    """
    return parse_futures_symbol(symbol)

def list_supported_futures() -> List[str]:
    """Get list of supported futures root symbols."""
    return list(FUTURES_DATABASE.keys())

def get_futures_by_category(category: FuturesCategory) -> List[str]:
    """Get list of futures symbols by category."""
    return [root for root, info in FUTURES_DATABASE.items() 
            if info.category == category]
