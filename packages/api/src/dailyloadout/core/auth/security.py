"""Security utilities: password hashing, JWT management, refresh tokens."""

from __future__ import annotations

import functools
import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from jwt import PyJWTError

from dailyloadout.config import settings

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
REFRESH_TOKEN_EXPIRE_DAYS: int = 30

_ALGORITHM = "HS256"

# ---------------------------------------------------------------------------
# Password hashing (bcrypt)
# ---------------------------------------------------------------------------


def hash_password(password: str) -> str:
    """Return a bcrypt hash of *password*."""
    salt = bcrypt.gensalt(rounds=settings.bcrypt_rounds)
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Return ``True`` if *plain* matches *hashed*."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


@functools.lru_cache(maxsize=4)
def _dummy_hash(rounds: int) -> bytes:
    """A throwaway bcrypt hash at *rounds*, computed once per rounds value.

    Used to equalise login timing on the no-user branch. Generated at the SAME
    cost factor as real password hashes (``settings.bcrypt_rounds``) so the dummy
    verification takes the same time as a real one — exact timing parity, and
    fast when the test config lowers the rounds.
    """
    return bcrypt.hashpw(b"timing-equaliser", bcrypt.gensalt(rounds=rounds))


def verify_password_dummy(plain: str) -> None:
    """Run a throwaway bcrypt verification to equalise login timing.

    Called on the "no such user" branch of login so an attacker cannot tell a
    missing account from a wrong password by response time. The return value is
    intentionally ignored (login fails regardless).
    """
    bcrypt.checkpw(plain.encode(), _dummy_hash(settings.bcrypt_rounds))


# ---------------------------------------------------------------------------
# JWT access tokens
# ---------------------------------------------------------------------------
def create_access_token(
    user_id: str,
    token_version: int,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT with *user_id* (public_id UUID string) as ``sub``.

    The ``tv`` claim carries the user's ``token_version``: ``get_current_user``
    rejects the token when it no longer matches the DB value, so bumping
    ``token_version`` instantly kills every outstanding access token.
    """
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {
        "sub": user_id,
        "tv": token_version,
        "exp": expire,
        "iat": now,
    }
    return str(jwt.encode(payload, settings.secret_key, algorithm=_ALGORITHM))


def decode_access_token(token: str) -> dict[str, object]:
    """Decode and verify *token*; raises ``JWTError`` on failure."""
    return dict(jwt.decode(token, settings.secret_key, algorithms=[_ALGORITHM]))


# ---------------------------------------------------------------------------
# Email-verification tokens (signed, purpose-scoped, time-limited)
# ---------------------------------------------------------------------------
_EMAIL_VERIFY_PURPOSE = "email_verify"


def create_email_verification_token(public_id: str) -> str:
    """Create a signed, time-limited token for verifying *public_id*'s email.

    The token is purpose-scoped (``purpose="email_verify"``) so it can never be
    used as an access token, and expires after ``email_verification_ttl_hours``.
    No DB row is needed: single-use is enforced by the user's ``email_verified``
    flag (verifying again is an idempotent no-op).
    """
    now = datetime.now(UTC)
    expire = now + timedelta(hours=settings.email_verification_ttl_hours)
    payload = {
        "sub": public_id,
        "purpose": _EMAIL_VERIFY_PURPOSE,
        "exp": expire,
        "iat": now,
    }
    return str(jwt.encode(payload, settings.secret_key, algorithm=_ALGORITHM))


def decode_email_verification_token(token: str) -> str:
    """Decode an email-verification *token* and return its subject public_id.

    Raises:
        ValueError: if the token is invalid, expired, or not purpose-scoped to
            email verification.
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[_ALGORITHM])
    except PyJWTError as exc:
        raise ValueError("Invalid or expired verification token") from exc

    if payload.get("purpose") != _EMAIL_VERIFY_PURPOSE:
        raise ValueError("Invalid or expired verification token")

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise ValueError("Invalid or expired verification token")

    return subject


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
    "PyJWTError",
    "create_access_token",
    "create_email_verification_token",
    "decode_access_token",
    "decode_email_verification_token",
    "generate_refresh_token",
    "hash_password",
    "hash_refresh_token",
    "verify_password",
    "verify_password_dummy",
]
