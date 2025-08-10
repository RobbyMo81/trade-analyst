import asyncio
from app.auth import AuthManager
from app.config import Config

async def _run_flow():
    cfg = Config('config.toml')
    # Ensure real flow (not simulated)
    cfg.config_data.setdefault('auth', {})['simulate'] = False
    am = AuthManager(cfg)

    # Monkeypatch: replace _request_token with deterministic coroutine
    async def fake_request(token_url, data):  # noqa: D401
        # Validate code_verifier presence if PKCE stored
        stored = am._load_pkce_state().get('default', {})
        if stored.get('code_verifier') and 'code_verifier' not in data:
            raise AssertionError("PKCE code_verifier missing from token request")
        return {
            'access_token': 'ACCESS123',
            'refresh_token': 'REFRESH123',
            'expires_in': 1200,
            'token_type': 'Bearer'
        }
    am._request_token = fake_request  # type: ignore

    # Build auth URL to store pkce state and generate state value
    await am._build_auth_url('default')
    st = am._load_pkce_state().get('default')
    assert st and st['state']

    # Simulate provider redirect with correct state
    ok = await am.handle_callback(code='AUTHCODE', state=st['state'], provider='default')
    assert ok, 'Callback handling should succeed with correct state'

    # Ensure tokens persisted and pkce state cleared
    assert 'default' in am.tokens
    assert am.tokens['default']['access_token'] == 'ACCESS123'
    # After success pkce state should be cleared
    assert 'default' not in am._load_pkce_state()


def test_callback_success():
    asyncio.run(_run_flow())
