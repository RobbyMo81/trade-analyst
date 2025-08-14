import asyncio
import pytest
from app.config import Config
from app.healthcheck import HealthChecker

class DummyResp:
    def __init__(self, status):
        self.status = status
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        return False

class DummySession:
    def __init__(self, statuses):
        self._statuses = statuses
        self._idx = 0
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        return False
    def get(self, url):
        # Return next status; simulate 404 then 200, etc
        if self._idx < len(self._statuses):
            status = self._statuses[self._idx]
            self._idx += 1
        else:
            status = 500
        return DummyResp(status)

@pytest.mark.asyncio
async def test_market_server_ok(monkeypatch):
    cfg = Config()
    cfg.set('providers.schwab.marketdata_base', 'https://probe.example')
    # Force simulate false to get healthy status
    cfg.set('auth.simulate', False)

    # Patch aiohttp.ClientSession to our dummy returning 404 (acceptable)
    import app.healthcheck as hc_mod
    class CS:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return DummySession([404])
        async def __aexit__(self, exc_type, exc, tb): return False
    class CT:
        def __init__(self, *a, **k):
            pass
    Aio = type('Aio', (), {'ClientSession': CS, 'ClientTimeout': CT})
    monkeypatch.setattr(hc_mod, 'aiohttp', Aio)

    hc = HealthChecker(cfg)
    res = await hc.check_schwab_market_server()
    assert res.status == 'healthy'

@pytest.mark.asyncio
async def test_market_server_unreachable_simulated(monkeypatch):
    cfg = Config()
    cfg.set('providers.schwab.marketdata_base', 'https://probe.example')
    cfg.set('auth.simulate', True)

    import app.healthcheck as hc_mod
    class CS:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return DummySession([500, 500])
        async def __aexit__(self, exc_type, exc, tb): return False
    class CT:
        def __init__(self, *a, **k):
            pass
    Aio = type('Aio', (), {'ClientSession': CS, 'ClientTimeout': CT})
    monkeypatch.setattr(hc_mod, 'aiohttp', Aio)

    hc = HealthChecker(cfg)
    res = await hc.check_schwab_market_server()
    assert res.status == 'warning'

@pytest.mark.asyncio
async def test_market_server_unreachable_live(monkeypatch):
    cfg = Config()
    cfg.set('providers.schwab.marketdata_base', 'https://probe.example')
    cfg.set('auth.simulate', False)

    import app.healthcheck as hc_mod
    class CS:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return DummySession([500, 500])
        async def __aexit__(self, exc_type, exc, tb): return False
    class CT:
        def __init__(self, *a, **k):
            pass
    Aio = type('Aio', (), {'ClientSession': CS, 'ClientTimeout': CT})
    monkeypatch.setattr(hc_mod, 'aiohttp', Aio)

    hc = HealthChecker(cfg)
    res = await hc.check_schwab_market_server()
    assert res.status == 'unhealthy'
