from __future__ import annotations
import toml
def load_config() -> dict:
    return toml.load("config.toml")
