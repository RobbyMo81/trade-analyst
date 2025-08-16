# scripts/print_access_token.py
import os, argparse, asyncio

try:
    from app.config_loader import Config
except ModuleNotFoundError:
    from app.config import Config  # fallback if loader module name differs

from app.auth import AuthManager

async def run(env: str | None, raw: bool):
    if env:
        os.environ["APP_ENV"] = env  # let Config pick the right env block
    cfg = Config()
    auth = AuthManager(cfg)
    tok = await auth.get_access_token("default")
    print(tok if raw else f"ACCESS_TOKEN={tok}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--env", default=None)
    p.add_argument("--raw", action="store_true", help="print only the token")
    args = p.parse_args()
    asyncio.run(run(args.env, args.raw))
