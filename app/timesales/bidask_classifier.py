"""Bid/Ask trade classification and aggregation.

Primary path: merge trades with NBBO quotes (nearest within tolerance),
assign label ask/bid/mid using epsilon bands.
Fallback: tick rule labeling when no NBBO available for a trade.
"""
from __future__ import annotations
from typing import Tuple, Optional
import pandas as pd

LabelledDF = pd.DataFrame


def _tick_labels(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame({"label": [], "confidence": []})
    df = df.sort_values("dt_utc").copy()
    prev_price = df["price"].shift(1)
    def decide(idx: int, price: float) -> str:
        pv = prev_price.iloc[idx]
        if pd.isna(pv):
            return "mid"
        if price > pv:
            return "ask"
        if price < pv:
            return "bid"
        return "mid"
    labels = [decide(i, p) for i, p in enumerate(df["price"])]
    return pd.DataFrame({"label": labels, "confidence": ["tick"] * len(labels)}, index=df.index)


def classify_trades(trades: pd.DataFrame, quotes: Optional[pd.DataFrame] = None, *, nbbo_window_ms: int = 1000, price_epsilon: float = 1e-6) -> LabelledDF:
    """Label trades relative to NBBO if quotes provided else tick rule.

    trades columns required: dt_utc, price, size
    quotes columns required (if provided): dt_utc, bid, ask
    """
    if trades is None or trades.empty:
        return trades.copy() if trades is not None else pd.DataFrame()
    t = trades.copy()
    t["dt_utc"] = pd.to_datetime(t["dt_utc"], utc=True)
    if quotes is None or quotes.empty:
        t[["label", "confidence"]] = _tick_labels(t)
        return t
    q = quotes.copy()
    q["dt_utc"] = pd.to_datetime(q["dt_utc"], utc=True)
    q = q.sort_values("dt_utc")[["dt_utc", "bid", "ask"]]
    t = t.sort_values("dt_utc")
    merged = pd.merge_asof(t, q, on="dt_utc", direction="nearest", tolerance=pd.Timedelta(milliseconds=nbbo_window_ms))
    def decide(row) -> Optional[str]:
        b, a, p = row.get("bid"), row.get("ask"), row["price"]
        if pd.isna(b) or pd.isna(a):
            return None
        if p >= a - price_epsilon:
            return "ask"
        if p <= b + price_epsilon:
            return "bid"
        return "mid"
    # apply returns scalar per row here (label string or None)
    merged["label"] = merged.apply(decide, axis=1)  # type: ignore[arg-type]
    merged["confidence"] = merged["label"].apply(lambda v: "nbbo" if v is not None else None)
    missing_mask = merged["label"].isna()
    if missing_mask.any():
        tick_fallback = _tick_labels(merged.loc[missing_mask, ["dt_utc", "price", "size"]])
        merged.loc[missing_mask, ["label", "confidence"]] = tick_fallback.values
    return merged


def percent_at_bid_ask(trades_with_labels: pd.DataFrame, size_col: str = "size") -> Tuple[float, float, float]:
    if trades_with_labels is None or trades_with_labels.empty:
        return 0.0, 0.0, 0.0
    if size_col not in trades_with_labels.columns:
        raise ValueError(f"Missing size column '{size_col}'")
    grouped = trades_with_labels.groupby("label")[size_col].sum(min_count=1)
    total = grouped.sum()
    if not total:
        return 0.0, 0.0, 0.0
    ask = float(grouped.get("ask", 0.0) / total * 100.0)
    bid = float(grouped.get("bid", 0.0) / total * 100.0)
    mid = float(grouped.get("mid", 0.0) / total * 100.0)
    return ask, bid, mid

__all__ = ["classify_trades", "percent_at_bid_ask"]
