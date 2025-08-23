#!/usr/bin/env python3
"""
Trade Analyst CLI - Production Safe Version

Main CLI entry point with production safety and mandatory provenance tracking.
"""

import argparse
import asyncio
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Ensure repository root is on sys.path for module imports
REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def run(args):
    """Run a subprocess command"""
    return subprocess.call(args)


def cmd_preflight(ns):
    """Run OAuth preflight checks"""
    cmd = [sys.executable, "-m", "scripts.oauth_preflight", "--env", ns.env, "--out", ns.out]
    if ns.reset_cache:
        cmd.append("--reset-cache")
    raise SystemExit(run(cmd))


def cmd_serve_callback(ns):
    """Start HTTPS callback listener"""
    cmd = [sys.executable, "-m", "scripts.callback_server", "--env", ns.env, "--port", str(ns.port)]
    if ns.tls:
        cmd.append("--tls")
    raise SystemExit(run(cmd))


def cmd_auth_login(ns):
    """Confidential + PKCE login"""
    cmd = [sys.executable, "-m", "scripts.secure_auth_login", "--env", ns.env, "--timeout", str(ns.timeout)]
    if ns.no_browser:
        cmd.append("--no-browser")
    raise SystemExit(run(cmd))


def cmd_futures_info(ns):
    """Get information about a futures symbol"""
    from app.utils.futures_symbols import get_futures_info, enhanced_translate_root_to_front_month, list_supported_futures
    
    if ns.list:
        print("Supported futures root symbols:")
        for root in sorted(list_supported_futures()):
            info = get_futures_info(root)
            if info:
                print(f"  {root:<8} - {info.description} ({info.category.value})")
        return
    
    if not ns.symbol:
        print("Please provide a symbol with --symbol or use --list to see all supported symbols")
        return
    
    # Get symbol info
    info = get_futures_info(ns.symbol)
    if not info:
        print(f"Symbol '{ns.symbol}' not recognized as a futures symbol")
        return
    
    # Get front month translation
    translated = enhanced_translate_root_to_front_month(ns.symbol)
    
    print(f"Futures Symbol Information:")
    print(f"  Input Symbol: {ns.symbol}")
    print(f"  Root: {info.root}")
    print(f"  Description: {info.description}")
    print(f"  Category: {info.category.value}")
    
    if translated != ns.symbol:
        print(f"  Front Month: {translated}")
        front_info = get_futures_info(translated)
        if front_info and front_info.month_code:
            print(f"  Expiry Month: {front_info.month_number} ({front_info.month_code})")
            print(f"  Expiry Year: {front_info.full_year}")


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
                print("❌ Provider authentication failed", file=sys.stderr)
                sys.exit(1)
            else:
                print("✅ Provider diagnostics passed", file=sys.stderr)
                
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
            print(f"❌ Provider diagnostics failed: {e}", file=sys.stderr)
            sys.exit(1)
    
    asyncio.run(run_diagnostics())


def cmd_quotes(ns):
    """One-shot quotes pull"""
    from app.config import Config
    from app.auth import AuthManager
    from app.providers import schwab as S
    
    async def go():
        config = Config()
        auth = AuthManager(config)
        client = S.SchwabClient(auth=auth, config=config)
        out = await client.quotes(ns.symbols)
        print(json.dumps(out, indent=2))
    
    asyncio.run(go())


def calc_levels(ns):
    """Calculate R1, S1, VWAP for a symbol/date using production-safe implementation."""
    # Delegate to the production-safe calc_levels function in start.py
    from start import calc_levels as production_calc_levels
    production_calc_levels(ns.symbol, ns.date, ns.format)


def main():
    """Main CLI entry point"""
    p = argparse.ArgumentParser(prog="ta.py", description="TradeAnalyst CLI - Production Safe")
    sub = p.add_subparsers(dest="cmd", required=True)
    
    # calc-levels command
    sp = sub.add_parser("calc-levels", help="Calculate R1, S1, VWAP for a symbol/date")
    sp.add_argument("--symbol", type=str, required=True, help="Symbol, e.g. AAPL, /NQ")
    sp.add_argument("--date", type=str, required=True, help="Date YYYY-MM-DD")
    sp.add_argument("--format", type=str, default="ai-block", 
                   help="Output format: ai-block, json, levels.v1, csv")
    sp.set_defaults(func=calc_levels)

    # diag command with subcommands
    diag_parser = sub.add_parser("diag", help="System diagnostics")
    diag_sub = diag_parser.add_subparsers(dest="diag_cmd", required=True)
    
    # diag provider
    provider_sp = diag_sub.add_parser("provider", help="Check provider authentication and connectivity")
    provider_sp.set_defaults(func=cmd_diag_provider)

    # preflight command
    sp = sub.add_parser("preflight", help="Run OAuth preflight checks")
    sp.add_argument("--env", default="dev")
    sp.add_argument("--reset-cache", action="store_true")
    sp.add_argument("--out", default="oauth_preflight_report.json")
    sp.set_defaults(func=cmd_preflight)

    # serve-callback command
    sp = sub.add_parser("serve-callback", help="Start HTTPS callback listener")
    sp.add_argument("--env", default="dev")
    sp.add_argument("--port", type=int, default=8443)
    sp.add_argument("--tls", action="store_true", default=True)
    sp.set_defaults(func=cmd_serve_callback)

    # auth-login command
    sp = sub.add_parser("auth-login", help="Confidential + PKCE login")
    sp.add_argument("--env", default="dev")
    sp.add_argument("--no-browser", action="store_true")
    sp.add_argument("--timeout", type=int, default=180)
    sp.set_defaults(func=cmd_auth_login)

    # quotes command
    sp = sub.add_parser("quotes", help="One-shot quotes pull")
    sp.add_argument("symbols", nargs="+")
    sp.set_defaults(func=cmd_quotes)

    # futures-info command
    sp = sub.add_parser("futures-info", help="Get information about futures symbols")
    sp.add_argument("--symbol", type=str, help="Futures symbol to analyze (e.g., /ES, NQZ25)")
    sp.add_argument("--list", action="store_true", help="List all supported futures symbols")
    sp.set_defaults(func=cmd_futures_info)

    # Parse and execute
    ns = p.parse_args()
    ns.func(ns)


if __name__ == "__main__":
    main()
