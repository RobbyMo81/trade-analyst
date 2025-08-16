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
