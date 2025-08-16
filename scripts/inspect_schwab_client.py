# scripts/inspect_schwab_client.py
import os
from app.config import Config
from app.providers.schwab import SchwabClient
from app.auth import AuthManager

cfg = Config()
print('CONFIG file used:', cfg.config_file)
print('config.providers.schwab.marketdata_base ->', cfg.get('providers.schwab.marketdata_base'))
print('env SCHWAB_MARKETDATA_BASE ->', os.getenv('SCHWAB_MARKETDATA_BASE'))
print('auth.simulate ->', cfg.get('auth.simulate', None))

# Create AuthManager (may read token) then client
auth = AuthManager(cfg)
client = SchwabClient(cfg, auth)
print('SchwabClient.base_url ->', repr(client.base_url))
print('SchwabClient.batch_url ->', client._join('/quotes'))
print('SchwabClient._join of /quotes?symbols=SPY ->', client._join('/quotes'))
