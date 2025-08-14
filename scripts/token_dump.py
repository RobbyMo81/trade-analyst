"""Inspect token cache for quick triage.

Usage (PowerShell):
    .venv\\Scripts\\python -m scripts.token_dump
"""
from __future__ import annotations

import json, os, pathlib

def main() -> int:
    cache = os.getenv("TOKEN_CACHE_PATH", ".cache\\dev\\token_cache.json")
    p = pathlib.Path(cache)
    print("cache:", p, "exists:", p.exists())
    if p.exists():
        try:
            j = json.loads(p.read_text(encoding="utf-8"))
            print({k: j.get(k) for k in ("token_type","expires_in","scope","access_token","refresh_token")})
        except Exception as e:
            print("failed to read token cache:", e)
            return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
