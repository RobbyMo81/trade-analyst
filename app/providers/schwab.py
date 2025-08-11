"""Schwab API client abstraction.

Currently a minimal skeleton that will evolve to perform real HTTP calls.
Uses AuthManager for token retrieval. Methods return structured dicts to
facilitate downstream normalization and testing.
"""
from __future__ import annotations
from typing import Any, Dict, Optional, List
from datetime import datetime  # retained only if needed elsewhere; timestamp creation now via timeutils helpers
import aiohttp
import logging
import asyncio
from app.config import Config
from app.auth import AuthManager
from app.utils.timeutils import now_utc, to_rfc3339
from app.common.exceptions import MissingAccessTokenError

logger = logging.getLogger(__name__)

class SchwabClient:
    def __init__(self, config: Config, auth: AuthManager, provider: str = "default"):
        self.config = config
        self.auth = auth
        self.provider = provider
        self.api_cfg = config.get_api_config(provider) or {}
        self.base_url = getattr(self.api_cfg, 'base_url', '') or config.get('auth.base_url', '')

    def _timestamp(self) -> str:
        """RFC3339 UTC timestamp with millisecond precision."""
        return to_rfc3339(now_utc(), milliseconds=True)

    async def _headers(self) -> Dict[str, str]:
        """Return auth headers or raise MissingAccessTokenError (typed for deterministic tests)."""
        token = await self.auth.get_access_token(self.provider)
        if not token:
            raise MissingAccessTokenError(self.provider, hint="Run auth login or supply mock_access_token fixture.")
        return {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    async def ping(self) -> Dict[str, Any]:
        """Simple readiness check to validate token usability.
        In simulate mode returns a stub response immediately.
        """
        if self.config.get('auth.simulate', True):
            return {"status": "ok", "simulate": True}
        url = f"{self.base_url.rstrip('/')}/ping"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=await self._headers(), timeout=10) as resp:
                    data = await resp.text()
                    return {"status_code": resp.status, "raw": data[:500]}
        except Exception as e:
            logger.error(f"Ping failed: {e}")
            return {"status": "error", "error": str(e)}

    async def quotes(self, symbols: List[str]) -> Dict[str, Any]:
        """Fetch quote snapshots for a list of symbols.

        In simulate mode returns deterministic stub data.
        In live mode attempts a batch endpoint first: GET /quotes?symbols=SYM1,SYM2
        Fallback: per-symbol requests if batch fails (non-200 or exception).

        Returns
        -------
        dict with keys:
          - records: raw provider-shaped dicts (normalized keys)
          - normalized: normalized records (schema-coerced subset)
          - validation: validation summary
          - meta: timing + mode info
        """
        from app.schemas.quotes import normalize_quote_data, validate_quote_data  # local import to avoid cycles
        start = asyncio.get_event_loop().time()
        simulate = self.config.get('auth.simulate', True)
        records: List[Dict[str, Any]] = []
        ts = self._timestamp()
        if not symbols:
            validation = validate_quote_data([])
            return {'records': [], 'normalized': [], 'validation': validation, 'meta': {'mode': 'simulate' if simulate else 'live_empty'}, 'ts': ts}

        if simulate:
            for sym in symbols:
                bid = 100.0
                ask = 100.05
                records.append({'symbol': sym.upper(), 'bid': bid, 'ask': ask, 'bid_size': 100, 'ask_size': 200, 'timestamp': ts})
        else:
            try:
                headers = await self._headers()
            except MissingAccessTokenError as e:
                # Deterministic structure for tests when auth precondition unmet
                validation = {'is_valid': False, 'reason': str(e)}
                return {'records': [], 'normalized': [], 'validation': validation, 'meta': {'mode': 'live_missing_token'}, 'ts': ts}
            await self._fetch_live_quotes(symbols, records, ts, headers)
        normalized = normalize_quote_data(records)
        validation = validate_quote_data(normalized)
        duration = asyncio.get_event_loop().time() - start
        return {'records': records, 'normalized': normalized, 'validation': validation, 'meta': {'duration_s': round(duration, 4), 'mode': 'simulate' if simulate else 'live'}, 'ts': ts}

    async def _fetch_live_quotes(self, symbols: List[str], out_records: List[Dict[str, Any]], ts: str, headers: Dict[str, str]):
        """Internal: live quote fetch with batch + fallback and retries.

        Populates out_records in place.
        Applies simple exponential backoff on network errors.
        """
        if not self.base_url:
            logger.error("Base URL not configured; cannot fetch live quotes")
            return
        max_attempts = int(self.config.get('retries.max_attempts', 3))
        initial_wait = float(self.config.get('retries.initial_seconds', 1))
        max_wait = float(self.config.get('retries.max_seconds', 10))
        batch_url = f"{self.base_url.rstrip('/')}/quotes"
        symbol_param = ','.join([s.upper() for s in symbols])
        params = {'symbols': symbol_param}
        attempt = 0
        async with aiohttp.ClientSession() as session:
            # Try batch first
            while attempt < max_attempts:
                try:
                    async with session.get(batch_url, headers=headers, params=params, timeout=10) as resp:
                        if resp.status == 200:
                            payload = await resp.json()
                            # Expect payload like {'quotes':[{'symbol':'AAPL','bid':...}]}
                            quotes = payload.get('quotes') or payload.get('data') or []
                            if isinstance(quotes, dict):  # some APIs return symbol keyed dict
                                # flatten to list
                                quotes = [v | {'symbol': k} for k, v in quotes.items()]
                            for q in quotes:
                                out_records.append(self._coerce_quote_dict(q, ts))
                            if out_records:
                                return
                        else:
                            logger.warning(f"Batch quotes status {resp.status}; falling back after attempt {attempt+1}")
                            break  # non-200; fallback to per-symbol
                except Exception as e:
                    logger.warning(f"Batch quotes attempt {attempt+1} failed: {e}")
                attempt += 1
                if attempt < max_attempts:
                    wait = min(max_wait, initial_wait * (2 ** (attempt - 1)))
                    await asyncio.sleep(wait)
            # Fallback per-symbol
            for sym in symbols:
                per_url = f"{self.base_url.rstrip('/')}/quotes/{sym.upper()}"
                attempt_s = 0
                while attempt_s < max_attempts:
                    try:
                        async with session.get(per_url, headers=headers, timeout=10) as resp:
                            if resp.status == 200:
                                payload = await resp.json()
                                out_records.append(self._coerce_quote_dict(payload | {'symbol': sym.upper()}, ts))
                                break
                            else:
                                logger.warning(f"Quote {sym} status {resp.status}")
                                break  # non-200 no retry for status errors except maybe 5xx
                    except Exception as se:
                        logger.warning(f"Quote {sym} attempt {attempt_s+1} error: {se}")
                        attempt_s += 1
                        if attempt_s < max_attempts:
                            wait = min(max_wait, initial_wait * (2 ** (attempt_s - 1)))
                            await asyncio.sleep(wait)

    def _coerce_quote_dict(self, payload: Dict[str, Any], ts: str) -> Dict[str, Any]:
        """Map provider payload keys to internal schema keys; fill timestamp if absent."""
        try:
            symbol = (payload.get('symbol') or '').upper()
            bid = payload.get('bid') or payload.get('bidPrice') or payload.get('bestBid')
            ask = payload.get('ask') or payload.get('askPrice') or payload.get('bestAsk')
            bid_sz = payload.get('bid_size') or payload.get('bidSize') or payload.get('bid_size_lot')
            ask_sz = payload.get('ask_size') or payload.get('askSize') or payload.get('ask_size_lot')
            timestamp = payload.get('timestamp') or payload.get('time') or ts
            return {
                'symbol': symbol,
                'bid': bid,
                'ask': ask,
                'bid_size': bid_sz,
                'ask_size': ask_sz,
                'timestamp': timestamp
            }
        except Exception as e:
            logger.error(f"Failed to coerce quote payload: {e}")
            return {}
