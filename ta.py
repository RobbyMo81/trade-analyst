#!/usr/bin/env python3
import argparse, asyncio, json, subprocess, sys
from pathlib import Path
import typer
from datetime import datetime
from app.config import Config
from app.auth import AuthManager
from app.historical import HistoricalInterface
import asyncio

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

def cmd_diag_provider(ns):
    """Run provider diagnostics - authentication and connectivity checks"""
    print("Running provider diagnostics...")
    
    async def run_diagnostics():
        try:
            from app.production_provider import run_diagnostics
            result = await run_diagnostics()
            print(json.dumps(result, indent=2))
            
            # Exit with non-zero code if auth failed
            if result.get("auth") != "ok":
                sys.exit(1)
                
        except SystemExit:
            raise
        except Exception as e:
            error_result = {
                "auth": "failed", 
                "provider": "schwab",
                "error": str(e),
                "time": datetime.utcnow().isoformat() + "Z"
            }
            print(json.dumps(error_result, indent=2))
            sys.exit(1)
    
    asyncio.run(run_diagnostics())

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
    sp = sub.add_parser("calc-levels", help="Calculate R1, S1, VWAP for a symbol/date.")
    sp.add_argument("--symbol", type=str, required=True, help="Symbol, e.g. AAPL, NQ")
    sp.add_argument("--date", type=str, required=True, help="Date YYYY-MM-DD")
    sp.add_argument("--format", type=str, default="ai-block", help="Output format: ai-block, json, csv")
    sp.set_defaults(func=calc_levels)

    sp = sub.add_parser("diag", help="System diagnostics")
    diag_sub = sp.add_subparsers(dest="diag_cmd", required=True)
    
    # ta diag provider
    provider_sp = diag_sub.add_parser("provider", help="Check provider authentication and connectivity")
    provider_sp.set_defaults(func=cmd_diag_provider)

    sp = sub.add_parser("preflight", help="Run OAuth preflight checks")
    sp.add_argument("--env", default="dev")
    sp.add_argument("--reset-cache", action="store_true")
    sp.add_argument("--out", default="oauth_preflight_report.json")
    sp.set_defaults(func=cmd_preflight)

    sp = sub.add_parser("serve-callback", help="Start HTTPS callback listener")
def calc_levels(ns):
    """Calculate R1, S1, VWAP for a symbol/date."""
    symbol = ns.symbol
    date = ns.date
    format = ns.format
    print(f"[DEBUG] calc-levels: symbol={symbol}, date={date}, format={format}")
    config = Config()
    print("[DEBUG] Config loaded.")
    auth_manager = AuthManager(config)
    print("[DEBUG] AuthManager initialized.")
    historical = HistoricalInterface(config, auth_manager)
    print("[DEBUG] HistoricalInterface initialized.")
    dt = datetime.strptime(date, "%Y-%m-%d")

    async def run():
        print(f"[DEBUG] Fetching OHLC for {symbol} on {dt.date()}...")
        ohlc = await historical.get_ohlc(symbol, dt, dt, interval="1D")
        print(f"[DEBUG] OHLC result: {ohlc}")
        if not ohlc or len(ohlc) == 0:
            print("No OHLC data found. Check authentication, config, or stub implementation.")
            return
        bar = ohlc[0]
        print(f"[DEBUG] Using bar: {bar}")
        H, L, C = float(bar["high"]), float(bar["low"]), float(bar["close"])
        pivot = (H + L + C) / 3.0
        r1 = 2 * pivot - L
        s1 = 2 * pivot - H
        vwap = float(bar.get("vwap", pivot))
        print(f"[DEBUG] Calculated: pivot={pivot}, r1={r1}, s1={s1}, vwap={vwap}")
        if format == "ai-block":
            print("[AI_DATA_BLOCK_START]")
            print(f"R1: {r1:.4f}")
            print(f"S1: {s1:.4f}")
            print(f"VWAP: {vwap:.4f}")
            print("[AI_DATA_BLOCK_END]")
        elif format == "json":
            import json
            print(json.dumps({"R1": r1, "S1": s1, "VWAP": vwap, "pivot": pivot}, indent=2))
        elif format == "csv":
            print("R1,S1,VWAP,pivot")
            print(f"{r1:.4f},{s1:.4f},{vwap:.4f},{pivot:.4f}")
        else:
            print(f"Unknown format: {format}")
            return

    asyncio.run(run())
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
