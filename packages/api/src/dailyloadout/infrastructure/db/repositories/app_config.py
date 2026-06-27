"""Repository for the ``app_config`` runtime-override table."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dailyloadout.infrastructure.db.models import AppConfig, User


class AppConfigRepository:
    """Thin data-access layer around the ``app_config`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, key: str) -> AppConfig | None:
        """Return the override row for *key*, or ``None`` if unset."""
        result = await self._session.execute(select(AppConfig).where(AppConfig.key == key))
        return result.scalar_one_or_none()

    async def list_with_updater(self) -> dict[str, tuple[AppConfig, UUID | None]]:
        """Return every override keyed by ``key``, each paired with the updater's
        public_id (``None`` if the updater row is gone or was a bootstrap write).
        """
        result = await self._session.execute(
            select(AppConfig, User.public_id).outerjoin(User, AppConfig.updated_by == User.id)
        )
        return {row[0].key: (row[0], row[1]) for row in result.all()}

    async def upsert(self, key: str, value: object, updated_by: int | None) -> AppConfig:
        """Insert or update the override for *key* and return the row."""
        row = await self.get(key)
        if row is None:
            row = AppConfig(key=key, value=value, updated_by=updated_by)
            self._session.add(row)
        else:
            row.value = value
            row.updated_by = updated_by
        await self._session.flush()
        return row

    async def delete(self, key: str) -> bool:
        """Delete the override for *key*. Return ``True`` if a row was removed."""
        row = await self.get(key)
        if row is None:
            return False
        await self._session.delete(row)
        await self._session.flush()
        return True
