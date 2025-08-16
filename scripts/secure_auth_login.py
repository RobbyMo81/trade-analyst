"""Secure OAuth login (Confidential + PKCE).

- Generates PKCE
- Opens browser to authorize_url
- Waits for a callback artifact written by a separate callback server
- Exchanges code using Basic auth (if configured) + code_verifier
- Writes raw token response to token_response_raw.json for your app to import/encrypt

Usage (PowerShell):
  .venv\\Scripts\\python -m scripts.secure_auth_login --env dev
  .venv\\Scripts\\python -m scripts.secure_auth_login --env dev --no-browser
"""
from __future__ import annotations

import argparse, asyncio, json, os
from pathlib import Path
from app.config import Config
from app.auth import AuthManager
import webbrowser


async def main_async(env: str, no_browser: bool, timeout: int) -> int:
    cfg = Config()
    auth = AuthManager(cfg, env=env)
    # Build URL (stores PKCE verifier internally)
    url = await auth._build_auth_url("default")  # internal helper
    if not no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    print("Auth URL:", url)
    # Persist the URL so external tools or the assistant can present it while this process waits
    cache_dir = Path('.cache') / env
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / 'auth_url.txt').write_text(url, encoding='utf-8')

    # Wait for callback artifact (written by callback server)
    artifact = cache_dir / 'last_callback.json'
    # Clear any stale artifact from prior attempts
    try:
        if artifact.exists():
            artifact.unlink()
    except Exception:
        pass
    # Poll every 0.5s up to the timeout window
    polls = max(1, int(timeout / 0.5))
    for _ in range(polls):
        if artifact.exists():
            try:
                data = json.loads(artifact.read_text(encoding='utf-8'))
                code = data.get('code')
                state = data.get('state', '')
                if code:
                    ok = await auth.handle_callback(code, state, provider='default')
                    if ok:
                        raw = {
                            'access_token': auth.tokens['default'].get('access_token'),
                            'refresh_token': auth.tokens['default'].get('refresh_token'),
                            'token_type': auth.tokens['default'].get('token_type'),
                        }
                        (cache_dir / 'token_response_raw.json').write_text(json.dumps(raw, indent=2))
                        print("Login successful; raw token saved.")
                        return 0
            except Exception:
                pass
        await asyncio.sleep(0.5)
    print("No callback artifact received.")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--env', default='dev')
    ap.add_argument('--no-browser', action='store_true')
    ap.add_argument('--timeout', type=int, default=180, help='Seconds to wait for callback artifact')
    a = ap.parse_args()
    return asyncio.run(main_async(a.env, a.no_browser, a.timeout))


if __name__ == '__main__':
    raise SystemExit(main())
