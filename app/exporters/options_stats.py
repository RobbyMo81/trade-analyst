from __future__ import annotations
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any

from app.metrics import (
    iv_rank_and_percentile,
    calculate_put_call_volume_ratio,
    calculate_put_call_oi_ratio,
)

def _synthetic_iv_series(days: int = 30) -> pd.Series:
    base = 0.20
    rng = pd.Series(
        [base + 0.02 * ((i % 10) / 10.0) for i in range(days)],
        index=pd.date_range(end=datetime.now(timezone.utc), periods=days, freq="D"),
    )
    return rng

def _synthetic_option_chain() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "option_type": ["call", "call", "put", "put"],
            "volume": [120, 80, 60, 140],
            "open_interest": [1000, 900, 500, 700],
        }
    )

def build_options_stats(cfg: Dict[str, Any], iv_series: pd.Series | None = None, chain: pd.DataFrame | None = None) -> Dict[str, Any]:
    """Compute options metrics (IV rank/percentile & put/call ratios).

    Provide real iv_series (historical implied volatility) and option chain dataframe when available.
    Fallback to synthetic data when absent so exporter wiring is demonstrable.
    """
    window = cfg.get("metrics", {}).get("iv_window_days", 252)
    if iv_series is None:
        iv_series = _synthetic_iv_series(min(window, 30))
    rank, pct = iv_rank_and_percentile(iv_series, window=window)
    if chain is None:
        chain = _synthetic_option_chain()
    vol_pcr = calculate_put_call_volume_ratio(chain)
    oi_pcr = calculate_put_call_oi_ratio(chain)
    return {
        "iv_rank": rank,
        "iv_percentile": pct,
        "put_call_ratio": vol_pcr,
        "oi_put_call_ratio": oi_pcr,
        "series_points": len(iv_series),
    }
