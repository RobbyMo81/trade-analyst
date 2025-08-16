<#  setup_dev.ps1  — one-shot dev setup & live test
    Usage examples:
      .\setup_dev.ps1
      .\setup_dev.ps1 -Env dev -Symbols "ES,NQ,SPY" -InstallMkcert -GenerateCerts
      .\setup_dev.ps1 -OnlyCreateFiles   # just drops ta.py, token_import.py, app/__init__.py
#>

[CmdletBinding()]
param(
  [string]$Env = "dev",
  [string]$Symbols = "ES,NQ,SPY",
  [int]$Port = 8443,
  [switch]$Force,             # overwrite helper files if they exist
  [switch]$InstallMkcert,     # run mkcert -install
  [switch]$GenerateCerts,     # create SAN cert (127.0.0.1, localhost, ::1)
  [switch]$NoBrowser,         # print auth URL instead of opening browser window
  [string]$Scope = "readonly",# OAuth scope for first login
  [switch]$SkipCreateFiles,   # skip creating helper files
  [switch]$OnlyCreateFiles,   # create helper files and exit
  [int]$LoginTimeout = 240    # timeout (seconds) for secure_auth_login wait
)

function Abort($msg) { Write-Error $msg; exit 1 }
function Info($msg) { Write-Host ">> $msg" -ForegroundColor Cyan }
function Ok($msg)   { Write-Host "[OK] $msg" -ForegroundColor Green }
function Warn($msg) { Write-Warning $msg }

# --- 0) Preconditions ---------------------------------------------------------
if (-not (Test-Path .\config.toml)) { Abort "Run this from the project root (config.toml not found)." }
if (-not (Test-Path .\scripts))     { New-Item -ItemType Directory -Path .\scripts -Force | Out-Null }
if (-not (Test-Path .\app))         { New-Item -ItemType Directory -Path .\app -Force | Out-Null }

# prefer venv python if present
$Py = Join-Path (Join-Path $PWD ".venv\Scripts") "python.exe"
if (-not (Test-Path $Py)) { $Py = "python" }

# --- 1) Create helper files (ta.py, token_import.py, app/__init__.py) --------
function Write-FileIfNeeded($Path, $Content, [switch]$ForceWrite) {
  if ((Test-Path $Path) -and (-not $ForceWrite)) { return }
  $dir = Split-Path -Parent $Path
  if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
  $Content | Set-Content -Path $Path -Encoding UTF8
}

if (-not $SkipCreateFiles) {
  Info "Creating helper files (use -Force to overwrite if they exist)..."

  ## NOTE: The here-strings below must have the terminating `'@ at start of line (no spaces)
  $ta = @'
#!/usr/bin/env python3
"""TradeAnalyst lightweight CLI wrapper (argparse)."""
import argparse, asyncio, json, subprocess, sys
from pathlib import Path

# Ensure repo root (folder containing this ta.py) is on sys.path
REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

def run(args): 
    return subprocess.call(args)

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
    # Try multiple module layouts gracefully
    try:
        from app.config_loader import Config  # type: ignore
        return Config
    except ModuleNotFoundError:
        try:
            from app.config import Config  # type: ignore
            return Config
        except ModuleNotFoundError as e:
            msg = (
                "Cannot import Config. Tried 'app.config_loader' and 'app.config'.\\n"
                "Run from project root; ensure 'app/__init__.py' exists, and that either "
                "app/config_loader.py or app/config.py defines class Config."
            )
            raise SystemExit(msg) from e

def cmd_quotes(ns):
    async def go():
        Config = _import_config()
        from app.auth import AuthManager  # type: ignore
        from app.providers import schwab as S  # type: ignore
        cfg = Config()
        auth = AuthManager(cfg)
        client = S.SchwabClient(auth=auth, config=cfg)
        out = await client.quotes([s.upper() for s in ns.symbols])
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
'@

  $tokenImport = @'
#!/usr/bin/env python3
"""Import raw OAuth token to app token cache (optional Fernet encryption)."""
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
    expires_at = now_utc() + timedelta(seconds=expires_in)
    cache_obj = {
        "provider": "default",
        "token_type": payload.get("token_type","Bearer"),
        "access_token": payload["access_token"],
        "refresh_token": payload.get("refresh_token"),
        "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
        "scope": payload.get("scope"),
        "created_at": now_utc().isoformat().replace("+00:00","Z"),
    }

    key = os.getenv("TOKEN_ENC_KEY")
    cache_dir.mkdir(parents=True, exist_ok=True)
    try:
        if key:
            from cryptography.fernet import Fernet  # type: ignore
            f = Fernet(key.encode() if isinstance(key, str) else key)
            enc = f.encrypt(json.dumps(cache_obj).encode("utf-8"))
            cache_path.write_bytes(enc)
            print(f"Wrote encrypted token cache: {cache_path}")
        else:
            cache_path.write_text(json.dumps(cache_obj, indent=2), encoding="utf-8")
            print(f"Wrote plain token cache (no TOKEN_ENC_KEY): {cache_path}")
    except Exception as e:
        cache_path.write_text(json.dumps(cache_obj, indent=2), encoding="utf-8")
        print(f"Wrote plain token cache (cryptography unavailable). Path: {cache_path}. Error: {e}")
    return 0

if __name__ == "__main__":
  raise SystemExit(main())
'@

  $appInit = "# Marks app as a package so imports like 'from app.config_loader import Config' work.`n"

  Write-FileIfNeeded -Path .\ta.py -Content $ta -ForceWrite:$Force
  Write-FileIfNeeded -Path .\scripts\token_import.py -Content $tokenImport -ForceWrite:$Force
  Write-FileIfNeeded -Path .\app\__init__.py -Content $appInit -ForceWrite:$Force
  Ok "Helper files created."
}

