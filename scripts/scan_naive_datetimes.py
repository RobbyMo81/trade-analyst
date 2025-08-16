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
