from datetime import datetime, date, timedelta
from .exchange_calendar import get_contract_expiry_date

# Futures month codes
_MONTH_CODES = {
    1: 'F', 2: 'G', 3: 'H', 4: 'J', 5: 'K', 6: 'M',
    7: 'N', 8: 'Q', 9: 'U', 10: 'V', 11: 'X', 12: 'Z'
}


def _third_friday(year: int, month: int) -> date:
    """Return the date of the third Friday for the given year/month.
    
    DEPRECATED: Use exchange_calendar.get_contract_expiry_date instead
    for proper holiday-aware expiry calculation.
    """
    d = date(year, month, 1)
    # weekday(): Monday=0 .. Sunday=6 ; Friday=4
    first_friday_delta = (4 - d.weekday() + 7) % 7
    first_friday = d + timedelta(days=first_friday_delta)
    third_friday = first_friday + timedelta(days=14)
    return third_friday


def _nearest_quarterly_contract(root: str, lookahead_months: int = 18) -> str:
    """Pick the nearest quarterly contract (Mar/Jun/Sep/Dec) whose expiry is after now.

    Look ahead up to `lookahead_months` months to find the earliest expiry.
    Uses exchange calendar for accurate expiry dates including holiday adjustments.
    Returns contract code like 'ESU25'.
    """
    now = datetime.utcnow().date()
    quarters = {3, 6, 9, 12}
    candidates = []
    # iterate months starting from current month up to lookahead
    year = now.year
    month = now.month
    for i in range(0, lookahead_months):
        m = ((month - 1 + i) % 12) + 1
        y = year + ((month - 1 + i) // 12)
        if m in quarters:
            # Use exchange calendar for accurate expiry date
            exp = get_contract_expiry_date(root, y, m)
            if exp >= now:
                candidates.append((exp, y, m))
    if not candidates:
        # fallback: choose next year's Mar
        y = now.year + 1
        m = 3
        exp = get_contract_expiry_date(root, y, m)
        candidates.append((exp, y, m))
    # pick earliest expiry
    candidates.sort(key=lambda t: t[0])
    _, y, m = candidates[0]
    code = _MONTH_CODES[m]
    yy = str(y)[-2:]
    return f"{root}{code}{yy}"


def translate_root_to_front_month(symbol: str) -> str:
    """Translate root futures (e.g., 'ES', 'NQ', '/NQ', '/ES') to a front-month contract code using nearest quarterly expiry.

    If symbol isn't a recognized root, return it unchanged.
    Handles symbols with or without leading forward slash (common in trading platforms).
    """
    if not symbol:
        return symbol
    
    # Strip leading forward slash if present (common in trading platforms)
    clean_symbol = symbol.lstrip('/')
    
    if not clean_symbol or not clean_symbol.isalpha():
        return symbol
    
    root = clean_symbol.upper()
    # Currently support common E-mini roots; extend as needed
    if root not in ("ES", "NQ"):
        return symbol  # Return original if not recognized
    
    try:
        return _nearest_quarterly_contract(root)
    except Exception:
        # fallback to simple heuristic using exchange calendar
        now = datetime.utcnow()
        year = now.year
        month = now.month
        for q in (3, 6, 9, 12):
            if q >= month:
                m = q
                break
        else:
            m = 3
            year += 1
        
        # Use exchange calendar for accurate expiry
        try:
            exp_date = get_contract_expiry_date(root, year, m)
            # If expiry has passed, move to next quarter
            if exp_date < now.date():
                if m == 12:
                    m = 3
                    year += 1
                else:
                    quarters = [3, 6, 9, 12]
                    next_idx = quarters.index(m) + 1
                    if next_idx < len(quarters):
                        m = quarters[next_idx]
                    else:
                        m = 3
                        year += 1
        except Exception:
            pass  # Use the calculated m and year
        
        code = _MONTH_CODES[m]
        yy = str(year)[-2:]
        return f"{root}{code}{yy}"
