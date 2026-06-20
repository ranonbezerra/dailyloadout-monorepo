import asyncio
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context
from dailyloadout.config import settings
from dailyloadout.infrastructure.db.base import Base

# Import all models so Alembic can detect them for autogenerate.
from dailyloadout.infrastructure.db.models import (  # noqa: F401
    Capture,
    CaptureCandidate,
    Game,
    LibraryEntry,
    Loadout,
    Mission,
    OAuthIdentity,
    Platform,
    RefreshToken,
    User,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL without connecting to the database (``--sql`` mode).

    Swaps the asyncpg driver for psycopg2 so ``literal_binds`` works.
    """
    sync_url = settings.database_url.replace("+asyncpg", "")
    context.configure(
        url=sync_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection) -> None:  # type: ignore[no-untyped-def]
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Connect to the database and apply migrations directly."""
    connectable = create_async_engine(settings.database_url)

    async with connectable.connect() as connection:
        await connection.run_sync(_do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
