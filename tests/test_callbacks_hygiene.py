from app.utils.validators import is_valid_redirect_format, exact_match

REGISTERED = [
  "https://127.0.0.1:5000/oauth2/callback",
  "https://127.0.0.1:3000/auth/redirect",
  "https://127.0.0.1:8443/auth/redirect",
]

def test_valid_exact_match():
    assert exact_match("https://127.0.0.1:5000/oauth2/callback", REGISTERED)

def test_scheme_mismatch():
    assert not is_valid_redirect_format("http://127.0.0.1:5000/oauth2/callback")

def test_path_not_registered():
    assert not exact_match("https://127.0.0.1:5000/other", REGISTERED)
