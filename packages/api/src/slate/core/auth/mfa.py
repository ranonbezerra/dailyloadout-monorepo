"""TOTP multi-factor authentication: enroll, confirm, verify, disable.

Flow: ``start_enrollment`` generates a pending secret (shown as a QR/otpauth
URI); ``confirm_enrollment`` activates it once the user proves possession and
returns one-time recovery codes; ``verify_challenge`` is the login second factor
(a TOTP code or a single-use recovery code). The secret is encrypted at rest via
:mod:`slate.infrastructure.crypto`; only SHA-256 hashes of recovery codes are
stored.
"""

from __future__ import annotations

import hashlib
import re
import secrets

import pyotp

from slate.config import settings
from slate.infrastructure.crypto import decrypt_secret, encrypt_secret
from slate.infrastructure.db.models import User, UserMfa
from slate.infrastructure.db.repositories.mfa import MfaRepository

__all__ = ["MfaService"]

_RECOVERY_CODE_COUNT = 10
# Accept the adjacent 30s step on each side to tolerate clock skew.
_TOTP_VALID_WINDOW = 1


def _canonicalize_recovery_code(code: str) -> str:
    """Lowercase and strip non-alphanumerics so format/case don't matter."""
    return re.sub(r"[^a-z0-9]", "", code.lower())


def _hash_recovery_code(code: str) -> str:
    """SHA-256 of the canonical recovery code (high-entropy → fast hash is fine)."""
    return hashlib.sha256(_canonicalize_recovery_code(code).encode()).hexdigest()


def _generate_recovery_codes(count: int) -> list[str]:
    """Return *count* readable single-use codes formatted ``xxxxx-xxxxx``."""
    codes = []
    for _ in range(count):
        raw = secrets.token_hex(5)  # 10 lowercase hex chars
        codes.append(f"{raw[:5]}-{raw[5:]}")
    return codes


class MfaService:
    """Orchestrates TOTP enrollment, login challenge, and recovery codes."""

    def __init__(self, mfa_repo: MfaRepository) -> None:
        self._repo = mfa_repo

    async def is_enabled(self, user_id: int) -> bool:
        """True only when the user has a *confirmed* MFA credential."""
        row = await self._repo.get_for_user(user_id)
        return row is not None and row.confirmed_at is not None

    async def status(self, user_id: int) -> tuple[bool, int]:
        """Return ``(enabled, unused_recovery_code_count)`` for the UI."""
        row = await self._repo.get_for_user(user_id)
        if row is None or row.confirmed_at is None:
            return False, 0
        return True, await self._repo.count_unused_recovery_codes(user_id)

    async def start_enrollment(self, user: User) -> tuple[str, str]:
        """Generate a fresh *pending* secret; return ``(secret, otpauth_uri)``.

        Raises:
            ValueError: if MFA is already enabled (disable it first).
        """
        existing = await self._repo.get_for_user(user.id)
        if existing is not None and existing.confirmed_at is not None:
            raise ValueError("MFA is already enabled")
        secret = pyotp.random_base32()
        await self._repo.upsert_pending(user.id, encrypt_secret(secret))
        uri = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name=settings.mfa_issuer)
        return secret, uri

    async def confirm_enrollment(self, user: User, code: str) -> list[str]:
        """Verify the first code, activate MFA, and return one-time recovery codes.

        Raises:
            ValueError: if there is no pending enrollment or the code is wrong.
        """
        row = await self._repo.get_for_user(user.id)
        if row is None or row.confirmed_at is not None:
            raise ValueError("No pending MFA enrollment")
        if not self._verify_totp(row, code):
            raise ValueError("Invalid verification code")
        await self._repo.confirm(row)
        codes = _generate_recovery_codes(_RECOVERY_CODE_COUNT)
        await self._repo.replace_recovery_codes(user.id, [_hash_recovery_code(c) for c in codes])
        return codes

    async def regenerate_recovery_codes(self, user: User, code: str) -> list[str]:
        """Replace the recovery-code set after verifying a current factor.

        Raises:
            ValueError: if MFA is not enabled or the code is invalid.
        """
        row = await self._require_enabled(user.id)
        if not await self._verify_any(user.id, row, code):
            raise ValueError("Invalid verification code")
        codes = _generate_recovery_codes(_RECOVERY_CODE_COUNT)
        await self._repo.replace_recovery_codes(user.id, [_hash_recovery_code(c) for c in codes])
        return codes

    async def disable(self, user: User, code: str) -> None:
        """Disable MFA after verifying a current TOTP or recovery code.

        Raises:
            ValueError: if MFA is not enabled or the code is invalid.
        """
        row = await self._require_enabled(user.id)
        if not await self._verify_any(user.id, row, code):
            raise ValueError("Invalid verification code")
        await self._repo.delete_for_user(user.id)

    async def verify_challenge(self, user_id: int, code: str) -> bool:
        """Login second factor: accept a TOTP code or consume a recovery code."""
        row = await self._repo.get_for_user(user_id)
        if row is None or row.confirmed_at is None:
            return False
        return await self._verify_any(user_id, row, code)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    async def _require_enabled(self, user_id: int) -> UserMfa:
        row = await self._repo.get_for_user(user_id)
        if row is None or row.confirmed_at is None:
            raise ValueError("MFA is not enabled")
        return row

    @staticmethod
    def _verify_totp(row: UserMfa, code: str) -> bool:
        secret = decrypt_secret(row.totp_secret)
        return bool(pyotp.TOTP(secret).verify(code.strip(), valid_window=_TOTP_VALID_WINDOW))

    async def _verify_any(self, user_id: int, row: UserMfa, code: str) -> bool:
        """Accept a valid TOTP code, else a single-use recovery code (consumed)."""
        if self._verify_totp(row, code):
            return True
        recovery = await self._repo.get_unused_recovery_code(user_id, _hash_recovery_code(code))
        if recovery is not None:
            await self._repo.mark_recovery_code_used(recovery)
            return True
        return False
