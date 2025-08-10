import argparse
import os
import shutil
import subprocess
import sys
from typing import List, Tuple

def _emoji_supports_unicode() -> bool:
    enc = getattr(sys.stdout, "encoding", None) or ""
    return "UTF" in enc.upper()

EMOJI = {
    "rocket": "🚀",
    "check": "✅",
    "x": "❌",
    "warn": "⚠️",
    "info": "📋",
    "pkg": "📦",
    "disk": "💾",
    "globe": "🌐",
    "done": "🎉",
    "chart": "📊",
    "mag": "🔍",
    "spin": "🔄",
    "q": "❓",
}
ASCII = {
    "rocket": "[*]",
    "check": "[OK]",
    "x": "[X]",
    "warn": "[!]",
    "info": "[i]",
    "pkg": "[pkg]",
    "disk": "[commit]",
    "globe": "[net]",
    "done": "[done]",
    "chart": "[status]",
    "mag": "[dry-run]",
    "spin": "[..]",
    "q": "[?]",
}
SYM = EMOJI if _emoji_supports_unicode() and os.environ.get("NO_EMOJI") != "1" else ASCII

def run(cmd: List[str], cwd: str = ".", check: bool = False, capture: bool = False) -> Tuple[int, str]:
    """Run a command; return (returncode, stdout)."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=capture,
        text=True,
        shell=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{result.stderr}")
    return result.returncode, (result.stdout or "").strip()

def print_header():
    print(f"{SYM['rocket']} Trade Analyst Repository Update")

def check_prereqs(repo_root: str) -> None:
    if not os.path.isdir(os.path.join(repo_root, "app")):
        raise SystemExit(f"{SYM['x']} Error: run from trade-analyst root (missing 'app' directory)")
    if shutil.which("git") is None:
        raise SystemExit(f"{SYM['x']} Error: Git is not installed or not in PATH")
    if not os.path.isdir(os.path.join(repo_root, ".git")):
        print(f"{SYM['x']} Error: This is not a git repository")
        print("Please initialize git first with: git init")
        raise SystemExit(1)
    print(f"{SYM['check']} Prerequisites check passed")

def ensure_gitignore(repo_root: str) -> None:
    src = os.path.join(repo_root, "gitignore")
    dst = os.path.join(repo_root, ".gitignore")
    if os.path.isfile(src) and not os.path.isfile(dst):
        print(f"{SYM['spin']} Renaming gitignore to .gitignore...")
        os.replace(src, dst)
        print(f"{SYM['check']} Renamed gitignore to .gitignore")

def show_git_status(repo_root: str) -> None:
    print(f"\n{SYM['info']} Current Git Status:")
    code, out = run(["git", "status", "--porcelain"], repo_root, capture=True)
    print(out)

def show_remotes(repo_root: str) -> None:
    code, out = run(["git", "remote", "-v"], repo_root, capture=True)
    if out.strip():
        print(f"\n{SYM['globe']} Remote repositories:")
        print(out)
    else:
        print(f"\n{SYM['warn']} No remote repositories configured")
        print("To add the GitHub remote, run:")
        print("git remote add origin https://github.com/RobbyMo81/trade-analyst.git")

def detect_sensitive(repo_root: str) -> None:
    candidates = [".env", "tokens", "data", "logs"]
    found = []
    for c in candidates:
        p = os.path.join(repo_root, c)
        if os.path.exists(p):
            found.append(c + ("/" if os.path.isdir(p) else ""))
    if found:
        print(f"\n{SYM['warn']} Sensitive files/directories detected:")
        for f in found:
            print(f"   - {f}")
        print("These should be in .gitignore (they are expected to be).")

def dry_run(repo_root: str) -> None:
    print(f"\n{SYM['mag']} DRY RUN MODE - No changes will be made")
    print("Files that would be added:")
    code, out = run(["git", "add", "--dry-run", "."], repo_root, capture=True)
    print(out)

def confirm_proceed(force: bool) -> None:
    if force:
        return
    ans = input(f"\n{SYM['q']} Proceed with updating the repository? [Y/N]: ").strip().lower()
    if ans != "y":
        print(f"{SYM['x']} Operation cancelled")
        raise SystemExit(0)

def stage_all(repo_root: str) -> None:
    print(f"\n{SYM['pkg']} Staging files...")
    code, _ = run(["git", "add", "."], repo_root, capture=True)
    if code != 0:
        raise SystemExit(f"{SYM['x']} Failed to stage files")

def show_cached_diff(repo_root: str) -> None:
    print(f"\n{SYM['info']} Files to be committed:")
    code, out = run(["git", "diff", "--cached", "--name-status"], repo_root, capture=True)
    print(out)

def commit_changes(repo_root: str, message: str) -> None:
    print(f"\n{SYM['disk']} Committing changes...")
    code, out = run(["git", "commit", "-m", message], repo_root, capture=True)
    if code == 0:
        print(f"{SYM['check']} Commit successful!")
    else:
        print(out)
        raise SystemExit(f"{SYM['x']} Commit failed")

def push_if_origin(repo_root: str) -> None:
    # Check for origin
    code, url = run(["git", "remote", "get-url", "origin"], repo_root, capture=True)
    if code != 0 or not url:
        print(f"\n{SYM['warn']} No origin remote found. Add it with:")
        print("git remote add origin https://github.com/RobbyMo81/trade-analyst.git")
        print("Then run: git push -u origin main")
        return

    print(f"\n{SYM['rocket']} Pushing to GitHub...")
    _, branch = run(["git", "branch", "--show-current"], repo_root, capture=True)
    branch = branch.strip() or "main"
    print(f"Current branch: {branch}")
    code, out = run(["git", "push", "origin", branch], repo_root, capture=True)
    if code == 0:
        print(f"{SYM['check']} Push successful!")
        print(f"{SYM['globe']} Repository updated at: https://github.com/RobbyMo81/trade-analyst")
    else:
        print(f"{SYM['x']} Push failed")
        print(out)
        print("You may need to pull first if the remote has changes:")
        print(f"git pull origin {branch}")

def final_status(repo_root: str) -> None:
    print(f"\n{SYM['done']} Repository update complete!")
    print(f"\n{SYM['chart']} Final Status:")
    code, out = run(["git", "status"], repo_root, capture=True)
    print(out)

from typing import Optional

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Update the trade-analyst Git repository.")
    parser.add_argument("--commit-message", "-m", default="Update trade-analyst application with complete implementation")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Skip confirmation")
    parser.add_argument("--repo-root", default=".", help="Path to the repo root (default: .)")

    args = parser.parse_args(argv)
    repo_root = os.path.abspath(args.repo_root)

    print_header()
    try:
        check_prereqs(repo_root)
        ensure_gitignore(repo_root)
        show_git_status(repo_root)
        show_remotes(repo_root)
        detect_sensitive(repo_root)

        if args.dry_run:
            dry_run(repo_root)
            return 0

        confirm_proceed(args.force)
        stage_all(repo_root)
        show_cached_diff(repo_root)
        commit_changes(repo_root, args.commit_message)
        push_if_origin(repo_root)
        final_status(repo_root)
        return 0
    except KeyboardInterrupt:
        print(f"\n{SYM['x']} Aborted by user")
        return 130
    except SystemExit as se:
        return int(se.code) if isinstance(se.code, int) else 1
    except Exception as e:
        print(f"{SYM['x']} Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
