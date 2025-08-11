import sys, pathlib, pytest
from unittest.mock import AsyncMock
root = pathlib.Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

@pytest.fixture
def mock_access_token(monkeypatch):
    """Opt-in fixture; add parameter to test to monkeypatch AuthManager.get_access_token.

    Returns a stable token dict to bypass real auth during provider tests.
    """
    try:
        import app.auth as auth_mod  # noqa: F401
    except Exception:
        pytest.skip("auth module not importable")
    monkeypatch.setattr(
        "app.auth.AuthManager.get_access_token",
        AsyncMock(return_value="XYZ"),
        raising=False
    )
    yield
