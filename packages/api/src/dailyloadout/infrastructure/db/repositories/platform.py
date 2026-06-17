"""Repository for the ``platforms`` table."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dailyloadout.infrastructure.db.models import Platform


class PlatformRepository:
    """Thin data-access layer around the ``platforms`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, platform_id: int) -> Platform | None:
        """Return the platform with the given *platform_id*, or ``None``."""
        stmt = select(Platform).where(Platform.id == platform_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Platform | None:
        """Return the platform with the given *slug*, or ``None``."""
        stmt = select(Platform).where(Platform.slug == slug)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Platform]:
        """Return all platforms ordered by label."""
        stmt = select(Platform).order_by(Platform.label)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
