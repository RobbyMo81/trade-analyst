import json, asyncio, os
from app.auth import AuthManager
from app.config import Config

async def _run_flow(simulate=False):
    cfg = Config('config.toml')
    cfg.config_data.setdefault('auth', {})['simulate'] = simulate
    am = AuthManager(cfg)
    # Force build auth URL (stores pkce state)
    url = await am._build_auth_url('default')
    state_data = am._load_pkce_state().get('default')
    assert state_data and state_data['state']
    # Simulate callback with mismatched state
    ok = await am.handle_callback(code='CODE', state='WRONG', provider='default')
    assert not ok


def test_pkce_state_mismatch():
    asyncio.run(_run_flow(simulate=False))
