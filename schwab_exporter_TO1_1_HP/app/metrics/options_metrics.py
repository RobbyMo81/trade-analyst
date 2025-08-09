from __future__ import annotations
import pandas as pd
from typing import Optional, Tuple

def iv_rank_and_percentile(iv_series: pd.Series, window: int = 252):
    s = pd.to_numeric(iv_series.dropna(), errors="coerce")
    if len(s) < 2:
        return None, None
    s = s.iloc[-window:] if len(s) > window else s
    iv_last = s.iloc[-1]
    iv_min, iv_max = float(s.min()), float(s.max())
    rank = None if iv_max == iv_min else 100.0 * (iv_last - iv_min) / (iv_max - iv_min)
    pct = 100.0 * (s.le(iv_last).sum()) / len(s)
    return (float(rank) if rank is not None else None, float(pct))

def calculate_put_call_volume_ratio(df: pd.DataFrame, type_col: str = "option_type", vol_col: str = "volume"):
    if df.empty or type_col not in df.columns or vol_col not in df.columns:
        return None
    calls = pd.to_numeric(df.loc[df[type_col].str.lower()=="call", vol_col], errors="coerce").sum()
    puts  = pd.to_numeric(df.loc[df[type_col].str.lower()=="put",  vol_col], errors="coerce").sum()
    return float(puts / calls) if calls else None

def calculate_put_call_oi_ratio(df: pd.DataFrame, type_col: str = "option_type", oi_col: str = "open_interest"):
    if df.empty or type_col not in df.columns or oi_col not in df.columns:
        return None
    calls = pd.to_numeric(df.loc[df[type_col].str.lower()=="call", oi_col], errors="coerce").sum()
    puts  = pd.to_numeric(df.loc[df[type_col].str.lower()=="put",  oi_col], errors="coerce").sum()
    return float(puts / calls) if calls else None
