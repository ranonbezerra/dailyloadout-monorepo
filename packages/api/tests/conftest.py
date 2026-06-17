"""Shared test fixtures for DailyLoadout API tests.

Uses an in-memory SQLite database (via aiosqlite) so that tests never
depend on a running PostgreSQL instance.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import BigInteger, Integer, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# SQLite compatibility: render BigInteger as plain INTEGER so that SQLite
# autoincrement works correctly (SQLite only auto-increments INTEGER PKs).
# ---------------------------------------------------------------------------
from sqlalchemy.ext.compiler import compiles  # noqa: E402

from dailyloadout.infrastructure.db.base import Base
from dailyloadout.infrastructure.db.models import User  # noqa: F401  — ensure models registered


@compiles(BigInteger, "sqlite")
def _bi_to_int(element: BigInteger, compiler: Any, **kw: Any) -> str:  # noqa: ARG001
    return compiler.visit_INTEGER(Integer(), **kw)


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
    from dailyloadout.main import app

    app.dependency_overrides[get_db] = _override_get_db

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
