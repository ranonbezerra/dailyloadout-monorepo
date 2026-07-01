"""Symmetric encryption for secrets at rest (e.g. TOTP secrets).

The Fernet key is derived from ``settings.secret_key`` — it lives only in the
environment, never in the database — so a DB-only leak cannot decrypt what we store.

Key derivation is **domain-separated via HKDF-SHA256** (``info`` label), so the
at-rest key is cryptographically independent of the same secret's other uses (JWT
signing): recovering one does not hand over the other. A ``MultiFernet`` keeps the
legacy single-SHA256 key as a decrypt-only fallback, so secrets encrypted before the
switch still decrypt (new writes use the HKDF key) — no re-enrolment needed.

Rotating ``secret_key`` still invalidates previously-encrypted values (the user
re-enrols), which is an acceptable trade for not managing a second key.
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from slate.config import settings

_HKDF_INFO = b"slate/mfa-secret/v1"


def _hkdf_key() -> bytes:
    """Domain-separated 32-byte Fernet key via HKDF-SHA256 (the primary key)."""
    raw = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=_HKDF_INFO).derive(
        settings.secret_key.encode()
    )
    return base64.urlsafe_b64encode(raw)


def _legacy_key() -> bytes:
    """Legacy single-SHA256 key — kept only to decrypt pre-rotation ciphertext."""
    digest = hashlib.sha256(f"mfa-secret:{settings.secret_key}".encode()).digest()
    return base64.urlsafe_b64encode(digest)


def _fernet() -> MultiFernet:
    """Encrypt with the HKDF key; decrypt with HKDF, then the legacy key."""
    return MultiFernet([Fernet(_hkdf_key()), Fernet(_legacy_key())])


def encrypt_secret(plaintext: str) -> str:
    """Return a URL-safe Fernet ciphertext for *plaintext* (HKDF key)."""
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(token: str) -> str:
    """Decrypt a Fernet *token* (HKDF or legacy key); raise ``ValueError`` on failure."""
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Could not decrypt secret") from exc
