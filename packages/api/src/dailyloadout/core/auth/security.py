"""Security utilities: password hashing, JWT management, refresh tokens."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from dailyloadout.config import settings

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
REFRESH_TOKEN_EXPIRE_DAYS: int = 30

_ALGORITHM = "HS256"
_BCRYPT_ROUNDS = 12

# ---------------------------------------------------------------------------
# Password hashing (bcrypt, 12 rounds)
# ---------------------------------------------------------------------------


def hash_password(password: str) -> str:
    """Return a bcrypt hash of *password*."""
    salt = bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Return ``True`` if *plain* matches *hashed*."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ---------------------------------------------------------------------------
# JWT access tokens
# ---------------------------------------------------------------------------
def create_access_token(
    user_id: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT with *user_id* (public_id UUID string) as ``sub``."""
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": now,
    }
    return str(jwt.encode(payload, settings.secret_key, algorithm=_ALGORITHM))


def decode_access_token(token: str) -> dict[str, object]:
    """Decode and verify *token*; raises ``JWTError`` on failure."""
    return dict(jwt.decode(token, settings.secret_key, algorithms=[_ALGORITHM]))


# ---------------------------------------------------------------------------
# Refresh tokens
# ---------------------------------------------------------------------------
def generate_refresh_token() -> str:
    """Return a cryptographically random URL-safe token (86 chars)."""
    return secrets.token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    """Return the SHA-256 hex digest of *token*."""
    return hashlib.sha256(token.encode()).hexdigest()


__all__ = [
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "REFRESH_TOKEN_EXPIRE_DAYS",
    "JWTError",
    "create_access_token",
    "decode_access_token",
    "generate_refresh_token",
    "hash_password",
    "hash_refresh_token",
    "verify_password",
]
