<# apply_utc_patch.ps1 — UTC hardening (Tier 1 + Tier 2)
   Usage:
     .\apply_utc_patch.ps1            # apply changes + smoke tests
     .\apply_utc_patch.ps1 -DryRun    # show what would change, do not modify files
     .\apply_utc_patch.ps1 -NoSmoke   # apply but skip smoke tests
#>

[CmdletBinding()]
param(
  [switch]$DryRun = $false,
  [switch]$NoSmoke = $false
)

function Abort { param($m) Write-Error $m; exit 1 }
function Info  { param($m) Write-Host ">> $m" -ForegroundColor Cyan }
function Ok    { param($m) Write-Host "[OK] $m" -ForegroundColor Green }
function Warn  { param($m) Write-Warning $m }

# Preconditions
if (-not (Test-Path .\config.toml)) { Abort "Run from repo root (config.toml not found)." }
if (-not (Test-Path .\scripts))     { New-Item -ItemType Directory -Path .\scripts -Force | Out-Null }

# Prefer venv python if present
$Py = Join-Path (Join-Path $PWD ".venv\Scripts") "python.exe"
if (-not (Test-Path $Py)) { $Py = "python" }

# ---------------------------------------------------------------------------
# 1) Write scanner that finds risky datetime usage
# ---------------------------------------------------------------------------
$scanPy = @'
#!/usr/bin/env python3
import re, sys, pathlib, json

ROOT = pathlib.Path(".").resolve()
INCLUDE = ["app", "scripts"]
EXCLUDE_DIRS = {".venv", ".git", ".utc_patch_backup", "__pycache__", "tests"}

PATTERNS = {
    "utcnow": re.compile(r"\bdatetime\.utcnow\s*\("),
    "now_empty": re.compile(r"\bdatetime\.now\s*\(\s*\)"),
    "fromiso_z": re.compile(r"datetime\.fromisoformat\s*\("),  # general catch; we normalize usage in patcher
}

def should_scan(p: pathlib.Path) -> bool:
    if p.suffix != ".py": return False
    if any(part in EXCLUDE_DIRS for part in p.parts): return False
    return p.parts[0] in INCLUDE

hits = []
for path in ROOT.rglob("*.py"):
    if not should_scan(path): continue
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        continue
    found = {k: bool(rx.search(text)) for k, rx in PATTERNS.items()}
    if any(found.values()):
        hits.append({"path": str(path.relative_to(ROOT)), **found})

print(json.dumps({"hits": hits}, indent=2))
'@
Set-Content -Encoding UTF8 -Path .\scripts\scan_naive_datetimes.py -Value $scanPy

# ---------------------------------------------------------------------------
# 2) Write patcher (Tier 1 + Tier 2)
# ---------------------------------------------------------------------------
$patchPy = @'
#!/usr/bin/env python3
"""
UTC unify patcher:
  - Ensures app/utils/timeutils.py exposes: now_utc(), to_rfc3339(), parse_iso8601_utc().
  - Replaces datetime.utcnow() and bare datetime.now() with now_utc() in targeted files.
  - Replaces manual fromisoformat(... replace('Z','+00:00')) with parse_iso8601_utc(...).
  - Adds "from app.utils.timeutils import now_utc, parse_iso8601_utc" if missing.
  - Normalizes .isoformat() writes on key fields to use trailing 'Z'.
Backups are written under .utc_patch_backup/
"""
from __future__ import annotations
import re, sys, shutil
from pathlib import Path

ROOT = Path(".").resolve()
BACKUP = ROOT/".utc_patch_backup"
BACKUP.mkdir(exist_ok=True)

TARGETS = [
  "app/auth.py",
  "app/utils/validators.py",
  "app/utils/timeutils.py",
  "app/schemas/timesales.py",
  "app/schemas/options.py",
  "app/writers.py",
  "app/timesales.py",
  "app/healthcheck.py",
  "app/utils/types.py",
  "app/utils/hashing.py",
]

