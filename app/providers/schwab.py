"""Schwab API client abstraction.

Currently a minimal skeleton that will evolve to perform real HTTP calls.
Uses AuthManager for token retrieval. Methods return structured dicts to
facilitate downstream normalization and testing.
"""
from __future__ import annotations
from typing import Any, Dict, Optional, List
from datetime import datetime
import aiohttp
import logging
from app.config import Config
from app.auth import AuthManager

logger = logging.getLogger(__name__)

class SchwabClient:
    def __init__(self, config: Config, auth: AuthManager, provider: str = "default"):
        self.config = config
        self.auth = auth
        self.provider = provider
        self.api_cfg = config.get_api_config(provider) or {}
        self.base_url = getattr(self.api_cfg, 'base_url', '') or config.get('auth.base_url', '')

    async def _headers(self) -> Dict[str, str]:
        token = await self.auth.get_access_token(self.provider)
        if not token:
            raise RuntimeError("No access token available; ensure login flow completed")
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

        Returns a structure with raw (provider) data, normalized records, validation summary.
        In simulate mode returns deterministic stub data suitable for tests.
        """
        from app.schemas.quotes import normalize_quote_data, validate_quote_data  # local import to avoid cycles
        simulate = self.config.get('auth.simulate', True)
        records: List[Dict[str, Any]] = []
        ts = datetime.utcnow().isoformat()
        if simulate:
            for sym in symbols:
                # Simple synthetic bid/ask spread
                bid = 100.0
                ask = 100.05
                records.append({
                    'symbol': sym.upper(),
                    'bid': bid,
                    'ask': ask,
                    'bid_size': 100,
                    'ask_size': 200,
                    'timestamp': ts
                })
        else:  # Real call placeholder; one request per symbol for now
            if not symbols:
                return {'records': [], 'normalized': [], 'validation': validate_quote_data([])}
            try:
                async with aiohttp.ClientSession() as session:
                    for sym in symbols:
                        url = f"{self.base_url.rstrip('/')}/quotes/{sym}"  # placeholder path
                        try:
                            async with session.get(url, headers=await self._headers(), timeout=10) as resp:
                                if resp.status == 200:
                                    payload = await resp.json()
                                    # Assume provider returns fields: bid, ask, sizes optional
                                    records.append({
                                        'symbol': sym.upper(),
                                        'bid': payload.get('bid'),
                                        'ask': payload.get('ask'),
                                        'bid_size': payload.get('bidSize'),
                                        'ask_size': payload.get('askSize'),
                                        'timestamp': payload.get('timestamp') or ts
                                    })
                                else:
                                    logger.warning(f"Quote fetch {sym} status {resp.status}")
                        except Exception as se:
                            logger.error(f"Quote fetch failed for {sym}: {se}")
            except Exception as outer:
                logger.error(f"Quotes session failure: {outer}")
        normalized = normalize_quote_data(records)
        validation = validate_quote_data(normalized)
        return {'records': records, 'normalized': normalized, 'validation': validation}
