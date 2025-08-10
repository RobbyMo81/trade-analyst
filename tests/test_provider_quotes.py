import asyncio
from app.config import Config
from app.auth import AuthManager
from app.providers import get_provider

def test_schwab_quotes_simulate():
    cfg = Config()
    cfg.set('auth.simulate', True)
    auth = AuthManager(cfg)
    client = get_provider('schwab', cfg, auth)
    symbols = ['AAPL', 'MSFT']
    result = asyncio.run(client.quotes(symbols))
    assert 'records' in result and 'normalized' in result
    assert len(result['records']) == len(symbols)
    assert result['validation']['is_valid'] is True
    sym_set = {r['symbol'] for r in result['normalized']}
    assert sym_set == {s.upper() for s in symbols}
    for rec in result['records']:
        assert rec['ask'] >= rec['bid']
