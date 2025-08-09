# Implementation Guidelines (Step-by-Step)

## 0) Prereqs

* **Python:** 3.12
* **OS packages:** git, OpenSSL (if you’ll use local HTTPS certs)
* **Artifacts:** The latest **TO1\_1\_high\_priority\_fixes** (contains CI, metrics, classifiers, smoke tests)

---

## 1) Initialize / Update the Repo

1. Create a clean feature branch, e.g. `feat/to1.1-hp`.
2. find `TO1_1_high_priority_fixes directory` in the repo root. You should see:

   ```
   app/
     metrics/
       options_metrics.py
     timesales/
       bidask_classifier.py
     utils/
       validators.py
     ...
   tests/
     test_options_metrics.py
     test_timesales_bidask.py
     test_oauth_smoke.py
     test_callbacks_hygiene.py
   .github/workflows/ci.yml
   config.toml
   requirements.txt
   start.py
   ```
3. Create a virtual env & install:

   ```bash
   python -m venv .venv
   source .venv/bin/activate          # Windows: .\.venv\Scripts\activate
   pip install -r requirements.txt
   ```

---

## 2) Wire Config (dev-safe defaults first)

Open `config.toml` and verify these blocks:

```toml
[auth]
authorize_url = "https://api.schwabapi.com/v1/oauth/authorize"
token_url     = "https://api.schwabapi.com/v1/oauth/token"
client_type   = "confidential"
client_auth_method = "basic"
scope         = "quotes.read historical.read options.read timesales.read"
pkce          = true
pkce_method   = "S256"
simulate      = true   # keep true for CI & local smoke without real creds

registered_uris = [
  "https://127.0.0.1:5000/oauth2/callback",
  "https://127.0.0.1:3000/auth/redirect",
  "https://127.0.0.1:8443/auth/redirect"
]

[env.dev]
redirect_uri = "https://127.0.0.1:5000/oauth2/callback"
host = "127.0.0.1"
port = 5000

[runtime]
token_cache = "token_cache.json"
pkce_state_file = "pkce_state.json"

[metrics]
iv_window_days = 252   # default rolling window

[timesales]
nbbo_window_ms = 1000  # tolerance for merge_asof
price_epsilon  = 1e-6  # boundary for <=bid / >=ask
```

> You can flip `simulate=false` only when you’re ready to do a real OAuth round-trip with secrets configured.

---

## 3) CI/CD Workflow (GitHub Actions)

The zip already includes `.github/workflows/ci.yml`. Confirm it’s present:

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: "3.12"
- run: |
    python -m pip install --upgrade pip
    pip install -r requirements.txt
