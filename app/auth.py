"""Authentication management for API access"""

import logging
import asyncio
import webbrowser
from typing import Optional, Dict, Any
from urllib.parse import urlencode, parse_qs, urlparse
import aiohttp
import json
import os
import base64
import hashlib
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken
from .config import Config

logger = logging.getLogger(__name__)


class AuthManager:
    """Handles authentication flows and token management"""
    
    def __init__(self, config: Config, env: str = "dev"):
        self.config = config
        self.env = env
        self.tokens = {}
        # Resolve per-env cache path: .cache/{env}/token_cache.json else fallback
        base_cache = self.config.get('runtime.token_cache', 'token_cache.json')
        cache_dir = Path('.cache') / env
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.token_file = str(cache_dir / Path(base_cache).name)
        self.encrypt_tokens = bool(self.config.get('auth.encrypt_tokens', True))
        self._fernet: Optional[Fernet] = None
        if self.encrypt_tokens:
            self._init_cipher()
    
    async def login(self, provider: str = "default") -> bool:
        """
        Initiate OAuth login flow
        
        Args:
            provider: Authentication provider identifier
            
        Returns:
            bool: True if authentication successful
        """
        try:
            logger.info(f"Starting authentication for provider: {provider}")
            
            # Load existing tokens
            await self._load_tokens()
            
            # Check if we have valid tokens
            if await self._is_token_valid(provider):
                logger.info("Valid token found, authentication successful")
                return True
            
            # Simulated mode short-circuits full browser flow
            simulate = self.config.get('auth.simulate', True)
            if simulate:
                logger.info("Simulated auth mode enabled; writing fake token cache")
                self.tokens[provider] = {
                    'access_token': 'SIMULATED',
                    'refresh_token': 'SIMULATED_REFRESH',
                    'expires_at': self._calculate_expiry(3600),
                    'token_type': 'Bearer'
                }
                await self._save_tokens()
                return True

            # Real flow.
            manual_code = os.getenv('MANUAL_OAUTH_CODE')
            if manual_code:
                logger.info("Using manual authorization code from environment")
                if await self.handle_callback(code=manual_code, state="manual", provider=provider):
                    return True
                return False

            auth_url = await self._build_auth_url(provider)
            logger.info(f"Opening browser for authentication: {auth_url}")
            try:
                webbrowser.open(auth_url)
            except Exception as be:
                logger.warning(f"Browser open failed: {be}; provide code manually from: {auth_url}")
            # Attempt lightweight local callback listener if redirect_uri host/port matches localhost
            if await self._attempt_local_callback(provider):
                return True
            # Fallback to manual input prompt (non-interactive environments may skip)
            code = os.getenv('OAUTH_CODE_INPUT') or ''
            if not code:
                try:
                    code = input("Enter authorization code: ").strip()  # pragma: no cover (interactive)
                except Exception:
                    pass
            if code:
                return await self.handle_callback(code=code, state="manual", provider=provider)
            logger.error("Authorization code not obtained")
            return False
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    async def refresh_token(self, provider: str) -> bool:
        """
        Refresh access token using refresh token
        
        Args:
            provider: Authentication provider identifier
            
        Returns:
            bool: True if refresh successful
        """
        try:
            logger.info(f"Refreshing token for provider: {provider}")
            
            provider_config = self.config.get_auth_config(provider)
            if not provider_config:
                logger.error(f"No configuration found for provider: {provider}")
                return False
            
            refresh_token = self.tokens.get(provider, {}).get('refresh_token')
            if not refresh_token:
                logger.error(f"No refresh token found for provider: {provider}")
                return False

            token_url = provider_config.get('token_url') or 'https://example.com/token'
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
                'client_id': provider_config.get('client_id', ''),
                'client_secret': provider_config.get('client_secret', ''),
            }
            # Optional: redirect_uri sometimes required by providers
            if provider_config.get('redirect_uri'):
                data['redirect_uri'] = provider_config.get('redirect_uri')

            new_tokens = await self._request_token(token_url, data)
            if not new_tokens or 'access_token' not in new_tokens:
                logger.error("Refresh failed: no access_token in response")
                return False

            # Update token payload preserving refresh token if not rotated
            self.tokens[provider]['access_token'] = new_tokens.get('access_token')
            self.tokens[provider]['expires_at'] = self._calculate_expiry(new_tokens.get('expires_in', 3600))
            if new_tokens.get('refresh_token'):
                self.tokens[provider]['refresh_token'] = new_tokens.get('refresh_token')
            self.tokens[provider]['token_type'] = new_tokens.get('token_type', self.tokens[provider].get('token_type', 'Bearer'))

            await self._save_tokens()
            logger.info("Token refresh successful")
            return True
            
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            return False
    
    async def get_access_token(self, provider: str) -> Optional[str]:
        """
        Get valid access token for provider
        
        Args:
            provider: Authentication provider identifier
            
        Returns:
            str: Access token if available and valid
        """
        await self._load_tokens()
        
        if await self._is_token_valid(provider):
            return self.tokens.get(provider, {}).get('access_token')
        
        # Try to refresh token
        if await self.refresh_token(provider):
            return self.tokens.get(provider, {}).get('access_token')
        
        return None
    
    async def handle_callback(self, code: str, state: str, provider: str) -> bool:
        """
        Handle OAuth callback with authorization code
        
        Args:
            code: Authorization code from OAuth provider
            state: State parameter for CSRF protection
            provider: Authentication provider identifier
            
        Returns:
            bool: True if token exchange successful
        """
        try:
            logger.info(f"Handling OAuth callback for provider: {provider}")
            
            # Verify state parameter for CSRF protection if we have stored state
            stored = self._load_pkce_state().get(provider, {})
            expected_state = stored.get('state')
            if expected_state and expected_state != state:
                logger.error(f"State mismatch: expected {expected_state} got {state}")
                return False
            
            # Exchange code for tokens
            tokens = await self._exchange_code_for_tokens(code, provider)
            if not tokens:
                logger.error("Failed to exchange code for tokens")
                return False
            
            # Store tokens
            self.tokens[provider] = {
                'access_token': tokens.get('access_token'),
                'refresh_token': tokens.get('refresh_token'),
                'expires_at': self._calculate_expiry(tokens.get('expires_in', 3600)),
                'token_type': tokens.get('token_type', 'Bearer')
            }
            
            await self._save_tokens()
            # Clear pkce state for provider after successful exchange
            if stored:
                self._clear_pkce_state(provider)
            logger.info("Authentication successful, tokens saved")
            
            return True
            
        except Exception as e:
            logger.error(f"Callback handling failed: {e}")
            return False
    
    async def _build_auth_url(self, provider: str) -> str:
        """Build OAuth authorization URL including PKCE parameters if enabled."""
        provider_config = self.config.get_auth_config(provider) or {}
        redirect = provider_config.get('redirect_uri') or self.config.get('env.dev.redirect_uri') or ''
        state = self._generate_state()
        pkce_enabled = bool(self.config.get('auth.pkce', True))
        params = {
            'client_id': provider_config.get('client_id', ''),
            'response_type': 'code',
            'redirect_uri': redirect,
            'scope': provider_config.get('scope', ''),
            'state': state
        }
        if pkce_enabled:
            verifier = self._generate_code_verifier()
            method = self.config.get('auth.pkce_method', 'S256')
            if method.upper() == 'S256':
                challenge = self._code_challenge_s256(verifier)
            else:
                challenge = verifier  # plain fallback
            params['code_challenge'] = challenge
            params['code_challenge_method'] = method
            self._store_pkce_state(provider, state=state, code_verifier=verifier)
        else:
            self._store_pkce_state(provider, state=state, code_verifier=None)
        base = provider_config.get('auth_url') or provider_config.get('authorize_url') or 'https://example.com/oauth'
        return f"{base}?{urlencode(params)}"
    
    async def _exchange_code_for_tokens(self, code: str, provider: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access tokens (adds PKCE verifier if present)."""
        provider_config = self.config.get_auth_config(provider) or {}
        redirect = provider_config.get('redirect_uri') or self.config.get('env.dev.redirect_uri') or ''
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': provider_config.get('client_id', ''),
            'client_secret': provider_config.get('client_secret', ''),
            'redirect_uri': redirect
        }
        stored = self._load_pkce_state().get(provider)
        if stored and stored.get('code_verifier'):
            data['code_verifier'] = stored['code_verifier']
        token_url = provider_config.get('token_url') or 'https://example.com/token'
        return await self._request_token(token_url, data)

    async def _request_token(self, token_url: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Internal helper to POST to token endpoint (facilitates monkeypatching in tests)."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(token_url, data=data) as response:
                    if response.status == 200:
                        return await response.json()
                    text = await response.text()
                    logger.error(f"Token request failed {response.status}: {text[:200]}")
        except Exception as e:
            logger.error(f"Token request exception: {e}")
        return None

    async def _attempt_local_callback(self, provider: str) -> bool:
        """Attempt to start a transient local HTTP server to capture the authorization code.
        Returns True if successful and tokens stored. Best-effort only.
        """
        provider_cfg = self.config.get_auth_config(provider) or {}
        redirect_uri = provider_cfg.get('redirect_uri') or self.config.get('env.dev.redirect_uri')
        if not redirect_uri:
            return False
        parsed = urlparse(redirect_uri)
        if parsed.hostname not in ("127.0.0.1", "localhost"):
            return False
        port = parsed.port or 5000
        path = parsed.path or '/'
        got_code: dict[str, str] = {}
        from http.server import BaseHTTPRequestHandler, HTTPServer  # built-in
        class Handler(BaseHTTPRequestHandler):  # pragma: no cover (network timing complex)
            def do_GET(self):  # noqa: N802
                q = urlparse(self.path)
                if q.path == path:
                    params = parse_qs(q.query)
                    code = params.get('code', [''])[0]
                    state = params.get('state', [''])[0]
                    if code:
                        got_code['code'] = code
                        got_code['state'] = state
                        self.send_response(200)
                        self.send_header('Content-Type', 'text/plain')
                        self.end_headers()
                        self.wfile.write(b"Authorization received. You may close this window.")
                        return
                self.send_response(404)
                self.end_headers()
            def log_message(self, format, *args):  # silence
                return
        try:
            server = HTTPServer((parsed.hostname, port), Handler)
        except Exception as e:
            logger.debug(f"Local callback server not started: {e}")
            return False
        loop = asyncio.get_event_loop()
        def run_server():  # pragma: no cover
            with server:
                server.timeout = 180
                while not got_code:
                    server.handle_request()
        await loop.run_in_executor(None, run_server)
        if 'code' in got_code:
            return await self.handle_callback(got_code['code'], got_code.get('state', ''), provider)
        return False

    # ------------------ Encryption helpers ------------------
    def _init_cipher(self):
        key = os.getenv('TOKEN_ENC_KEY')
        if not key:
            # Generate ephemeral key (not persisted) for dev convenience
            key = Fernet.generate_key().decode('utf-8')
            logger.warning("TOKEN_ENC_KEY not set; generated ephemeral key (tokens won't persist across restarts)")
        # Validate length
        try:
            self._fernet = Fernet(key.encode('utf-8'))
        except Exception as e:
            logger.error(f"Invalid TOKEN_ENC_KEY; encryption disabled: {e}")
            self.encrypt_tokens = False

    def _encrypt(self, data: bytes) -> bytes:
        if not self.encrypt_tokens or not self._fernet:
            return data
        return self._fernet.encrypt(data)

    def _decrypt(self, data: bytes) -> Optional[bytes]:
        if not self.encrypt_tokens or not self._fernet:
            return data
        try:
            return self._fernet.decrypt(data)
        except InvalidToken:
            logger.error("Failed to decrypt token cache (invalid key or corrupted file)")
            return None
    
    async def _is_token_valid(self, provider: str) -> bool:
        """Check if stored token is valid and not expired"""
        token_data = self.tokens.get(provider)
        if not token_data:
            return False
        
        expires_at = token_data.get('expires_at')
        if not expires_at:
            return False
        
        # Check if token expires within next 5 minutes
        expiry_time = datetime.fromisoformat(expires_at)
        return expiry_time > datetime.now() + timedelta(minutes=5)
    
    def _calculate_expiry(self, expires_in: int) -> str:
        """Calculate token expiry time"""
        expiry_time = datetime.now() + timedelta(seconds=expires_in)
        return expiry_time.isoformat()
    
    def _generate_state(self) -> str:
        """Generate state parameter for CSRF protection"""
        return secrets.token_urlsafe(32)

    # ------------------ PKCE helpers & state persistence ------------------
    def _generate_code_verifier(self, length: int = 64) -> str:
        raw = secrets.token_urlsafe(length)
        return raw[:128]  # ensure within RFC length

    def _code_challenge_s256(self, verifier: str) -> str:
        digest = hashlib.sha256(verifier.encode('ascii')).digest()
        return base64.urlsafe_b64encode(digest).decode('ascii').rstrip('=')

    def _pkce_state_path(self) -> Path:
        fname = self.config.get('runtime.pkce_state_file', 'pkce_state.json')
        cache_dir = Path('.cache') / self.env
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / fname

    def _load_pkce_state(self) -> Dict[str, Dict[str, Optional[str]]]:
        p = self._pkce_state_path()
        try:
            if p.exists():
                return json.loads(p.read_text())
        except Exception as e:
            logger.debug(f"Failed loading pkce state: {e}")
        return {}

    def _save_pkce_state(self, data: Dict[str, Dict[str, Optional[str]]]):
        p = self._pkce_state_path()
        try:
            p.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning(f"Failed saving pkce state: {e}")

    def _store_pkce_state(self, provider: str, state: str, code_verifier: Optional[str]):
        data = self._load_pkce_state()
        data[provider] = {'state': state, 'code_verifier': code_verifier}  # type: ignore[assignment]
        self._save_pkce_state(data)

    def _clear_pkce_state(self, provider: str):
        data = self._load_pkce_state()
        if provider in data:
            del data[provider]
            self._save_pkce_state(data)
    
    async def _load_tokens(self):
        """Load tokens from file"""
        try:
            with open(self.token_file, 'rb') as f:
                raw = f.read()
            # Detect encryption magic? Use JSON parse attempt first.
            try:
                self.tokens = json.loads(raw.decode('utf-8'))
                return
            except Exception:
                dec = self._decrypt(raw)
                if dec is None:
                    self.tokens = {}
                    return
                try:
                    self.tokens = json.loads(dec.decode('utf-8'))
                except Exception as je:
                    logger.error(f"Failed to parse decrypted token cache: {je}")
                    self.tokens = {}
        except FileNotFoundError:
            self.tokens = {}
        except Exception as e:
            logger.error(f"Failed to load tokens: {e}")
            self.tokens = {}
    
    async def _save_tokens(self):
        """Save tokens to file"""
        try:
            data = json.dumps(self.tokens, indent=2).encode('utf-8')
            enc = self._encrypt(data)
            with open(self.token_file, 'wb') as f:
                f.write(enc)
        except Exception as e:
            logger.error(f"Failed to save tokens: {e}")
