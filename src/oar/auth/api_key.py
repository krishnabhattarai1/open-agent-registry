"""API key generation, hashing, and verification."""

import hashlib
import secrets

import bcrypt


def create_api_key() -> tuple[str, str, str]:
    """Generate a new API key.

    Returns (raw_key, hashed_key, prefix).
    raw_key is shown to the user exactly once.
    hashed_key is stored in the DB.
    prefix (first 8 chars after 'oar_') is stored indexed for O(1) lookup.
    """
    raw = "oar_" + secrets.token_hex(16)
    prefix = raw[4:12]  # 8 chars after 'oar_'
    hashed = bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()
    return raw, hashed, prefix


def verify_api_key(raw_key: str, hashed_key: str) -> bool:
    """Verify a raw API key against its bcrypt hash."""
    try:
        return bcrypt.checkpw(raw_key.encode(), hashed_key.encode())
    except Exception:
        return False


def extract_bearer_token(authorization: str | None) -> str | None:
    """Extract the token from 'Authorization: Bearer <token>'."""
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1]


def extract_key_prefix(raw_key: str) -> str | None:
    """Extract the 8-char prefix used for DB lookup."""
    if not raw_key.startswith("oar_") or len(raw_key) < 12:
        return None
    return raw_key[4:12]
