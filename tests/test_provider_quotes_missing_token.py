import pytest


@pytest.mark.asyncio
async def test_quotes_returns_validation_on_missing_token(monkeypatch):
    """SchwabClient.quotes should return structured validation block when no token.

    Ensures:
      - No exception raised
      - validation.is_valid is False with reason
      - normalized list empty
      - RFC3339 timestamp with 'Z' and millisecond component
    """
    from app.providers.schwab import SchwabClient
    from app.config import Config

    class DummyAuth:
        async def get_access_token(self, provider: str):  # signature matches AuthManager
            return None

    cfg = Config('config.toml')
    cfg.config_data.setdefault('auth', {})['simulate'] = False  # force live path
    # base_url not required; missing token short-circuits before HTTP

    client = SchwabClient(cfg, DummyAuth())
    out = await client.quotes(["ES", "NQ"])  # symbols already uppercase

    assert isinstance(out, dict)
    assert 'validation' in out
    assert out['validation']['is_valid'] is False
    assert 'reason' in out['validation']
    assert out.get('normalized') == []
    ts = out.get('ts')
    assert isinstance(ts, str) and ts.endswith('Z') and '.' in ts  # RFC3339 with ms
