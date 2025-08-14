"""Minimal OAuth login helper using AuthManager.

- Starts the auth flow
- Best-effort local callback if redirect is localhost
- Writes token cache on success

Usage (PowerShell):
  .venv\\Scripts\\python -m scripts.auth_login
"""
from __future__ import annotations

import asyncio
from app.config import Config
from app.auth import AuthManager

async def main() -> int:
    cfg = Config()
    auth = AuthManager(cfg, env="dev")
    ok = await auth.login(provider="default")
    print("login:", ok)
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
