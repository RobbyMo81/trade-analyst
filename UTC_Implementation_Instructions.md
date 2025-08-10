
# Step-by-step Implementation for the schwab_exporter_TO1_1_UTC upgrade.

## 1) Prep & Branch

1. Pull latest `main` and create a feature branch:

   ```bash
   git checkout main && git pull
   git checkout -b feat/utc-unified
   ```
2. Located the package schwab_exporter_TO1_1_UTC found the repo root:

   * `TO1_1_UTC_unified_build`
   * Verify you see `app/utils/timeutils.py`, updated `app/auth.py`, schema files under `app/schemas/…`, and tests under `tests/…`.

## 2) Config merge (keep your rich Config)

1. Open your existing `Config` class/module.
2. Merge in these keys (names are stable—don’t rename):

   * `auth.simulate` (bool)
   * `runtime.token_cache` (default per-env: `.cache/dev/token_cache.json`)
   * `runtime.pkce_state_file`
   * `metrics.iv_window_days`
   * `timesales.nbbo_window_ms`, `timesales.price_epsilon`
3. Keep **exact-match** callback enforcement using `auth.registered_uris` + `env.<name>.redirect_uri`.

## 3) Adopt the UTC utilities

1. Add `app/utils/timeutils.py` to the repo.
2. **Single source of truth** for time:

   * Use `now_utc()` for “current time”.
   * Use `to_rfc3339(dt)` to serialize (ends with `Z`).
   * Use `parse_rfc3339(s)` to parse.
   * For pandas DataFrames, call `ensure_df_utc(df, "dt_utc")`.
3. Ban `datetime.utcnow()` and naive `datetime.now()` in app code. (Tests will enforce.)

## 4) Replace naïve timestamps (surgical edits)

1. **Auth** (`app/auth.py`):

   * Store token times as:

     * `acquired_at`: epoch seconds (int)
     * `acquired_at_utc`: RFC3339 `Z` string
   * Compute expiry with epoch math (tz-safe).
2. **Providers / Snapshots**:

   * Any `datetime.utcnow().isoformat()` → `to_rfc3339(now_utc())`.
3. **Schemas & Writers**:

   * Ensure all time columns are named **`dt_utc`** and coerced:

     ```python
     df["dt_utc"] = pd.to_datetime(df["dt_utc"], utc=True)
     ```
   * Meta timestamps (e.g., `created_at_utc`) should use `to_rfc3339(now_utc())`.

## 5) Time & Sales classifier integration

1. Place `app/timesales/bidask_classifier.py` in your project (or merge changes into your existing module).
2. Primary path: supply quotes (dt\_utc, bid, ask) → NBBO classification.
3. Fallback: no quotes → tick rule classification.
4. Persist `% at ask/bid/mid` and a **confidence** summary (`nbbo`, `tick`, or `mixed`).

## 6) Per-environment token cache

* Default path: `.cache/<env>/token_cache.json`.
* Honor `TOKEN_CACHE_PATH` env var as an override (useful in CI and tests).

## 7) CI pipeline

1. Keep or add `.github/workflows/ci.yml` with:

   ```yaml
   - run: python -m app.main --env dev healthcheck
   - run: pytest -q
   ```
2. For headless CI runs without secrets, set `AUTH_SIMULATE=true`.

## 8) Local verification (dev)

```bash
python -m venv .venv
source .venv/bin/activate     # Windows: .\.venv\Scripts\activate
pip install -r requirements.txt

# Callback exact-match sanity
python -m app.main --env dev healthcheck

# Run tests (includes UTC invariants)
pytest -q

# OAuth smoke (simulate mode default ON)
python -m app.main auth-smoke
cat .cache/dev/token_cache.json
# Expect: keys 'access_token', 'expires_in', 'token_type', 'acquired_at', 'acquired_at_utc' (ends with 'Z')
```

## 9) Rollout of real OAuth (later)

* Flip `auth.simulate=false` (or `AUTH_SIMULATE=false` env).
* Provide `CLIENT_ID` and `CLIENT_SECRET` securely (local `.env` or GitHub Actions Secrets).
* Ensure **HTTPS** callback and **exact** redirect URI match.

---

# Additional Information & Guardrails

## What the tests enforce (acceptance)

* **No** `datetime.utcnow()` anywhere under `app/`.
* RFC3339 `Z` round-trip parsing works.
* Token cache includes both epoch and RFC3339 UTC.
* Healthcheck fails if redirect is not an **exact** allowlist match.

## Grep to double-check locally

```bash
grep -R "datetime.utcnow(" -n app || true
grep -R "datetime.now(" -n app | grep -v "timezone.utc" || true
```

Both commands should return **no offenders** after the refactor.

## Naming & schema tips

* Canonical time column: **`dt_utc`**.
* Options metrics columns (approved):

  * `iv_rank`, `iv_percentile`, `put_call_ratio`, `oi_put_call_ratio`
* Time & Sales summary:

  * `pct_traded_ask`, `pct_traded_bid`, `pct_traded_mid`, plus `trade_classification_confidence`.

## Backward compatibility (data at rest)

* If older Parquet files have naive timestamps, do **not** mutate them in place.
* Add a lightweight one-off migration script if needed to re-write archival data with UTC tz; otherwise, only **new** outputs need to be UTC-clean.

## Common pitfalls (and fixes)

* **“Token expired immediately”** → system clock skew; epoch math prevents tz bugs, but verify host time.
* **“Merge\_asof misaligned”** → quotes/trades timestamps weren’t UTC-coerced; call `ensure_df_utc` on both.
* **“Healthcheck failing”** → redirect mismatch; scheme/host/port/path must match exactly.

---

# Suggested commit plan

1. `feat(utc): add timeutils and enforce RFC3339Z; ban naive datetimes`
2. `feat(auth): epoch+RFC3339 token timestamps; per-env token cache`
3. `feat(timesales): nbbo+tick classifier; utc coercion`
4. `chore(ci): run healthcheck and tests; simulate auth in CI`
5. `test(utc): invariants and auth token math`
6. `docs: update configuration and rollout notes`

---

## End of Instructions ##