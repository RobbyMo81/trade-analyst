"""Options metrics calculations: IV rank/percentile and Put/Call ratios.

All functions are pure and accept pre-cleaned pandas objects. They perform
light validation and return numeric results (or None when undefined).
"""
from __future__ import annotations
from typing import Tuple, Optional
import pandas as pd

Number = Optional[float]


def iv_rank_and_percentile(iv_series: pd.Series, window: int = 252) -> Tuple[Number, Number]:
    """Compute IV Rank and IV Percentile over a rolling window.

    Args:
        iv_series: Series of implied volatility values (float). Can contain NaNs.
        window: Max lookback length (truncate to last *window* points if longer).
    Returns:
        (iv_rank, iv_percentile) each in 0..100 or None when undefined.
    Rules:
        - Less than 2 usable points => (None, None)
        - Flat window (max == min) => iv_rank None, percentile still computed.
        - Percentile definition: proportion of values <= last * 100.
    """
    if iv_series is None:
        return None, None
    s = pd.to_numeric(iv_series.dropna(), errors="coerce")
    if len(s) < 2:
        return None, None
    if len(s) > window:
        s = s.iloc[-window:]
    last = s.iloc[-1]
    mn, mx = float(s.min()), float(s.max())
    rank = None if mx == mn else 100.0 * (last - mn) / (mx - mn)
    pct = 100.0 * (s.le(last).sum()) / len(s)
    return (float(rank) if rank is not None else None, float(pct))


def _pcr(df: pd.DataFrame, type_col: str, value_col: str) -> Number:
    if df is None or df.empty:
        return None
    missing = [c for c in (type_col, value_col) if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns for PCR: {missing}")
    calls = pd.to_numeric(df.loc[df[type_col].str.lower() == "call", value_col], errors="coerce").sum()
    puts = pd.to_numeric(df.loc[df[type_col].str.lower() == "put", value_col], errors="coerce").sum()
    if calls == 0:
        return None
    return float(puts / calls)


def calculate_put_call_volume_ratio(df: pd.DataFrame, type_col: str = "option_type", vol_col: str = "volume") -> Number:
    """Classic put/call volume ratio (puts divided by calls)."""
    return _pcr(df, type_col, vol_col)


def calculate_put_call_oi_ratio(df: pd.DataFrame, type_col: str = "option_type", oi_col: str = "open_interest") -> Number:
    """Put/Call open interest ratio (puts divided by calls)."""
    return _pcr(df, type_col, oi_col)

__all__ = [
    "iv_rank_and_percentile",
    "calculate_put_call_volume_ratio",
    "calculate_put_call_oi_ratio",
]
