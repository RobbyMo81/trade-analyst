#!/usr/bin/env python3
import argparse, asyncio, json, subprocess, sys
from pathlib import Path

# Ensure repository root (directory containing this file) is on sys.path for module imports
REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

def run(args): return subprocess.call(args)

def cmd_preflight(ns):
    cmd = [sys.executable, "-m", "scripts.oauth_preflight", "--env", ns.env, "--out", ns.out]
    if ns.reset_cache: cmd.append("--reset-cache")
    raise SystemExit(run(cmd))

def cmd_serve_callback(ns):
    cmd = [sys.executable, "-m", "scripts.callback_server", "--env", ns.env, "--port", str(ns.port)]
    if ns.tls: cmd.append("--tls")
    raise SystemExit(run(cmd))

def cmd_auth_login(ns):
    cmd = [sys.executable, "-m", "scripts.secure_auth_login", "--env", ns.env, "--timeout", str(ns.timeout)]
    if ns.no_browser: cmd.append("--no-browser")
    raise SystemExit(run(cmd))

def _import_config():
    try:
        from app.config_loader import Config  # type: ignore
        return Config
    except ModuleNotFoundError:
        try:
            from app.config import Config  # type: ignore
            return Config
        except ModuleNotFoundError as e:  # pragma: no cover
            raise SystemExit("Cannot import Config from app.config_loader or app.config") from e

def cmd_quotes(ns):
    async def go():
        Config = _import_config()
        from app.auth import AuthManager  # type: ignore
        from app.providers import schwab as S  # type: ignore
        # futures root -> front-month translator
        try:
            from app.utils.futures import translate_root_to_front_month
        except Exception:
            translate_root_to_front_month = lambda s: s
        cfg = Config()
        auth = AuthManager(cfg)
        client = S.SchwabClient(auth=auth, config=cfg)
        # translate roots like ES/NQ to front-month contract codes
        symbols = [translate_root_to_front_month(s).upper() for s in ns.symbols]
        out = await client.quotes(symbols)
        print(json.dumps(out, indent=2))
    asyncio.run(go())

def main():
    p = argparse.ArgumentParser(prog="ta.py", description="TradeAnalyst CLI (wrapper)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("preflight", help="Run OAuth preflight checks")
    sp.add_argument("--env", default="dev")
    sp.add_argument("--reset-cache", action="store_true")
    sp.add_argument("--out", default="oauth_preflight_report.json")
    sp.set_defaults(func=cmd_preflight)

    sp = sub.add_parser("serve-callback", help="Start HTTPS callback listener")
    sp.add_argument("--env", default="dev")
    sp.add_argument("--port", type=int, default=8443)
    sp.add_argument("--tls", action="store_true", default=True)
    sp.set_defaults(func=cmd_serve_callback)

    sp = sub.add_parser("auth-login", help="Confidential + PKCE login")
    sp.add_argument("--env", default="dev")
    sp.add_argument("--no-browser", action="store_true")
    sp.add_argument("--timeout", type=int, default=180)
    sp.set_defaults(func=cmd_auth_login)

    sp = sub.add_parser("quotes", help="One-shot quotes pull")
    sp.add_argument("symbols", nargs="+")
    sp.set_defaults(func=cmd_quotes)

    ns = p.parse_args()
    ns.func(ns)

if __name__ == "__main__":
    main()
