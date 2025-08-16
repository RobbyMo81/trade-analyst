
# CLI Drop-in

Files:
- start.py  — unified CLI façade using Typer
- pyproject.additions.toml — snippet to add console script entry

## Install dependency
pip install "typer[all]"

## Register console script
Merge `pyproject.additions.toml` into your `pyproject.toml` under `[project]`.
Then in your repo root:
  pip install -e .

## Usage
  python start.py --help
  trade-analyst --help

  python start.py preflight --env dev --reset-cache
  python start.py serve-callback --env dev --port 8443
  python start.py auth-login --env dev
  python start.py quotes ES NQ
  python start.py stress --target scripts.targets:schwab_quotes --concurrency 10 --iterations 300
  python start.py healthcheck
