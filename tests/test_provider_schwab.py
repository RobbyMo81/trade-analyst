import pytest
from app.config import Config
from app.auth import AuthManager
from app.providers import get_provider

@pytest.mark.asyncio
async def test_schwab_client_ping_simulate():
    cfg = Config()
    cfg.set('auth.simulate', True)
    auth = AuthManager(cfg)
    # Ensure simulated token present
    await auth.login('default')
    client = get_provider('schwab', cfg, auth)
    result = await client.ping()
    assert result.get('status') == 'ok'
    assert result.get('simulate') is True
