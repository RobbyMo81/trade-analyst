# Metrics Reference

Authoritative specification for calculated metrics, classification logic, and edge-case handling.
All inputs are expected to be pre-normalized (uppercase symbols, numeric columns cast, RFC3339 timestamps).

---

## Table of Contents

1. Volatility Metrics
    - 1.1 Implied Volatility (IV) Rank
    - 1.2 Implied Volatility (IV) Percentile
2. Option Flow Ratios
    - 2.1 Put/Call Volume Ratio (PCR Volume)
    - 2.2 Put/Call Open Interest Ratio (PCR OI)
3. Trade Location Metrics
    - 3.1 % Size at Bid / Ask / Mid
    - 3.2 Classification Confidence
4. Supporting Classifiers
    - 4.1 NBBO Alignment Classifier
    - 4.2 Tick Rule Fallback
5. Rolling History Management (IV Windows)
6. Error & Edge Case Semantics
7. Recommended Data Contracts
8. Extension Points
9. Example Pseudocode (IV Rank / Percentile)
10. Testing Guidance
11. Versioning
12. Glossary

---

## 1. Volatility Metrics

Window parameter `N` (default 252 trading sessions unless otherwise configured).

### 1.1 IV Rank

Purpose: Where today’s implied volatility lies within the observed range over the last `N` observations.

Formula:

```text
Let S = {IV_(t-N+1), ..., IV_t}
IV_rank = ((IV_t - min(S)) / (max(S) - min(S))) * 100
```

Return `None` (or NaN) when:

- Fewer than 2 distinct observations
- `max(S) == min(S)` (flat volatility regime)

Recommended rounding: integer or 2 decimal places depending on UI needs.

### 1.2 IV Percentile

Purpose: Percent of observations in the lookback window less than or equal to current.

Formula:

```text
count_le = | { x in S : x <= IV_t } |
IV_percentile = (count_le / |S|) * 100
```

Edge behavior:

- If all observations identical -> 100.0 (inform user distribution is degenerate)
    OR choose 50.0; we adopt 100.0 for “at top of identical set”.
- If window size < 5 you may flag low-confidence (optional metadata).

Both metrics should be computed after filtering obviously bad values
(negative IV, > 10 i.e. >1000%). Reject or drop invalid rows and log count.

---

## 2. Option Flow Ratios

### 2.1 Put/Call Volume Ratio (PCR Volume)

```text
PCR_volume = puts_volume / calls_volume
```

Handling:

- If `calls_volume == 0` and `puts_volume == 0` -> return None.
- If `calls_volume == 0` and `puts_volume > 0` -> return `inf` (or large sentinel) + add validation warning.
- Both inputs must be non-negative integers.

### 2.2 Put/Call Open Interest Ratio (PCR OI)

```text
PCR_oi = puts_oi / calls_oi
```

Same denominator rules as above. Prefer consistent type (float) even when integral.

Optional smoothing: a 5-day EMA to reduce noise; compute only when at least 3 observations exist.

---

## 3. Trade Location Metrics

### 3.1 % Size at Bid / Ask / Mid

Goal: Size‑weighted distribution of executed trades relative to contemporaneous NBBO.

Inputs per trade (normalized):

```text
symbol, timestamp, price, size, (optional) bid, ask
```

Algorithm (NBBO path):

1. For each trade T, find the latest NBBO snapshot with
   `0 <= trade_ts - nbbo_ts <= nbbo_window_ms` (default 500 ms).
   If none: mark `nbbo_missing = True`.
1. Classify:
    - If `price <= bid + price_epsilon` -> BID
    - Else if `price >= ask - price_epsilon` -> ASK
    - Else -> MID
1. Accumulate `size` into `size_at_bid`, `size_at_ask`, `size_mid`.
1. Percentages:

```text
total = size_at_bid + size_at_ask + size_mid
pct_at_bid = size_at_bid / total * 100
... etc.
```

1. If `total == 0` -> all percentages None.

### 3.2 Classification Confidence

Confidence levels indicate reliability of the trade side labeling:

- `nbbo` – ≥ X% (default 80%) of cumulative size classified using valid NBBO context.
- `tick` – 100% tick-rule fallback (no NBBO available).
- `mixed` – some NBBO, some tick-rule (<80% NBBO size share).
Included in metric output: `{ 'confidence': 'nbbo' | 'tick' | 'mixed', 'nbbo_size_ratio': ratio }`.

---

## 4. Supporting Classifiers

### 4.1 NBBO Alignment Classifier

Given ordered trade list and ordered NBBO snapshots:

```python
for trade in trades:
    candidate = last_nbbo_within_window(trade.ts)
    if candidate:
        trade.bid = candidate.bid
        trade.ask = candidate.ask
```

Complexity: O(T + B) with two-pointer sweep.

