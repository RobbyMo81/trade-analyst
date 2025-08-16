"""Simple HTTPS callback server that writes a callback artifact.

- Binds to the configured redirect (https://localhost:PORT/PATH)
- On GET, writes .cache/{env}/last_callback.json with code and state

Usage (PowerShell):
  .venv\\Scripts\\python -m scripts.callback_server --env dev --port 8443 --tls
"""
from __future__ import annotations

import argparse, json, ssl
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from pathlib import Path

from app.config import Config


def ensure_self_signed_cert(host: str, cert_dir: Path) -> tuple[Path, Path]:
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    import datetime, ipaddress

    cert_dir.mkdir(parents=True, exist_ok=True)
    key_path = cert_dir / "server.key"
    crt_path = cert_dir / "server.crt"
    # Prefer existing server certs in the cert_dir
    if key_path.exists() and crt_path.exists():
        return crt_path, key_path
    # If mkcert default files exist in project root, adopt them
    root = Path.cwd()
    mkcert_crt = root / "127.0.0.1+1.pem"
    mkcert_key = root / "127.0.0.1+1-key.pem"
    if mkcert_crt.exists() and mkcert_key.exists():
        # Copy to expected filenames
        crt_bytes = mkcert_crt.read_bytes()
        key_bytes = mkcert_key.read_bytes()
        crt_path.write_bytes(crt_bytes)
        key_path.write_bytes(key_bytes)
        return crt_path, key_path

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Local Dev"),
        x509.NameAttribute(NameOID.COMMON_NAME, host),
    ])
    alt = [x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow() - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
        .add_extension(x509.SubjectAlternativeName(alt), critical=False)
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--env', default='dev')
    ap.add_argument('--port', type=int, default=8443)
    ap.add_argument('--tls', action='store_true')
    args = ap.parse_args()

    cfg = Config()
    env = args.env
    redir = cfg.get(f'env.{env}.redirect_uri') or cfg.get('auth.redirect_uri')
    if not redir:
        print('redirect_uri not configured')
        return 1
    u = urlparse(redir)
    host, path = u.hostname or '127.0.0.1', u.path or '/'

    cache_dir = Path('.cache') / env
    cache_dir.mkdir(parents=True, exist_ok=True)
    artifact = cache_dir / 'last_callback.json'

    class Handler(BaseHTTPRequestHandler):  # pragma: no cover
        def do_GET(self):  # noqa: N802
            q = urlparse(self.path)
            if q.path == path:
                params = parse_qs(q.query)
                code = params.get('code', [''])[0]
                state = params.get('state', [''])[0]
                if code:
                    artifact.write_text(json.dumps({'code': code, 'state': state}, indent=2))
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b'OK. You may close this window.')
                    return
            self.send_response(404)
            self.end_headers()
        def log_message(self, format, *args):
            return

    server = HTTPServer((host, args.port), Handler)
    if args.tls:
        crt, key = ensure_self_signed_cert(host, cache_dir / 'certs')
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(certfile=str(crt), keyfile=str(key))
        server.socket = ctx.wrap_socket(server.socket, server_side=True)
    try:
        print(f'Listening on {host}:{args.port}{path} (tls={args.tls})')
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
