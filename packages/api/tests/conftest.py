"""Shared test fixtures for DailyLoadout API tests.

Uses an in-memory SQLite database (via aiosqlite) so that tests never
depend on a running PostgreSQL instance.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import BigInteger, Integer, SmallInteger, Text, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# SQLite compatibility: render BigInteger as plain INTEGER so that SQLite
# autoincrement works correctly (SQLite only auto-increments INTEGER PKs).
# ---------------------------------------------------------------------------
from sqlalchemy.ext.compiler import compiles  # noqa: E402
from sqlalchemy.types import TypeDecorator

from dailyloadout.infrastructure.db.base import Base
from dailyloadout.infrastructure.db.models import (
    Capture,  # noqa: F401  — ensure models registered
    CaptureCandidate,  # noqa: F401  — ensure models registered
    Game,
    LibraryEntry,  # noqa: F401  — ensure models registered
    Loadout,  # noqa: F401  — ensure models registered
    Mission,  # noqa: F401  — ensure models registered
    Platform,  # noqa: F401  — ensure models registered
    User,  # noqa: F401  — ensure models registered
)


@compiles(BigInteger, "sqlite")
def _bi_to_int(element: BigInteger, compiler: Any, **kw: Any) -> str:  # noqa: ARG001
    return compiler.visit_INTEGER(Integer(), **kw)


@compiles(SmallInteger, "sqlite")
def _si_to_int(element: SmallInteger, compiler: Any, **kw: Any) -> str:  # noqa: ARG001
    return compiler.visit_INTEGER(Integer(), **kw)


# ---------------------------------------------------------------------------
# SQLite compatibility: PostgreSQL ARRAY(String) → JSON text in SQLite.
# We monkey-patch the Game.genres column type so that create_all() produces
# a TEXT column and the ORM transparently serialises lists as JSON strings.
# ---------------------------------------------------------------------------


class _JSONEncodedList(TypeDecorator):
    """Store a Python list as a JSON string in SQLite."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: list[str] | None, dialect: Any) -> str | None:  # noqa: ARG002
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(self, value: str | None, dialect: Any) -> list[str] | None:  # noqa: ARG002
        if value is None:
            return None
        return json.loads(value)


# Swap ARRAY(String) column types at import time, before create_all() runs.
Game.__table__.c.genres.type = _JSONEncodedList()
CaptureCandidate.__table__.c.igdb_genres.type = _JSONEncodedList()

# Swap JSONB → JSON-encoded TEXT for SQLite.
Mission.__table__.c.extracted_state.type = _JSONEncodedList()


# ---------------------------------------------------------------------------
# Test-scoped async SQLite engine
# ---------------------------------------------------------------------------
_TEST_DATABASE_URL = "sqlite+aiosqlite://"

_test_engine = create_async_engine(
    _TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

_TestSessionFactory = async_sessionmaker(
    _test_engine,
    expire_on_commit=False,
)


@event.listens_for(_test_engine.sync_engine, "connect")
def _enable_sqlite_fks(dbapi_connection: Any, _connection_record: Any) -> None:
    """Enable foreign-key enforcement on every new SQLite connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# SQLite compatibility: remove indexes that use features unsupported by SQLite
# (GIN, NULLS LAST, etc.).  This must happen once, before any create_all().
# ---------------------------------------------------------------------------

_SQLITE_INCOMPATIBLE_INDEXES = {
    "idx_games_title_trgm",  # GIN + pg_trgm
    "idx_library_user_last_played",  # NULLS LAST
    "idx_captures_created",  # created_at DESC expression
    "idx_missions_user_active",  # partial unique (WHERE ended_at IS NULL)
    "idx_missions_entry_ended",  # DESC expression
    "idx_loadouts_user_created",  # DESC expression
}

for _table in Base.metadata.tables.values():
    _to_remove = [idx for idx in _table.indexes if idx.name in _SQLITE_INCOMPATIBLE_INDEXES]
    for idx in _to_remove:
        _table.indexes.discard(idx)


@pytest.fixture(autouse=True)
async def _setup_database() -> AsyncIterator[None]:
    """Create all tables before the test and drop them afterwards.

    This gives each test a completely fresh schema.
    """
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _override_get_db() -> AsyncIterator[AsyncSession]:
    """Dependency override that yields a test SQLite session."""
    async with _TestSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest.fixture
async def async_client() -> AsyncIterator[AsyncClient]:
    """Provide an ``httpx.AsyncClient`` wired to the FastAPI app with the
    database dependency overridden to use the in-memory SQLite engine.
    """
    from dailyloadout.deps import get_db
    from dailyloadout.deps.capture import (
        get_igdb_client_dep,
        get_llm_client_dep,
        get_stt_client_dep,
    )
    from dailyloadout.infrastructure.llm.dummy import DummyLLMClient
    from dailyloadout.infrastructure.stt.dummy import DummySTTClient
    from dailyloadout.main import app

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_llm_client_dep] = lambda: DummyLLMClient()
    app.dependency_overrides[get_igdb_client_dep] = lambda: None
    app.dependency_overrides[get_stt_client_dep] = lambda: DummySTTClient()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# Also keep the old "client" fixture name so existing tests still work.
@pytest.fixture
async def client(async_client: AsyncClient) -> AsyncClient:
    return async_client


# ---------------------------------------------------------------------------
# Helper fixtures
# ---------------------------------------------------------------------------

_DEFAULT_USER = {
    "email": "test@example.com",
    "password": "strongpassword123",
    "display_name": "Test Player",
}


@pytest.fixture
async def register_user(async_client: AsyncClient) -> dict[str, Any]:
    """Register a user and return the parsed JSON response (TokenResponse)."""
    resp = await async_client.post("/v1/auth/register", json=_DEFAULT_USER)
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture
async def auth_headers(register_user: dict[str, Any]) -> dict[str, str]:
    """Return ``Authorization: Bearer <access_token>`` headers for the
    default test user.
    """
    return {"Authorization": f"Bearer {register_user['access_token']}"}


# ---------------------------------------------------------------------------
# Platform seed data for library tests
# ---------------------------------------------------------------------------

_SEED_PLATFORMS = [
    {"slug": "pc", "label": "PC", "family": "pc"},
    {"slug": "ps5", "label": "PlayStation 5", "family": "playstation"},
    {"slug": "ps4", "label": "PlayStation 4", "family": "playstation"},
    {"slug": "xbox-series-x", "label": "Xbox Series X|S", "family": "xbox"},
    {"slug": "xbox-one", "label": "Xbox One", "family": "xbox"},
    {"slug": "switch", "label": "Nintendo Switch", "family": "nintendo"},
    {"slug": "switch-2", "label": "Nintendo Switch 2", "family": "nintendo"},
    {"slug": "steam-deck", "label": "Steam Deck", "family": "pc"},
    {"slug": "ios", "label": "iOS", "family": "mobile"},
    {"slug": "android", "label": "Android", "family": "mobile"},
]


@pytest.fixture
async def seed_platforms() -> list[dict[str, Any]]:
    """Insert seed platforms into the test database and return them as dicts.

    Each dict contains ``id``, ``slug``, ``label``, and ``family`` after
    insertion.
    """
    async with _TestSessionFactory() as session:
        rows: list[dict[str, Any]] = []
        for p in _SEED_PLATFORMS:
            platform = Platform(**p)
            session.add(platform)
            await session.flush()
            rows.append(
                {
                    "id": platform.id,
                    "slug": platform.slug,
                    "label": platform.label,
                    "family": platform.family,
                }
            )
        await session.commit()
    return rows
