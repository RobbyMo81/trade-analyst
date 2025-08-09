import json, os, pathlib
from app.auth import AuthManager
from app.config import Config
import pytest

@pytest.mark.asyncio
async def test_simulated_auth_smoke(tmp_path, monkeypatch):
    # Arrange simulate by monkeypatching AuthManager internals for this smoke.
    cfg = Config()
    am = AuthManager(cfg)
    # Force tokens file into temp path
    am.token_file = tmp_path / 'tokens.json'
    # Provide fake token save
    am.tokens['default'] = {
        'access_token':'SIMULATED',
        'expires_at':'2999-01-01T00:00:00',
        'token_type':'Bearer'
    }
    await am._save_tokens()
    # Act
    token = await am.get_access_token('default')
    # Assert
    assert token == 'SIMULATED'
