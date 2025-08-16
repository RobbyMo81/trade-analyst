
#!/usr/bin/env python3
"""TradeAnalyst unified CLI façade (thin wrappers)."""
from __future__ import annotations
import asyncio, json, os, subprocess, sys
from typing import List
import typer

app = typer.Typer(help="TradeAnalyst unified CLI")

def _run(args: list[str]) -> int:
    return subprocess.call(args)

@app.command()
def preflight(env: str = typer.Option("dev", help="Environment key (e.g., dev, prod)"),
              reset_cache: bool = typer.Option(False, help="Delete stale token cache before checks"),
              out: str = typer.Option("oauth_preflight_report.json", help="JSON report path")):
    """Run Schwab OAuth preflight checks."""
    cmd = [sys.executable, "-m", "scripts.oauth_preflight", "--env", env, "--out", out]
    if reset_cache:
        cmd.append("--reset-cache")
    raise SystemExit(_run(cmd))

@app.command("serve-callback")
def serve_callback(env: str = typer.Option("dev", help="Environment key"),
                   port: int = typer.Option(8443, help="HTTPS port"),
                   tls: bool = typer.Option(True, help="Enable TLS for local HTTPS")):
    """Start HTTPS callback listener that writes last_callback.json."""
    cmd = [sys.executable, "-m", "scripts.callback_server", "--env", env, "--port", str(port)]
    if tls:
        cmd.append("--tls")
    raise SystemExit(_run(cmd))

@app.command("auth-login")
def auth_login(env: str = typer.Option("dev", help="Environment key"),
               no_browser: bool = typer.Option(False, help="Print URL instead of opening browser"),
               timeout: int = typer.Option(180, help="Seconds to wait for callback")):
    """Confidential + PKCE login (opens browser unless --no-browser)."""
    cmd = [sys.executable, "-m", "scripts.secure_auth_login", "--env", env, "--timeout", str(timeout)]
    if no_browser:
        cmd.append("--no-browser")
    raise SystemExit(_run(cmd))

@app.command()
def stress(target: str = typer.Argument(..., help="Dotted async target, e.g. scripts.targets:schwab_quotes"),
           concurrency: int = typer.Option(50, help="Concurrent tasks"),
           iterations: int = typer.Option(1000, help="Total tasks"),
           symbols: str = typer.Option("ES,NQ,SPY", help="Comma-separated symbols"),
           delay_jitter_ms: int = typer.Option(20, help="Randomized dispatch delay (0..ms)"),
           print_sample: bool = typer.Option(False, help="Include sample responses in report")):
    """Forward to the async stress runner."""
    # Prefer local scripts/stress_runner.py if present, else fallback to stress_suite/scripts/stress_runner.py
    runner_path = "scripts/stress_runner.py"
    alt_runner_path = "stress_suite/scripts/stress_runner.py"
    runner = runner_path if os.path.exists(runner_path) else alt_runner_path
    cmd = [sys.executable, runner,
           "--target", target,
           "--concurrency", str(concurrency),
           "--iterations", str(iterations),
           "--symbols", symbols,
           "--delay-jitter-ms", str(delay_jitter_ms)]
    if print_sample:
        cmd.append("--print-sample")
    raise SystemExit(_run(cmd))

@app.command()
def quotes(symbols: List[str] = typer.Argument(..., help="Symbols, e.g. ES NQ SPY")):
    """One-shot quotes pull (real or simulate based on env)."""
    async def run():
        from app.config import Config
        from app.auth import AuthManager
        from app.providers import schwab as S
        cfg = Config()
        auth = AuthManager(cfg)
        client = S.SchwabClient(auth=auth, config=cfg)
        out = await client.quotes([s.upper() for s in symbols])
        print(json.dumps(out, indent=2))
    asyncio.run(run())

@app.command()
def healthcheck():
    """Run system healthcheck and return its exit code."""
    from app.healthcheck import run_healthcheck
    # Use default env; can be extended to accept --env later
    code = run_healthcheck(env="dev")
    raise SystemExit(code)

if __name__ == "__main__":
    app()
