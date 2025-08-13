import os
from importlib import reload


def test_env_overrides_tmp(tmp_path, monkeypatch):
    toml_content = """
[auth]
authorize_url = "A"
token_url = "B"
registered_uris = ["https://127.0.0.1:8443/auth/redirect"]

[env.dev]
redirect_uri = "https://127.0.0.1:8443/auth/redirect"

[runtime]
token_cache = ".cache/dev/token.json"
"""
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(toml_content, encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AUTH_SIMULATE", "true")
    monkeypatch.setenv("TOKEN_CACHE_PATH", str(tmp_path / "cache.json"))
    monkeypatch.setenv("OAUTH_AUTH_URL", "https://api.schwabapi.com/v1/oauth/authorize")
    monkeypatch.setenv("OAUTH_TOKEN_URL", "https://api.schwabapi.com/v1/oauth/token")
    monkeypatch.setenv("OAUTH_REDIRECT_URI", "https://127.0.0.1:8443/auth/redirect")
    monkeypatch.setenv("OAUTH_CLIENT_ID", "alias_client")
    monkeypatch.setenv("OAUTH_CLIENT_SECRET", "alias_secret")

    from app import config as config_module
    reload(config_module)
    cfg = config_module.load_config()

    assert cfg["auth"]["simulate"] is True
    assert cfg["runtime"]["token_cache"].endswith("cache.json")
    assert cfg["auth"]["authorize_url"].startswith("https://")
    assert cfg["auth"]["token_url"].startswith("https://")
    assert cfg["env"]["dev"]["redirect_uri"].startswith("https://")
    assert os.getenv("CLIENT_ID") == "alias_client"
    assert os.getenv("CLIENT_SECRET") == "alias_secret"
