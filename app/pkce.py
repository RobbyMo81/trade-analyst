from __future__ import annotations
import base64, hashlib, secrets
from dataclasses import dataclass
@dataclass
class PkcePair:
    verifier: str
    challenge: str
    method: str = "S256"
def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")
def generate_pair(length: int = 64) -> PkcePair:
    verifier = _b64url(secrets.token_bytes(length))
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = _b64url(digest)
    return PkcePair(verifier=verifier, challenge=challenge)
