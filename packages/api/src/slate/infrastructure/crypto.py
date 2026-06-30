"""Symmetric encryption for secrets at rest (e.g. TOTP secrets).

The Fernet key is derived from ``settings.secret_key`` — it lives only in the
environment, never in the database — so a DB-only leak cannot decrypt what we
store. Rotating ``secret_key`` invalidates previously-encrypted values (the user
simply re-enrolls), which is an acceptable trade for not managing a second key.
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from slate.config import settings


def _fernet() -> Fernet:
    """Build a Fernet from a 32-byte key derived from the app secret."""
    digest = hashlib.sha256(f"mfa-secret:{settings.secret_key}".encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plaintext: str) -> str:
    """Return a URL-safe Fernet ciphertext for *plaintext*."""
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(token: str) -> str:
    """Decrypt a Fernet *token*; raise ``ValueError`` if it cannot be decrypted."""
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Could not decrypt secret") from exc
