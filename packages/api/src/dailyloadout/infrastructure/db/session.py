from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from dailyloadout.config import settings

engine = create_async_engine(settings.database_url, echo=(settings.app_env == "development"))

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield an ``AsyncSession`` for use with FastAPI ``Depends``.

    Commits automatically on success; rolls back on exception.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
