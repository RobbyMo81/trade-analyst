import os, asyncio, pytest
from app.auth import AuthManager
from app.config import Config

REQUIRED_ENV = [
    'SCHWAB_CLIENT_ID',
    'SCHWAB_CLIENT_SECRET',
]

def test_real_oauth_smoke_skipped_if_missing_env():
    if any(not os.getenv(v) for v in REQUIRED_ENV) or os.getenv('SKIP_REAL_OAUTH', '1') == '1':
        pytest.skip('Real OAuth smoke skipped: credentials or flag missing')

    async def _run():
        cfg = Config('config.toml')
        cfg.config_data.setdefault('auth', {})['simulate'] = False
        cfg.config_data.setdefault('auth', {})['client_id'] = os.getenv('SCHWAB_CLIENT_ID')
        cfg.config_data.setdefault('auth', {})['client_secret'] = os.getenv('SCHWAB_CLIENT_SECRET')
        am = AuthManager(cfg)
        manual_code = os.getenv('MANUAL_OAUTH_CODE')
        if manual_code:
            ok = await am.handle_callback(code=manual_code, state='manual', provider='default')
            assert ok, 'Manual code exchange failed'
        else:
            url = await am._build_auth_url('default')
            assert 'code_challenge' in url
    asyncio.run(_run())