ADD_IMPORT = "from app.utils.timeutils import now_utc, parse_iso8601_utc"
ISO_WRITE_KEYS = ("expires_at", "created_at", "dt_utc", " ts ", "\"ts\"", "'ts'")

RX_NOW_EMPTY = re.compile(r"\bdatetime\.now\s*\(\s*\)")
RX_UTCNOW    = re.compile(r"\bdatetime\.utcnow\s*\(\s*\)")
RX_REPLACE_Z = re.compile(r"datetime\.fromisoformat\s*\(\s*([^)]+?)\s*\)\.replace\(\s*['\"]Z['\"]\s*,\s*['\"]\+00:00['\"]\s*\)")
RX_FROMISO   = re.compile(r"datetime\.fromisoformat\s*\(")
RX_HAS_IMPORT = re.compile(r"from\s+app\.utils\.timeutils\s+import\s+now_utc\s*,\s*parse_iso8601_utc")

def backup(path: Path):
    dst = BACKUP / path
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dst)

def ensure_timeutils(path: Path):
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    need_now   = "def now_utc(" not in text
    need_rfc   = "def to_rfc3339(" not in text
    need_parse = "def parse_iso8601_utc(" not in text
    if not (need_now or need_rfc or need_parse):
        return False
    backup(path)
    if not text:
        text = ""
    pieces = [text, "\n\n# --- UTC helpers (injected) ---\n"]
    if need_now:
        pieces.append(
            "from datetime import datetime, timezone\n"
            "def now_utc() -> datetime:\n"
            "    return datetime.now(timezone.utc)\n"
        )
    if need_rfc:
        pieces.append(
            "def to_rfc3339(dt) -> str:\n"
            "    if dt is None: return ''\n"
            "    try:\n"
            "        s = dt.isoformat()\n"
            "        return s.replace('+00:00','Z') if '+00:00' in s else s\n"
            "    except Exception:\n"
            "        return str(dt)\n"
        )
    if need_parse:
        pieces.append(
            "from datetime import datetime, timezone\n"
            "def parse_iso8601_utc(value):\n"
            "    if not value: return None\n"
            "    if isinstance(value, datetime):\n"
            "        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)\n"
            "    try:\n"
            "        dt = datetime.fromisoformat(str(value).replace('Z','+00:00'))\n"
            "        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)\n"
            "    except Exception:\n"
            "        return None\n"
        )
    path.write_text(\"\".join(pieces), encoding=\"utf-8\")
    return True

def add_import_block(text: str) -> str:
    if RX_HAS_IMPORT.search(text):
        return text
    lines = text.splitlines()
    # insert after leading shebang/comments and existing imports
    insert_at = 0
    for i, line in enumerate(lines[:50]):
        if line.startswith(\"#\") or line.startswith(\"\\\"\\\"\") or not line.strip():
            insert_at = i + 1
            continue
        if line.startswith(\"import \") or line.startswith(\"from \"):
            insert_at = i + 1
            continue
        break
    lines.insert(insert_at, ADD_IMPORT)
    return \"\\n\".join(lines)

def patch_file(path: Path, dry: bool=False):
    if not path.exists(): return None
    original = text = path.read_text(encoding=\"utf-8\")

    # timeutils ensure helpers
    if path.name == "timeutils.py":
        ensured = ensure_timeutils(path)
        if ensured and dry:
            # restore original if dry run
            path.write_text(original, encoding=\"utf-8\")
        # continue to general patches too

    # add import
    text = add_import_block(text)

    # replace utcnow() and bare now()
    text = RX_UTCNOW.sub(\"now_utc()\", text)
    text = RX_NOW_EMPTY.sub(\"now_utc()\", text)

    # normalize fromisoformat Z usage to parse helper
    text = RX_REPLACE_Z.sub(r\"parse_iso8601_utc(\\1)\", text)

    # For generic fromisoformat occurrences, prefer wrapping with parse helper where safe
    # (we only replace when pattern is exactly datetime.fromisoformat(<expr>))
    # This is conservative; manual follow-up is OK for complex cases.
    # No-op here; RX_FROMISO is used for scanning only.

    # normalize isoformat writes on known keys: add trailing Z if missing
    new_lines = []
    for l in text.splitlines():
        needs = any(k in l for k in ISO_WRITE_KEYS)
        if needs and \".isoformat()\" in l and \".replace(\" not in l:
            l = l.replace(\".isoformat()\", \".isoformat().replace('+00:00','Z')\")
        new_lines.append(l)
    text = \"\\n\".join(new_lines)

    if text != original:
        if not dry:
            backup(path)
            path.write_text(text, encoding=\"utf-8\")
        return True
    return False

def main():
    dry = \"--dry\" in sys.argv
    changed = []
    for rel in TARGETS:
        p = ROOT/rel
        res = patch_file(p, dry=dry)
        if res:
            changed.append(rel)
    print({\"changed\": changed, \"dry\": dry})

if __name__ == \"__main__\":
    main()
'@
Set-Content -Encoding UTF8 -Path .\scripts\utc_unify_patch.py -Value $patchPy

# ---------------------------------------------------------------------------
# 3) Scan (pre), patch, scan (post)
# ---------------------------------------------------------------------------
Info "Scanning for risky datetime usage (before patch)..."
& $Py -m scripts.scan_naive_datetimes | Out-Host

Info ("Applying UTC patcher" + ($(if ($DryRun){" (DRY RUN)"} else {""})))
$patchArgs = @()
if ($DryRun) { $patchArgs += "--dry" }
& $Py -m scripts.utc_unify_patch @patchArgs | Out-Host
Ok "UTC patcher finished."

Info "Scanning for risky datetime usage (after patch)..."
& $Py -m scripts.scan_naive_datetimes | Out-Host

if ($NoSmoke) { Ok "Skipping smoke tests by request."; exit 0 }

# ---------------------------------------------------------------------------
# 4) Smoke tests (no Bash heredocs; write temp .py files and run)
# ---------------------------------------------------------------------------
$tmp = ".\.tmp_utc_patch"
New-Item -ItemType Directory -Path $tmp -Force | Out-Null

$smokeToken = @'
import asyncio, json
try:
    from app.config_loader import Config
except ModuleNotFoundError:
    from app.config import Config
from app.auth import AuthManager

async def main():
    cfg = Config()
    auth = AuthManager(cfg)
    try:
        tok = await auth.get_access_token("default")
        print("access_token_ok:", bool(tok))
    except Exception as e:
        print("access_token_error:", type(e).__name__, str(e)[:200])
asyncio.run(main())
'@
Set-Content -Encoding UTF8 -Path "$tmp\smoke_token.py" -Value $smokeToken
Info "Token validity smoke..."
& $Py "$tmp\smoke_token.py" | Out-Host

$smokeQuotes = @'
import asyncio, json
try:
    from app.config_loader import Config
except ModuleNotFoundError:
    from app.config import Config
from app.auth import AuthManager
from app.providers import schwab as S

async def main():
    cfg = Config()
    auth = AuthManager(cfg)
    client = S.SchwabClient(auth=auth, config=cfg)
    out = await client.quotes(["ES","NQ"])
    ok = (out or {}).get("validation",{}).get("is_valid")
    print("quotes_valid:", ok, "| reason:", (out or {}).get("validation",{}).get("reason"))
asyncio.run(main())
'@
Set-Content -Encoding UTF8 -Path "$tmp\smoke_quotes.py" -Value $smokeQuotes
Info "Quotes smoke (ES,NQ)..."
& $Py "$tmp\smoke_quotes.py" | Out-Host

Ok "Done. Backups for modified files are under .utc_patch_backup\"
if ($DryRun) {
    Ok "Dry run completed. No files were modified."
} else {
    Ok "UTC patch applied successfully."
}