"""Schwab API client abstraction.

Currently a minimal skeleton that will evolve to perform real HTTP calls.
Uses AuthManager for token retrieval. Methods return structured dicts to
facilitate downstream normalization and testing.
"""
from __future__ import annotations
from typing import Any, Dict, Optional, List, Union
from datetime import datetime, date
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
        # Prefer provider marketdata base override, then api_cfg.base_url, then legacy auth.base_url
        md_base = ''
        try:
            md_base = self.config.get_schwab_market_base()
        except Exception:
            md_base = ''
        fallback_base = getattr(self.api_cfg, 'base_url', '') or config.get('auth.base_url', '')
        self.base_url = (md_base or fallback_base or '').rstrip('/')

    def _join(self, path: str) -> str:
        base = (self.base_url or '').rstrip('/')
        p = (path or '').lstrip('/')
        return f"{base}/{p}" if base else f"/{p}"

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
        url = self._join('/ping')
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=await self._headers(), timeout=aiohttp.ClientTimeout(total=10)) as resp:
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
        batch_url = self._join('/quotes')
        symbol_param = ','.join([s.upper() for s in symbols])
        params = {'symbols': symbol_param}
        attempt = 0
        async with aiohttp.ClientSession() as session:
            # Try batch first
            while attempt < max_attempts:
                try:
                    async with session.get(batch_url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
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
                # Use batch endpoint with single-symbol param instead of unsupported /quotes/{symbol}
                attempt_s = 0
                while attempt_s < max_attempts:
                    try:
                        params_single = {'symbols': sym.upper()}
                        async with session.get(batch_url, headers=headers, params=params_single, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                            if resp.status == 200:
                                payload = await resp.json()
                                # Normalize payload to a list of quote dicts
                                quotes = payload.get('quotes') or payload.get('data') or []
                                if isinstance(quotes, dict):
                                    quotes = [v | {'symbol': k} for k, v in quotes.items()]
                                # If still empty, try top-level symbol-keyed responses
                                if not quotes and isinstance(payload, dict):
                                    for k, v in payload.items():
                                        # only accept dict-valued entries that look like quotes
                                        if not isinstance(v, dict):
                                            continue
                                        # accept if key matches requested symbol or value contains numeric price fields
                                        if k.upper() == sym.upper() or any(field in v for field in ('bid', 'bidPrice', 'lastPrice', 'ask', 'askPrice')):
                                            quotes.append(v | {'symbol': k})
                                for q in quotes:
                                    out_records.append(self._coerce_quote_dict(q, ts))
                                if out_records:
                                    break
                                # no records, treat as non-200-ish for fallback logic
                                logger.warning(f"Quote {sym} status {resp.status} (no quotes found)")
                                break
                            else:
                                logger.warning(f"Quote {sym} status {resp.status}")
                                break
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
            # Try several common locations for bid/ask across provider responses
            bid = (payload.get('bid') or payload.get('bidPrice') or payload.get('bestBid'))
            ask = (payload.get('ask') or payload.get('askPrice') or payload.get('bestAsk'))
            # Nested shapes (Schwab often uses 'extended' or 'quote' sections)
            if not bid:
                ext = payload.get('extended') or {}
                q = payload.get('quote') or {}
                bid = ext.get('bidPrice') or ext.get('bid') or q.get('bidPrice') or q.get('lastPrice')
            if not ask:
                ext = payload.get('extended') or {}
                q = payload.get('quote') or {}
                ask = ext.get('askPrice') or ext.get('ask') or q.get('askPrice') or q.get('lastPrice')

            # Sizes
            bid_sz = (payload.get('bid_size') or payload.get('bidSize') or
                      (payload.get('extended') or {}).get('bidSize') or (payload.get('quote') or {}).get('bidSize'))
            ask_sz = (payload.get('ask_size') or payload.get('askSize') or
                      (payload.get('extended') or {}).get('askSize') or (payload.get('quote') or {}).get('askSize'))

            # Timestamp: provider may use epoch ms, 'time', or nested fields
            timestamp = payload.get('timestamp') or payload.get('time') or payload.get('quoteTime') or payload.get('tradeTime') or ts
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

    async def get_price_history(self, symbol: str, period_type: str = "day", period: int = 1, 
                               frequency_type: str = "daily", frequency: int = 1, 
                               start_date: Optional[Union[int, date]] = None, end_date: Optional[Union[int, date]] = None,
                               need_extended_hours_data: bool = False) -> Dict[str, Any]:
        """
        Retrieve historical price data from Schwab API.
        
        Args:
            symbol: Stock symbol (e.g., 'SPY')
            period_type: 'day', 'month', 'year', 'ytd'
            period: Number of periods (1, 2, 3, etc.)
            frequency_type: 'minute', 'daily', 'weekly', 'monthly'
            frequency: Frequency value (1, 5, 10, 15, 30 for minute data)
            start_date: Start date as epoch milliseconds
            end_date: End date as epoch milliseconds
            
        Returns:
            Dict containing candles and metadata
        """
        try:
            params = {
                'periodType': period_type,
                'period': period,
                'frequencyType': frequency_type,
                'frequency': frequency
            }
            
            # Convert date objects to epoch milliseconds if provided
            if start_date:
                if isinstance(start_date, date):
                    # Convert date to epoch milliseconds (start of day)
                    start_datetime = datetime.combine(start_date, datetime.min.time())
                    params['startDate'] = int(start_datetime.timestamp() * 1000)
                else:
                    params['startDate'] = start_date
                    
            if end_date:
                if isinstance(end_date, date):
                    # Convert date to epoch milliseconds (end of day)
                    end_datetime = datetime.combine(end_date, datetime.max.time())
                    params['endDate'] = int(end_datetime.timestamp() * 1000)
                else:
                    params['endDate'] = end_date
                    
            if need_extended_hours_data:
                params['needExtendedHoursData'] = need_extended_hours_data
                
            url = self._join("/pricehistory")
            params['symbol'] = symbol.upper()
            
            headers = await self._headers()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        response_text = await response.text()
                        logger.error(f"Historical API error {response.status}: {response_text}")
                        logger.error(f"Request URL: {response.url}")
                        logger.error(f"Request headers: {headers}")
                        logger.error(f"Request params: {params}")
                    
                    response.raise_for_status()
                    data = await response.json()
                    
                    logger.debug(f"Historical data retrieved for {symbol}: {len(data.get('candles', []))} candles")
                    return data
                
        except Exception as e:
            logger.error(f"Error getting price history for {symbol}: {e}")
            return {"candles": [], "symbol": symbol, "empty": True}

    async def get_daily_bars(self, symbol: str, days_back: int = 30) -> List[Dict[str, Any]]:
        """
        Get daily OHLCV bars for a symbol.
        
        Args:
            symbol: Stock symbol
            days_back: Number of days of history to retrieve
            
        Returns:
            List of daily bar dictionaries
        """
        try:
            data = await self.get_price_history(
                symbol=symbol,
                period_type="day",
                period=days_back,
                frequency_type="daily",
                frequency=1
            )
            
            candles = data.get('candles', [])
            bars = []
            
            for candle in candles:
                bars.append({
                    'symbol': symbol.upper(),
                    'date': candle.get('datetime'),
                    'open': candle.get('open'),
                    'high': candle.get('high'),
                    'low': candle.get('low'),
                    'close': candle.get('close'),
                    'volume': candle.get('volume', 0)
                })
                
            logger.debug(f"Retrieved {len(bars)} daily bars for {symbol}")
            return bars
            
        except Exception as e:
            logger.error(f"Error getting daily bars for {symbol}: {e}")
            return []



    async def get_intraday_bars(self, symbol: str, target_date: date, session: str = "rth") -> List[Dict[str, Any]]:
        """
        Get intraday minute bars for a specific trading day.
        
        Args:
            symbol: Stock symbol
            target_date: Trading date to get bars for
            session: Trading session ('rth' for regular trading hours)
            
        Returns:
            List of intraday bar dictionaries
        """
        try:
            # Get 1-minute bars for the target date
            data = await self.get_price_history(
                symbol=symbol,
                period_type="day",
                period=1,
                frequency_type="minute",
                frequency=1,
                start_date=target_date,
                end_date=target_date
            )
            
            candles = data.get('candles', [])
            bars = []
            
            for candle in candles:
                # Convert timestamp to datetime
                dt = datetime.fromtimestamp(candle.get('datetime', 0) / 1000)
                
                # Filter for regular trading hours if requested
                if session == "rth":
                    # Regular trading hours: 9:30 AM - 4:00 PM ET
                    if dt.hour < 9 or (dt.hour == 9 and dt.minute < 30) or dt.hour >= 16:
                        continue
                
                bars.append({
                    'symbol': symbol.upper(),
                    'datetime': dt,
                    'timestamp': candle.get('datetime'),
                    'open': candle.get('open'),
                    'high': candle.get('high'),
                    'low': candle.get('low'),
                    'close': candle.get('close'),
                    'volume': candle.get('volume', 0)
                })
                
            logger.debug(f"Retrieved {len(bars)} intraday bars for {symbol} on {target_date}")
            return bars
            
        except Exception as e:
            logger.error(f"Error getting intraday bars for {symbol} on {target_date}: {e}")
            return []
