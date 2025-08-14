"""Fully-automated OAuth login with local HTTPS callback.

- Generates a self-signed cert for 127.0.0.1/localhost if missing
- Starts a TLS callback server bound to the redirect URI from config/env
- Opens the system browser to the real authorization URL
- Captures ?code=... and exchanges for tokens automatically

Usage (PowerShell):
  .venv\\Scripts\\python -m scripts.auth_login_auto

Prereqs:
- Set OAUTH_REDIRECT_URI to an https localhost URI present in config auth.registered_uris, e.g.:
    https://127.0.0.1:8443/auth/redirect
"""
from __future__ import annotations

import asyncio
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from pathlib import Path
import ssl
import time

from app.config import Config
from app.auth import AuthManager

# --- Certificate utilities ---

def ensure_self_signed_cert(host: str, cert_dir: Path) -> tuple[Path, Path]:
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    import datetime

    cert_dir.mkdir(parents=True, exist_ok=True)
    key_path = cert_dir / "server.key"
    crt_path = cert_dir / "server.crt"
    if key_path.exists() and crt_path.exists():
        return crt_path, key_path

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Local Dev"),
        x509.NameAttribute(NameOID.COMMON_NAME, host),
    ])
    alt_gns: list[x509.GeneralName] = [x509.DNSName("localhost")]
    # Add IP SAN when host is an IP
    try:
        import ipaddress
        alt_gns.append(x509.IPAddress(ipaddress.ip_address(host)))
    except Exception:
        # Not an IP, skip
        pass

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow() - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
    .add_extension(x509.SubjectAlternativeName(alt_gns), critical=False)
        .sign(key, hashes.SHA256())
    )

    key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    crt_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return crt_path, key_path


def run_tls_callback(auth: AuthManager, host: str, port: int, path: str, stop_event: threading.Event):
    got: dict[str, str] = {}

    class Handler(BaseHTTPRequestHandler):  # pragma: no cover (network timing)
        def do_GET(self):  # noqa: N802
            q = urlparse(self.path)
            if q.path == path:
                params = parse_qs(q.query)
                code = params.get('code', [''])[0]
                state = params.get('state', [''])[0]
                if code:
                    ok = False
                    try:
                        ok = asyncio.run(auth.handle_callback(code, state, provider="default"))
                    except Exception:
                        ok = False
                    self.send_response(200 if ok else 500)
                    self.send_header('Content-Type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b"Authorization received. You may close this window." if ok else b"Token exchange failed.")
                    got['ok'] = '1' if ok else '0'
                    # trigger shutdown without deadlocking
                    threading.Thread(target=server.shutdown, daemon=True).start()
                    return
            self.send_response(404)
            self.end_headers()
        def log_message(self, format, *args):
            return

    server = HTTPServer((host, port), Handler)
    crt_path, key_path = ensure_self_signed_cert(host, Path('.cache') / 'dev' / 'certs')
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(certfile=str(crt_path), keyfile=str(key_path))
    server.socket = ctx.wrap_socket(server.socket, server_side=True)
    with server:
        while not stop_event.is_set():
            server.handle_request()
    return got.get('ok') == '1'


async def open_auth_and_wait(cfg: Config) -> bool:
    auth = AuthManager(cfg, env="dev")
    # Resolve redirect
    redirect = cfg.get('auth.redirect_uri') or cfg.get('env.prod.redirect_uri') or cfg.get('env.dev.redirect_uri')
    if not redirect:
        print("No redirect_uri configured.")
        return False
    u = urlparse(redirect)
    if u.scheme.lower() != 'https' or (u.hostname not in ('127.0.0.1','localhost')):
        print("Redirect must be https and localhost for automated TLS callback.")
        return False
    host, port, path = u.hostname, (u.port or 8443), (u.path or '/')

    # Build auth URL and open browser
    url = await auth._build_auth_url("default")  # internal but OK for CLI helper
    try:
        webbrowser.open(url)
    except Exception as e:
        print("Open browser failed:", e)

    # Start TLS callback server
    stop_event = threading.Event()
    th = threading.Thread(target=run_tls_callback, args=(auth, host, port, path, stop_event), daemon=True)
    th.start()

    # Wait up to 3 minutes
    t0 = time.time()
    while time.time() - t0 < 180:
        if not th.is_alive():
            break
        await asyncio.sleep(0.5)
    stop_event.set()
    th.join(timeout=2)
    # If tokens exist now, consider success
    tok = await auth.get_access_token("default")
    return tok is not None


def main() -> int:
    cfg = Config()
    ok = asyncio.run(open_auth_and_wait(cfg))
    print("login:", ok)
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
