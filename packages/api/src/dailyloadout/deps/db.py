"""Database session dependency."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from dailyloadout.infrastructure.db.session import get_session


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yield an ``AsyncSession`` for request-scoped database access."""
    async for session in get_session():
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db)]
