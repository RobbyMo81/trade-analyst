import pytest

@pytest.mark.asyncio
async def test_quotes_returns_validation_on_missing_token():
    # Arrange: force get_access_token() to return None via a dummy auth
    from app.providers import schwab as S

    class DummyAuth:
        async def get_access_token(self):  # no token
            return None

    client = S.SchwabClient(auth=DummyAuth())

    out = await client.quotes(["ES", "NQ"])  # symbols must already be uppercase per validator

    assert isinstance(out, dict)
    assert "validation" in out and out["validation"]["is_valid"] is False
    assert "reason" in out["validation"]
    assert "normalized" in out and out["normalized"] == []
    assert "ts" in out and out["ts"].endswith("Z") and "." in out["ts"]  # RFC3339 with ms