- run: python -m app.main --env dev healthcheck
- run: pytest -q || true
```

Commit & push your branch to ensure the pipeline runs.

> Later, remove `|| true` once the suite is fully stable so CI fails on test regressions.

---

## 4) Metrics: IV Rank & Percentile, PCR (Volume & OI)

### What’s already implemented

* `app/metrics/options_metrics.py`

  * `iv_rank_and_percentile(series, window=252)`
  * `calculate_put_call_volume_ratio(df)`
  * `calculate_put_call_oi_ratio(df)`

### How to integrate

* If you currently produce an options chain DataFrame, call:

  ```python
  from app.metrics.options_metrics import (
      iv_rank_and_percentile,
      calculate_put_call_volume_ratio,
      calculate_put_call_oi_ratio
  )

  # Example
  rank, pct = iv_rank_and_percentile(iv30_series, window=cfg["metrics"]["iv_window_days"])
  vol_pcr   = calculate_put_call_volume_ratio(chain_df)        # expects option_type, volume
  oi_pcr    = calculate_put_call_oi_ratio(chain_df)            # expects option_type, open_interest
  ```

* **Schema wiring:** Map these outputs into your Options Stats parquet as:

  * `iv_rank` (rank), `iv_percentile` (pct)
  * `put_call_ratio` (use **volume PCR** for session stats)
  * Optionally add `oi_put_call_ratio` for end-of-day summary downstream.

* **Edge cases:**

  * Flat window → `iv_rank=None`
  * Insufficient history (<2 points) → `(None, None)`

---

## 5) Time & Sales: % Traded at Bid / Ask

### What’s already implemented

* `app/timesales/bidask_classifier.py`

  * `classify_trades(trades, quotes=None, nbbo_window_ms, price_epsilon)`
  * `percent_at_bid_ask(labeled_trades, size_col="size")`

### How to integrate

* **Primary NBBO path:** if you can supply a quotes DataFrame (`dt_utc`, `bid`, `ask`):

  ```python
  from app.timesales.bidask_classifier import classify_trades, percent_at_bid_ask

  labeled = classify_trades(trades_df, quotes_df,
                            nbbo_window_ms=cfg["timesales"]["nbbo_window_ms"],
                            price_epsilon=cfg["timesales"]["price_epsilon"])
  pct_ask, pct_bid, pct_mid = percent_at_bid_ask(labeled)
  ```

* **Fallback (no quotes available):** pass `quotes=None`. The tick rule is used and confidence is labeled `"tick"`.

* **Persist confidence:** Consider adding `confidence` to your output for transparency (`"nbbo"` or `"tick"`).

---

## 6) OAuth Round-Trip Smoke (CI-friendly)

### Simulated mode (default)

* Runs without real credentials; writes a shape-correct `token_cache.json`.
* Command:

  ```bash
  python -m app.main auth-smoke
  ```
* CI can run this safely with `auth.simulate=true`.

### Real round-trip (when you’re ready)

1. Set `auth.simulate=false` in `config.toml` (or `AUTH_SIMULATE=false` env).
2. Set secrets locally or in CI:

   * `CLIENT_ID`, `CLIENT_SECRET`
3. Ensure your listener is **HTTPS** and the **redirect URI is an exact match** to one of `registered_uris`.

   * If you’re using the earlier TO1.1 TLS server, set `ssl.mode=adhoc` or provide `certfile/keyfile`, then run `auth-login`.
   * If your current app doesn’t enable HTTPS, terminate TLS with a local proxy (e.g., Caddy/Nginx) and forward to Flask.
4. Launch:

   ```bash
   python -m app.main --env dev auth-login
   ```

   or headless:

   ```bash
   python -m app.main --env dev auth-login --no-browser
   ```
5. Verify `token_cache.json` contains `access_token`, `expires_in`, and (if provided) `refresh_token`.

> **Exact match reminder:** scheme, host, port, and path must be identical to the portal entry.

---

## 7) Callback Hygiene (Allowlist + Tests)

* Registered URIs live in `config.toml` → `[auth].registered_uris`.
* **Do not** loosen to regex for allow; you may add a **lint-only** regex to warn on typos if you’d like.
* Tests included: `tests/test_callbacks_hygiene.py` (3 positives; scheme/path negatives).
  Run:

  ```bash
  pytest -q
  ```

---

## 8) Hooking the Metrics into Your Exporters

When your Schwab fetchers (e.g., `options.py`, `timesales.py`) are live:

1. **Options Stats Exporter**

   * After building a chain DF: compute `iv_rank`, `iv_percentile`, `put_call_ratio`, `oi_put_call_ratio` (optional).
   * Store as part of the Options Stats parquet + `.meta.json`.

2. **Time & Sales Exporter**

   * After collecting trades: optionally join with quotes for NBBO.
   * Compute `% at ask/bid/mid` and persist either:

     * aggregated metrics in Options Stats, and/or
     * per-trade labels in a richer timesales parquet.

3. **Idempotence**

   * Continue using the existing write helper (hash-based meta) to avoid duplicate rows.

---

## 9) GitHub Actions Secrets (for real OAuth later)

Add to your repo’s **Settings → Secrets and variables → Actions**:

* `SCHWAB_CLIENT_ID`
* `SCHWAB_CLIENT_SECRET`
* optionally `AUTH_SIMULATE=false` when you want CI to do a real token exchange (you’ll also need a way to complete the consent step at least once and preserve a refresh token).

Update the workflow step to export them if doing a real run:

```yaml
env:
  CLIENT_ID: ${{ secrets.SCHWAB_CLIENT_ID }}
  CLIENT_SECRET: ${{ secrets.SCHWAB_CLIENT_SECRET }}
  AUTH_SIMULATE: "false"
```

---

## 10) Acceptance Gates (what “done” looks like)

1. **CI workflow present and green** (healthcheck + pytest).
2. **IV Rank/Percentile** computed and unit-tested.
3. **PCR (Volume & OI)** computed and unit-tested.
4. **% at Bid/Ask** computed (NBBO primary; tick fallback) with confidence flag + tests.
5. **OAuth smoke** passing in simulate mode; real mode available when secrets + HTTPS are in place.
6. **Callback tests** prove strict **exact-match** allowlist.

---

## 11) Troubleshooting Cheatsheet

* **“Zip doesn’t run”**: verify you installed from `requirements.txt` and run commands **inside** the venv.
* **IV rank = None**: window is flat (max==min) or too short. Confirm at least 2 points in the series.
* **PCR is None**: your input DF likely missing `option_type`, `volume` or `open_interest`. Confirm column names.
* **Bid/Ask % all zeros**: check `size` column is numeric; ensure labels exist (`ask/bid/mid`) after classification.
* **Healthcheck fails**: `redirect_uri` is not an **exact** member of `registered_uris` or format invalid.
* **OAuth (real) fails**: confirm **HTTPS** listener; confirm portal **exact** URI; confirm PKCE/secret alignment for **confidential + PKCE**.

---

## Optional: Re-enable Local HTTPS in the App (if you’re using our earlier TLS variant)

If your current branch lacks HTTPS serving but you want to terminate TLS in-process (dev only):

* Add an `_ssl_context()` helper (adhoc or certfile) and pass `ssl_context=_ssl_context(cfg)` to `app.run(...)`.
* Otherwise, terminate TLS with a local reverse proxy and keep Flask on HTTP loopback.

---

## Commit Plan (suggested)

1. `feat(ci): add GitHub Actions workflow & healthcheck`
2. `feat(metrics): IV rank/percentile + PCR utilities`
3. `feat(timesales): bid/ask classifier (nbbo + tick) + percentages`
4. `feat(auth): OAuth smoke (simulate mode)`
5. `test: add tests for metrics, bid/ask, oauth smoke, callbacks hygiene`
6. `docs: update README and config notes`

---

