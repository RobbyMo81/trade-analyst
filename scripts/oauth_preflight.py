"""OAuth preflight checks (Confidential + PKCE).

Validates:
- HTTPS redirect exact-match in allowlist
- OAuth endpoints present
- Client ID/Secret presence and not placeholders
- TOKEN_ENC_KEY validity for Fernet

Optionally clears token cache when encryption key changed.

Usage (PowerShell):
  .venv\\Scripts\\python -m scripts.oauth_preflight --env dev --out oauth_preflight_report.json
  .venv\\Scripts\\python -m scripts.oauth_preflight --env dev --reset-cache --out oauth_preflight_report.json
"""
from __future__ import annotations

import argparse, json, os
from pathlib import Path
from urllib.parse import urlparse
from typing import Any, Dict

from app.config import Config
from app.utils.validators import exact_match
from cryptography.fernet import Fernet


def _is_placeholder(val: str | None) -> bool:
    if not val:
        return True
    v = val.strip().lower()
    return v.startswith("your_") or v.startswith("changeme") or v in {"", "placeholder"}


def preflight(env: str, reset_cache: bool) -> Dict[str, Any]:
    cfg = Config()

    # Resolve redirect candidates
    redirect = os.getenv("OAUTH_REDIRECT_URI") or (
        cfg.get(f"env.{env}.redirect_uri")
    ) or cfg.get("auth.redirect_uri")
    allowlist = cfg.get("auth.registered_uris", []) or []
    parsed = urlparse(redirect or "")

    # OAuth endpoints
    auth_url = os.getenv("OAUTH_AUTH_URL") or cfg.get("auth.authorize_url") or cfg.get("auth.auth_url")
    token_url = os.getenv("OAUTH_TOKEN_URL") or cfg.get("auth.token_url")

    # Credentials
    cid = os.getenv("CLIENT_ID") or cfg.get("auth.client_id")
    csec = os.getenv("CLIENT_SECRET") or cfg.get("auth.client_secret")

    # Encryption key
    key = os.getenv("TOKEN_ENC_KEY", "")
    key_ok = True
    try:
        if key:
            _ = Fernet(key.encode("utf-8"))
        else:
            key_ok = False
    except Exception:
        key_ok = False

    # Token cache path
    base_cache = cfg.get('runtime.token_cache', 'token_cache.json')
    cache_dir = Path('.cache') / env
    cache_dir.mkdir(parents=True, exist_ok=True)
    token_cache = cache_dir / Path(base_cache).name
    pkce_state = cache_dir / (cfg.get('runtime.pkce_state_file', 'pkce_state.json'))

    actions: list[str] = []
    if reset_cache:
        try:
            if token_cache.exists():
                token_cache.unlink()
                actions.append(f"deleted {token_cache}")
            if pkce_state.exists():
                pkce_state.unlink()
                actions.append(f"deleted {pkce_state}")
        except Exception as e:
            actions.append(f"cache_reset_failed: {e}")

    report = {
        "env": env,
        "redirect_uri": redirect,
        "redirect_https": bool(redirect and parsed.scheme.lower() == 'https'),
        "redirect_in_allowlist": bool(redirect and exact_match(redirect, allowlist)),
        "authorize_url_present": bool(auth_url),
        "token_url_present": bool(token_url),
        "client_id_present": not _is_placeholder(cid),
        "client_secret_present": not _is_placeholder(csec),
        "fernet_key_valid": key_ok,
        "token_cache": str(token_cache),
        "actions": actions,
        "passed": False,
    }
    report["passed"] = all([
        report["redirect_https"],
        report["redirect_in_allowlist"],
        report["authorize_url_present"],
        report["token_url_present"],
        report["client_id_present"],
        report["client_secret_present"],
        report["fernet_key_valid"],
    ])
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", default="dev")
    ap.add_argument("--out", default="oauth_preflight_report.json")
    ap.add_argument("--reset-cache", action="store_true")
    args = ap.parse_args()
    r = preflight(args.env, args.reset_cache)
    Path(args.out).write_text(json.dumps(r, indent=2))
    print(json.dumps(r, indent=2))
    return 0 if r["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
