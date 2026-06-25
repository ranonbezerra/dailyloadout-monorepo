"""Conversation-thread checkpointer for the Concierge (ROADMAP Epic 16).

``MemorySaver`` loses threads on restart and isn't shared across workers.
``AsyncPostgresSaver`` persists thread state to the existing PostgreSQL so
conversations survive restarts and are resumable. The Postgres saver is
process-lazy — the pool is opened and the checkpoint tables created on first use
— and on any init failure it degrades to the in-memory saver so chat keeps
working.
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog
from langgraph.checkpoint.memory import MemorySaver

from dailyloadout.config import Settings

logger = structlog.get_logger()

# Process-wide in-memory saver: the fallback, and the default for non-postgres
# configs (and tests, where the langgraph agent isn't exercised).
_memory = MemorySaver()
_lock = asyncio.Lock()
_postgres: Any = None
_postgres_tried = False


def to_psycopg_conninfo(database_url: str) -> str:
    """Convert a SQLAlchemy asyncpg URL to a psycopg conninfo string.

    ``AsyncPostgresSaver`` talks to PostgreSQL via psycopg (not asyncpg), so the
    ``+asyncpg`` driver suffix must be dropped.
    """
    return database_url.replace("+asyncpg://", "://")


async def get_checkpointer(settings: Settings) -> Any:
    """Return the configured checkpointer, falling back to the in-memory one.

    ``concierge_checkpointer='postgres'`` persists threads to PostgreSQL; any
    other value (or a Postgres init failure) uses the in-memory saver.
    """
    if settings.concierge_checkpointer != "postgres":
        return _memory
    global _postgres, _postgres_tried
    if not _postgres_tried:
        async with _lock:
            if not _postgres_tried:
                _postgres = await _init_postgres(settings)
                _postgres_tried = True
    return _postgres or _memory


async def _init_postgres(settings: Settings) -> Any:  # pragma: no cover - needs live PG
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from psycopg.rows import dict_row
        from psycopg_pool import AsyncConnectionPool

        pool = AsyncConnectionPool(
            conninfo=to_psycopg_conninfo(settings.database_url),
            open=False,
            kwargs={
                "autocommit": True,
                "prepare_threshold": 0,
                "row_factory": dict_row,
            },
        )
        await pool.open()
        saver = AsyncPostgresSaver(pool)  # type: ignore[arg-type]
        await saver.setup()  # idempotent: creates the checkpoint tables
        logger.info("concierge_postgres_checkpointer_ready")
        return saver
    except Exception:
        logger.warning("concierge_postgres_checkpointer_init_failed", exc_info=True)
        return None
