from __future__ import annotations
import pandas as pd
from typing import Tuple

def _tick_labels(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty: 
        return pd.DataFrame({"label":[], "confidence": []})
    df = df.sort_values("dt_utc")
    prev = df["price"].shift(1)
    lbl = df.apply(lambda r: "ask" if (not pd.isna(prev.loc[r.name]) and r["price"]>prev.loc[r.name])
                             else ("bid" if (not pd.isna(prev.loc[r.name]) and r["price"]<prev.loc[r.name]) else "mid"), axis=1)
    return pd.DataFrame({"label": lbl, "confidence": "tick"}).set_index(df.index)

def classify_trades(trades: pd.DataFrame, quotes: pd.DataFrame | None = None, nbbo_window_ms: int = 1000, price_epsilon: float = 1e-6) -> pd.DataFrame:
    t = trades.copy()
    t["dt_utc"] = pd.to_datetime(t["dt_utc"], utc=True)
    if quotes is None or quotes.empty:
        t[["label","confidence"]] = _tick_labels(t)
        return t
    q = quotes.copy()
    q["dt_utc"] = pd.to_datetime(q["dt_utc"], utc=True)
    q = q.sort_values("dt_utc")[["dt_utc","bid","ask"]]
    t = t.sort_values("dt_utc")
    merged = pd.merge_asof(t, q, on="dt_utc", direction="nearest", tolerance=pd.Timedelta(milliseconds=nbbo_window_ms))
    def _lab(row):
        if pd.isna(row.get("bid")) or pd.isna(row.get("ask")):
            return None
        p = float(row["price"]); b=float(row["bid"]); a=float(row["ask"])
        if p >= a - price_epsilon: return "ask"
        if p <= b + price_epsilon: return "bid"
        return "mid"
    merged["label"] = merged.apply(_lab, axis=1)
    merged["confidence"] = merged["label"].apply(lambda x: "nbbo" if x else None)
    missing = merged["label"].isna()
    if missing.any():
        merged.loc[missing, ["label","confidence"]] = _tick_labels(merged.loc[missing])
    return merged

def percent_at_bid_ask(trades_with_labels: pd.DataFrame, size_col: str = "size") -> Tuple[float, float, float]:
    sizes = trades_with_labels.groupby("label")[size_col].sum(min_count=1)
    total = sizes.sum()
    if not total or total == 0:
        return 0.0, 0.0, 0.0
    ask = float((sizes.get("ask", 0.0) / total) * 100.0)
    bid = float((sizes.get("bid", 0.0) / total) * 100.0)
    mid = float((sizes.get("mid", 0.0) / total) * 100.0)
    return ask, bid, mid
