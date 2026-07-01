"""Repository for MFA credentials (``user_mfa``) and recovery codes."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from slate.infrastructure.db.models import MfaRecoveryCode, UserMfa


class MfaRepository:
    """Data access for a user's TOTP credential and single-use recovery codes."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── TOTP credential ──
    async def get_for_user(self, user_id: int) -> UserMfa | None:
        """Return the user's MFA row (pending or confirmed), or ``None``."""
        stmt = select(UserMfa).where(UserMfa.user_id == user_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def upsert_pending(self, user_id: int, encrypted_secret: str) -> UserMfa:
        """Create or reset the user's MFA row to a fresh, *unconfirmed* secret."""
        existing = await self.get_for_user(user_id)
        if existing is not None:
            existing.totp_secret = encrypted_secret
            existing.confirmed_at = None
            await self._session.flush()
            return existing
        row = UserMfa(user_id=user_id, totp_secret=encrypted_secret, confirmed_at=None)
        self._session.add(row)
        await self._session.flush()
        return row

    async def confirm(self, user_mfa: UserMfa) -> None:
        """Mark *user_mfa* as active (sets ``confirmed_at``)."""
        user_mfa.confirmed_at = datetime.now(UTC)
        await self._session.flush()

    async def set_last_totp_step(self, user_mfa: UserMfa, step: int) -> None:
        """Record the highest consumed TOTP time-step (replay guard)."""
        user_mfa.last_totp_step = step
        await self._session.flush()

    async def delete_for_user(self, user_id: int) -> None:
        """Remove the MFA credential and every recovery code for *user_id*."""
        await self._session.execute(
            delete(MfaRecoveryCode).where(MfaRecoveryCode.user_id == user_id)
        )
        await self._session.execute(delete(UserMfa).where(UserMfa.user_id == user_id))

    # ── Recovery codes ──
    async def replace_recovery_codes(self, user_id: int, code_hashes: list[str]) -> None:
        """Replace all of *user_id*'s recovery codes with a fresh hashed set."""
        await self._session.execute(
            delete(MfaRecoveryCode).where(MfaRecoveryCode.user_id == user_id)
        )
        for code_hash in code_hashes:
            self._session.add(MfaRecoveryCode(user_id=user_id, code_hash=code_hash))
        await self._session.flush()

    async def get_unused_recovery_code(
        self, user_id: int, code_hash: str
    ) -> MfaRecoveryCode | None:
        """Return the matching *unused* recovery code, or ``None``."""
        stmt = select(MfaRecoveryCode).where(
            MfaRecoveryCode.user_id == user_id,
            MfaRecoveryCode.code_hash == code_hash,
            MfaRecoveryCode.used_at.is_(None),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def mark_recovery_code_used(self, code: MfaRecoveryCode) -> None:
        """Stamp *code* as spent (single-use)."""
        code.used_at = datetime.now(UTC)
        await self._session.flush()

    async def count_unused_recovery_codes(self, user_id: int) -> int:
        """Return how many recovery codes *user_id* still has available."""
        stmt = (
            select(func.count())
            .select_from(MfaRecoveryCode)
            .where(MfaRecoveryCode.user_id == user_id, MfaRecoveryCode.used_at.is_(None))
        )
        return (await self._session.scalar(stmt)) or 0
