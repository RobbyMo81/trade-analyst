#!/usr/bin/env python3
"""Import raw OAuth token to app token cache (compat: flat + providers.default)."""
from __future__ import annotations
import os, json
from pathlib import Path
from datetime import datetime, timezone, timedelta

def now_utc(): return datetime.now(timezone.utc)

def main():
    cache_path = Path(os.getenv("TOKEN_CACHE_PATH", ".cache/dev/token_cache.json"))
    cache_dir = cache_path.parent
    raw_path = cache_dir / "token_response_raw.json"
    if not raw_path.exists():
        print(f"ERROR: {raw_path} not found. Run secure_auth_login first."); return 2
    payload = json.loads(raw_path.read_text(encoding="utf-8"))
    if "access_token" not in payload:
        print(f"ERROR: token response missing access_token: {payload}"); return 2

    expires_in = int(payload.get("expires_in", 3600))
    rec = {
        "provider": "default",
        "token_type": payload.get("token_type","Bearer"),
        "access_token": payload["access_token"],
        "refresh_token": payload.get("refresh_token"),
        "expires_at": (now_utc() + timedelta(seconds=expires_in)).isoformat().replace("+00:00","Z"),
        "scope": payload.get("scope"),
        "created_at": now_utc().isoformat().replace("+00:00","Z"),
    }
    # Provide both flat and nested provider mapping for maximal compatibility.
    obj = dict(rec)
    # Provide multiple access patterns:
    #  - obj['default'] (what AuthManager expects: tokens[provider])
    #  - obj['providers']['default'] (forward compatibility / other tooling)
    obj["default"] = dict(rec)
    obj["providers"] = {"default": dict(rec)}

    key = os.getenv("TOKEN_ENC_KEY")
    cache_dir.mkdir(parents=True, exist_ok=True)
    try:
        if key:
            from cryptography.fernet import Fernet  # type: ignore
            f = Fernet(key.encode() if isinstance(key, str) else key)
            enc = f.encrypt(json.dumps(obj).encode("utf-8"))
            cache_path.write_bytes(enc)
            print(f"Wrote encrypted compat token cache: {cache_path}")
        else:
            cache_path.write_text(json.dumps(obj, indent=2), encoding="utf-8")
            print(f"Wrote plain compat token cache (no TOKEN_ENC_KEY): {cache_path}")
    except Exception as e:
        cache_path.write_text(json.dumps(obj, indent=2), encoding="utf-8")
        print(f"Wrote plain compat token cache (cryptography unavailable). Path: {cache_path}. Error: {e}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
