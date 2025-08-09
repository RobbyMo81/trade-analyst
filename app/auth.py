"""Authentication management for API access"""

import logging
import asyncio
import webbrowser
from typing import Optional, Dict, Any
from urllib.parse import urlencode, parse_qs, urlparse
import aiohttp
import json
from datetime import datetime, timedelta
from .config import Config

logger = logging.getLogger(__name__)


class AuthManager:
    """Handles authentication flows and token management"""
    
    def __init__(self, config: Config):
        self.config = config
        self.tokens = {}
        self.token_file = "tokens.json"
    
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
            
            # Start OAuth flow
            auth_url = await self._build_auth_url(provider)
            logger.info(f"Opening browser for authentication: {auth_url}")
            
            # Open browser for user authentication
            webbrowser.open(auth_url)
            
            # Wait for callback (this would be handled by the callback server)
            logger.info("Waiting for authentication callback...")
            # TODO: Implement proper callback handling
            
            return True
            
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
            
            # TODO: Implement token refresh logic
            logger.info("Token refresh successful")
            await self._save_tokens()
            
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
            
            # TODO: Verify state parameter for CSRF protection
            
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
            logger.info("Authentication successful, tokens saved")
            
            return True
            
        except Exception as e:
            logger.error(f"Callback handling failed: {e}")
            return False
    
    async def _build_auth_url(self, provider: str) -> str:
        """Build OAuth authorization URL"""
        provider_config = self.config.get_auth_config(provider)
        
        params = {
            'client_id': provider_config['client_id'],
            'response_type': 'code',
            'redirect_uri': provider_config['redirect_uri'],
            'scope': provider_config.get('scope', ''),
            'state': self._generate_state()
        }
        
        return f"{provider_config['auth_url']}?{urlencode(params)}"
    
    async def _exchange_code_for_tokens(self, code: str, provider: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access tokens"""
        provider_config = self.config.get_auth_config(provider)
        
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': provider_config['client_id'],
            'client_secret': provider_config['client_secret'],
            'redirect_uri': provider_config['redirect_uri']
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(provider_config['token_url'], data=data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Token exchange failed: {response.status}")
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
        import secrets
        return secrets.token_urlsafe(32)
    
    async def _load_tokens(self):
        """Load tokens from file"""
        try:
            with open(self.token_file, 'r') as f:
                self.tokens = json.load(f)
        except FileNotFoundError:
            self.tokens = {}
        except Exception as e:
            logger.error(f"Failed to load tokens: {e}")
            self.tokens = {}
    
    async def _save_tokens(self):
        """Save tokens to file"""
        try:
            with open(self.token_file, 'w') as f:
                json.dump(self.tokens, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save tokens: {e}")
