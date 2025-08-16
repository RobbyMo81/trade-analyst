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
