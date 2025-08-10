"""Provider abstractions for external APIs (e.g., Schwab).

Exports factory for obtaining a provider client. This indirection allows
mocking and switching implementations without changing calling code.
"""
from typing import Optional
from .schwab import SchwabClient
from app.config import Config
from app.auth import AuthManager


def get_provider(name: str, config: Config, auth: AuthManager):  # simple factory
    if name.lower() in ("schwab", "default"):
        return SchwabClient(config=config, auth=auth)
    raise ValueError(f"Unknown provider '{name}'")