### 4.2 Tick Rule Fallback

When NBBO missing:

```text
if prev_price is None: label = 'mid'
elif price > prev_price: label = 'ask'
elif price < prev_price: label = 'bid'
else: label = previous_label or 'mid'
```

Prev label stored to break ties on equal prices. Size accumulates into corresponding bucket.

---

## 5. Rolling History Management (IV Windows)

Maintain a per-symbol deque (maxlen = window) for daily IV observations.
Operations:

- `append(iv_value, ts)` after validation.
- On compute request, materialize list and apply formulas.
Persistence Strategy:
- Periodically serialize to `.cache/iv_history/{symbol}.json` (opt-in) containing array of `{ts, iv}`.
- On startup, hydrate deques if files exist; ignore entries older than
    retention horizon (e.g. 400 sessions) to keep store bounded.
Integrity:
- Reject outliers beyond configurable z-score (default disable).

---

## 6. Error & Edge Case Semantics

| Scenario | Metric Output | Notes |
|----------|---------------|-------|
| Flat IV window | IV_rank = None, IV_percentile = 100 | Provide `range=0` flag |
| Zero denominator PCR | None or inf (config) | Emit validation warning |
| Missing all NBBO | confidence = 'tick' | Percentages still computed |
| Mixed NBBO/tick | confidence = 'mixed' | Include ratio |
| No trades | All percentages None | validation.is_valid False |
| Negative or zero prices | Row dropped; count in errors | Pre-filter step |

Validation dictionary pattern:

```text
{
  'is_valid': bool,
  'errors': [str],
  'warnings': [str],
  'meta': {... optional diagnostic ...}
}
```

---

## 7. Recommended Data Contracts

### 7.1 Quotes Input

```json
[{ "symbol": "AAPL", "bid": 150.25, "ask": 150.30, "timestamp": "...Z" }]
```

### 7.2 Trades (Time & Sales)

```json
[{ "symbol": "AAPL", "timestamp": "...Z", "price": 150.27, "size": 100, "exchange": "NASDAQ" }]
```

### 7.3 NBBO Snapshots

```json
[{ "symbol": "AAPL", "timestamp": "...Z", "bid": 150.25, "ask": 150.30 }]
```

All timestamps MUST be RFC3339 with 'Z'. Milliseconds recommended (ms precision reduces collision risk for rapid prints).

---

## 8. Extension Points

| Extension | Why | Outline |
|-----------|-----|---------|
| Historical IV persistence | Cross-session continuity | Pluggable storage backend interface (file, Redis, S3) |
| Advanced volatility stats | Surface distribution shape | Add skewness, kurtosis, realized vs implied spread |
| Microstructure metrics | Deeper order flow insight | Add trade-to-quote ratio, effective spread vs quoted spread |
| Anomaly flags | Alerting | Z-score outlier detection on PCR / IV rank changes |

---

## 9. Example Pseudocode (IV Rank / Percentile)

```python
from collections import deque

window = 252
store = deque(maxlen=window)

def update_iv(iv_value: float):
    if not (0 <= iv_value <= 10):
        return  # invalid
    store.append(iv_value)

def compute_iv_metrics():
    if len(store) < 2:
        return {'iv_rank': None, 'iv_percentile': None, 'count': len(store)}
    xs = list(store)
    lo, hi = min(xs), max(xs)
    last = xs[-1]
    iv_rank = None if hi == lo else (last - lo) / (hi - lo) * 100
    count_le = sum(1 for x in xs if x <= last)
    iv_pct = count_le / len(xs) * 100
    if hi == lo:
        iv_pct = 100.0
    return {'iv_rank': iv_rank, 'iv_percentile': iv_pct, 'count': len(xs), 'range': hi - lo}
```

---

## 10. Testing Guidance

| Test Type | Case |
|-----------|------|
| IV Rank Edge | All values equal -> rank None, percentile 100 |
| IV Percentile | Strictly increasing series -> percentile 100 |
| PCR Denominator | calls_volume = 0, puts_volume > 0 -> inf + warning |
| NBBO vs Tick | Provide trades lacking NBBO entirely -> confidence tick |
| Mixed Confidence | 60% size NBBO, 40% tick -> confidence mixed |
| Timestamp Format | All outputs end with 'Z' and include '.' for ms |

---

## 11. Versioning

Add a `metrics_spec_version` field (e.g., `1.0.0`) in any API payload producing
these metrics. Increment minor when adding fields (backward compatible), major
when changing semantics.

---

## 12. Glossary

| Term | Definition |
|------|------------|
| NBBO | National Best Bid and Offer snapshot at a point in time |
| Tick Rule | Heuristic: trade classification based on price vs previous trade |
| IV | Implied Volatility (annualized) |
| PCR | Put/Call Ratio |

---
End of document.