if ($OnlyCreateFiles) { Ok "Created files. Exiting by request (-OnlyCreateFiles)."; exit 0 }

# --- 2) (Optional) mkcert setup ------------------------------------------------
if ($InstallMkcert) {
  if (-not (Get-Command mkcert -ErrorAction SilentlyContinue)) {
    Warn "mkcert not found in PATH; skipping -InstallMkcert."
  } else {
    Info "Installing mkcert local root (user trust store)..."
    mkcert -install | Out-Host
    Ok "mkcert root installed."
  }
}

if ($GenerateCerts) {
  if (-not (Get-Command mkcert -ErrorAction SilentlyContinue)) {
    Warn "mkcert not found; cannot generate certs."
  } else {
    Info "Generating SAN cert: 127.0.0.1, localhost, ::1"
    mkcert -cert-file 127-local.crt -key-file 127-local.key 127.0.0.1 localhost ::1 | Out-Host
    New-Item -ItemType Directory -Path ".\.cache\$Env\certs" -Force | Out-Null
    Copy-Item .\127-local.crt ".\.cache\$Env\certs\server.crt" -Force
    Copy-Item .\127-local.key ".\.cache\$Env\certs\server.key" -Force
    Ok "Copied certs to .cache\$Env\certs"
  }
}

# --- 3) Set scope for this session (non-invasive) ------------------------------
$env:OAUTH_SCOPE = $Scope

# --- 4) Preflight (strict) -----------------------------------------------------
Info "Running OAuth preflight with cache reset..."
& $Py -m scripts.oauth_preflight --env $Env --reset-cache --out oauth_preflight_report.json
if ($LASTEXITCODE -ne 0) { Abort "Preflight failed. See oauth_preflight_report.json." }
Ok "Preflight passed."

# --- 5) Start HTTPS callback server in new window ------------------------------
Info "Starting HTTPS callback server on port $Port (new window)..."
# Set env var in current session (child inherits) instead of inline assignment which previously expanded away
$env:PYTHONIOENCODING = 'utf-8'
$cbCmd = "& `"$Py`" -m scripts.callback_server --env $Env --port $Port --tls"
Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", $cbCmd -WorkingDirectory $PWD | Out-Null
Start-Sleep -Seconds 2
Ok "Callback server launched (check the new window for 'Listening on 127.0.0.1:$Port/auth/redirect')."

# --- 6) Secure login (confidential + PKCE) ------------------------------------
Info "Launching secure OAuth login (timeout=$LoginTimeout s)..."
$loginArgs = @("-m", "scripts.secure_auth_login", "--env", $Env, "--timeout", "$LoginTimeout")
if ($NoBrowser) { $loginArgs += "--no-browser" }
& $Py @loginArgs
if ($LASTEXITCODE -ne 0) { Abort "Login failed. Check callback window and environment variables (or increase -LoginTimeout)." }
Ok "Login successful."

# --- 7) Import token into the app cache ---------------------------------------
Info "Importing raw token into TOKEN_CACHE_PATH..."
& $Py -m scripts.token_import
if ($LASTEXITCODE -ne 0) { Abort "Token import failed. Ensure token_response_raw.json exists." }
Ok "Token cache updated."

# --- 8) Pull a live quotes sample ---------------------------------------------
Info "Fetching live quotes for: $Symbols"
$syms = $Symbols -split ","
& $Py .\ta.py quotes @syms
if ($LASTEXITCODE -ne 0) { Abort "Quotes fetch failed." }
Ok "Live quotes fetched. All systems nominal."
