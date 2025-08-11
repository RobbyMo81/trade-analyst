import asyncio, types
from app.providers.schwab import SchwabClient
from app.auth import AuthManager
from app.config import Config
import pytest

class DummyResponse:
    def __init__(self, status, payload):
        self.status = status
        self._payload = payload
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        return False
    async def json(self):
        return self._payload

class DummySession:
    def __init__(self, batch_payload=None, per_payload=None):
        self.batch_payload = batch_payload
        self.per_payload = per_payload or {}
        self.requests = []
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        return False
    def get(self, url, headers=None, params=None, timeout=None):
        # Batch endpoint
        if params and 'symbols' in params and self.batch_payload is not None:
            self.requests.append(('batch', url, params))
            return DummyResponse(200, self.batch_payload)
        # Per symbol fallback
        sym = url.rsplit('/',1)[-1]
        payload = self.per_payload.get(sym, {'symbol': sym, 'bid': 10.0, 'ask': 10.1, 'bidSize': 1, 'askSize': 2})
        self.requests.append(('per', url, None))
        return DummyResponse(200, payload)

def test_quotes_live_batch(monkeypatch):
    async def _run():
        cfg = Config('config.toml')
        cfg.config_data.setdefault('auth', {})['simulate'] = False
        cfg.config_data.setdefault('auth', {})['base_url'] = 'https://example.com'
        am = AuthManager(cfg)
        # Seed token for headers and bypass validity checks
        am.tokens['default'] = {'access_token':'XYZ','expires_at':'2999-01-01T00:00:00','token_type':'Bearer'}
        async def _ga(provider):
            return 'XYZ'
        am.get_access_token = _ga  # type: ignore

        batch_payload = {'quotes':[{'symbol':'ABC','bid':100,'ask':100.5,'bidSize':10,'askSize':12}]}
        dummy = DummySession(batch_payload=batch_payload)
        monkeypatch.setattr('app.providers.schwab.aiohttp.ClientSession', lambda: dummy)

        client = SchwabClient(cfg, am)
        out = await client.quotes(['ABC'])
        assert out['validation']['is_valid']
        assert out['normalized'][0]['symbol'] == 'ABC'
        assert dummy.requests[0][0] == 'batch'
    asyncio.run(_run())
def test_quotes_live_per_symbol_fallback(monkeypatch):
    async def _run():
        cfg = Config('config.toml')
        cfg.config_data.setdefault('auth', {})['simulate'] = False
        cfg.config_data.setdefault('auth', {})['base_url'] = 'https://example.com'
        am = AuthManager(cfg)
        am.tokens['default'] = {'access_token':'XYZ','expires_at':'2999-01-01T00:00:00','token_type':'Bearer'}
        async def _ga(provider):
            return 'XYZ'
        am.get_access_token = _ga  # type: ignore

        class FailingBatchSession(DummySession):
            def get(self, url, headers=None, params=None, timeout=None):  # override
                if params and 'symbols' in params:
                    raise RuntimeError('batch fail')
                return super().get(url, headers=headers, params=params, timeout=timeout)
        dummy = FailingBatchSession()
        monkeypatch.setattr('app.providers.schwab.aiohttp.ClientSession', lambda: dummy)

        client = SchwabClient(cfg, am)
        out = await client.quotes(['XYZ'])
        assert out['validation']['is_valid']
        assert out['normalized'][0]['symbol'] == 'XYZ'
        assert any(kind=='per' for kind, *_ in dummy.requests)
    asyncio.run(_run())
