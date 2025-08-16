from __future__ import annotations
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from app.timesales import classify_trades, percent_at_bid_ask, aggregate_trade_classification_confidence

def _synthetic_trades() -> pd.DataFrame:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    return pd.DataFrame(
        {
            "dt_utc": [now + timedelta(seconds=i) for i in range(3)],
            "price": [100.0, 100.4, 100.2],
            "size": [10, 15, 20],
        }
    )

def _synthetic_quotes() -> pd.DataFrame:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    return pd.DataFrame(
        {
            "dt_utc": [now + timedelta(seconds=i) for i in range(3)],
            "bid": [99.9, 100.1, 100.05],
            "ask": [100.3, 100.5, 100.35],
        }
    )

def build_timesales_metrics(cfg: Dict[str, Any], trades: pd.DataFrame | None = None, quotes: pd.DataFrame | None = None) -> Dict[str, Any]:
    """Compute % traded at bid/ask/mid and classification confidence.

    Provide real trades & quotes DataFrames when available; synthetic placeholders are used otherwise.
    """
    nbbo_window_ms = cfg.get("timesales", {}).get("nbbo_window_ms", 1000)
    pe = cfg.get("timesales", {}).get("price_epsilon", 1e-6)
    try:
        price_epsilon = float(pe)
    except Exception:
        price_epsilon = 1e-6
    if trades is None:
        trades = _synthetic_trades()
    if quotes is None:
        quotes = _synthetic_quotes()
    labeled = classify_trades(trades, quotes, nbbo_window_ms=nbbo_window_ms, price_epsilon=price_epsilon)
    pct_ask, pct_bid, pct_mid = percent_at_bid_ask(labeled)
    confidence_summary = aggregate_trade_classification_confidence(labeled)
    return {
        "pct_at_ask": pct_ask,
        "pct_at_bid": pct_bid,
        "pct_at_mid": pct_mid,
        "confidence": confidence_summary,
        "trade_count": len(labeled),
    }
