import os
import pytest
from app.config import Config


def test_env_override_wins(monkeypatch):
    monkeypatch.setenv('SCHWAB_MARKETDATA_BASE', 'https://env.example/market/')
    cfg = Config()
    # Also set conflicting provider + legacy to ensure env wins
    cfg.set('providers.schwab.marketdata_base', 'https://cfg.example/root/')
    cfg.set('auth.base_url', 'https://legacy.example/v1/')
    val = cfg.get_schwab_market_base()
    assert val == 'https://env.example/market'


def test_config_provider_fallback(monkeypatch):
    # Ensure env var not present
    monkeypatch.delenv('SCHWAB_MARKETDATA_BASE', raising=False)
    # Prevent .env from re-populating the var
    monkeypatch.setattr('app.config.load_dotenv', lambda *a, **k: None, raising=False)
    cfg = Config()
    cfg.set('providers.schwab.marketdata_base', 'https://cfg.example/root/')
    cfg.set('auth.base_url', 'https://legacy.example/v1/')
    val = cfg.get_schwab_market_base()
    assert val == 'https://cfg.example/root'


def test_legacy_auth_base_fallback(monkeypatch):
    monkeypatch.delenv('SCHWAB_MARKETDATA_BASE', raising=False)
    monkeypatch.setattr('app.config.load_dotenv', lambda *a, **k: None, raising=False)
    cfg = Config()
    # Clear provider override
    cfg.set('providers.schwab.marketdata_base', '')
    cfg.set('auth.base_url', 'https://legacy.example/v1/')
    val = cfg.get_schwab_market_base()
    assert val == 'https://legacy.example/v1'
