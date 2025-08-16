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
