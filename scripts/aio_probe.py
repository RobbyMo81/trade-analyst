# scripts/aio_probe.py
import os, asyncio
import aiohttp


def _read_token(path: str) -> str:
    # Read as text; PowerShell redirection may have written UTF-16 with BOM
    data = None
    # try utf-8 first
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = f.read()
    except Exception:
        try:
            with open(path, 'r', encoding='utf-16') as f:
                data = f.read()
        except Exception:
            # fallback to binary and strip common BOMs
            b = open(path, 'rb').read()
            for bom in [b"\xef\xbb\xbf", b"\xff\xfe", b"\xfe\xff"]:
                if b.startswith(bom):
                    b = b[len(bom):]
                    break
            try:
                data = b.decode('utf-8')
            except Exception:
                data = b.decode('latin1')
    return data.strip() if data else ''


async def main():
    tok = _read_token('.cache/dev/access_token.txt')
    base = os.getenv('SCHWAB_MARKETDATA_BASE', 'https://api.schwabapi.com/marketdata/v1').rstrip('/')
    url = f"{base}/quotes"
    params = {'symbols': 'SPY'}
    headers = {'Authorization': f'Bearer {tok}', 'Accept': 'application/json'}
    print('URL:', url)
    print('Params:', params)
    print('Headers:', {k: (v[:30] + '...' if k == 'Authorization' else v) for k, v in headers.items()})
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            print('Status:', resp.status)
            txt = await resp.text()
            print('Body (first 800 chars):\n', txt[:800])

if __name__ == '__main__':
    asyncio.run(main())
