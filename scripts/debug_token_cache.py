#!/usr/bin/env python3
"""Inspect token cache and AuthManager view.

Usage:
  python -m scripts.debug_token_cache --env dev

Outputs:
  - cache path & size
  - top-level keys in raw token file (after decrypt if needed)
  - whether provider 'default' is present & access token status
  - get_access_token result (attempting refresh if expired)
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
from app.config import Config
from app.auth import AuthManager
import asyncio


async def run(env: str):
    cfg = Config()
    auth = AuthManager(cfg, env=env)
    cache_path = Path(auth.token_file)
    print(f"cache_path: {cache_path}")
    print(f"cache_exists: {cache_path.exists()} size: {cache_path.stat().st_size if cache_path.exists() else 0}")
    await auth._load_tokens()
    raw_keys = list(auth.tokens.keys())
    print(f"raw_top_level_keys: {raw_keys}")
    default_rec = auth.tokens.get('default')
    print(f"default_present: {default_rec is not None}")
    if isinstance(default_rec, dict):
        print(f"default_record_keys: {list(default_rec.keys())}")
        print(f"access_token_present: {bool(default_rec.get('access_token'))}")
        print(f"expires_at: {default_rec.get('expires_at')}")
    token = await auth.get_access_token('default')
    print(f"get_access_token_returned_nonempty: {bool(token)}")
    if token and isinstance(token, str):
        print(f"access_token_prefix: {token[:12]}... len={len(token)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--env', default='dev')
    args = ap.parse_args()
    asyncio.run(run(args.env))


if __name__ == '__main__':  # pragma: no cover
    main()
