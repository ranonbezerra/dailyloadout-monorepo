"""Shared test fixtures for Slate API tests.

Uses an in-memory SQLite database (via aiosqlite) so that tests never
depend on a running PostgreSQL instance.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import BigInteger, Integer, SmallInteger, Text, event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# SQLite compatibility: render BigInteger as plain INTEGER so that SQLite
# autoincrement works correctly (SQLite only auto-increments INTEGER PKs).
# ---------------------------------------------------------------------------
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.types import TypeDecorator

from slate.infrastructure.db.base import Base
from slate.infrastructure.db.models import (  # noqa: F401  — ensure models registered
    AppConfig,
    Capture,
    CaptureCandidate,
    Game,
    LibraryEntry,
    Pick,
    Platform,
    PlaySession,
    User,
)


@compiles(BigInteger, "sqlite")
def _bi_to_int(element: BigInteger, compiler: Any, **kw: Any) -> str:
    return compiler.visit_INTEGER(Integer(), **kw)


@compiles(SmallInteger, "sqlite")
def _si_to_int(element: SmallInteger, compiler: Any, **kw: Any) -> str:
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

    def process_bind_param(self, value: list[str] | None, dialect: Any) -> str | None:
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(self, value: str | None, dialect: Any) -> list[str] | None:
        if value is None:
            return None
        return json.loads(value)


# Swap ARRAY(String) column types at import time, before create_all() runs.
Game.__table__.c.genres.type = _JSONEncodedList()
CaptureCandidate.__table__.c.igdb_genres.type = _JSONEncodedList()

# Swap JSONB → JSON-encoded TEXT for SQLite (round-trips scalars too: bool/int).
PlaySession.__table__.c.extracted_state.type = _JSONEncodedList()
AppConfig.__table__.c.value.type = _JSONEncodedList()


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


@pytest.fixture(autouse=True)
def _reset_dynamic_config() -> Iterator[None]:
    """Point the dynamic-config overlay at the test DB and reset its cache.

    The overlay self-sources a session (it has no request scope). On the shared
    in-memory SQLite connection, opening that nested session *mid-transaction*
    would reset the caller's transaction — harmless in production (separate
    Postgres connections) but a hazard here. So we pre-warm the cache as
    "no override" for every key: consumers fall back to the settings baseline
    without ever touching the DB. Tests that exercise real overrides
    ``invalidate``/``clear`` the relevant key to force a fresh read in a clean
    context. Clearing before and after stops cross-test leakage.
    """
    import time

    from slate.infrastructure.config.dynamic import _MISSING, dynamic_config
    from slate.infrastructure.config.registry import CONFIG_REGISTRY

    dynamic_config._session_factory = _TestSessionFactory
    dynamic_config.clear()
    far_future = time.monotonic() + 3600
    for key in CONFIG_REGISTRY:
        dynamic_config._cache[key] = (_MISSING, far_future)
    yield
    dynamic_config.clear()


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
    "idx_play_sessions_user_active",  # partial unique (WHERE ended_at IS NULL)
    "idx_play_sessions_entry_ended",  # DESC expression
    "idx_picks_user_created",  # DESC expression
    "idx_users_email_active",  # partial (WHERE deleted_at IS NULL)
    "idx_refresh_user_active",  # partial (WHERE revoked_at IS NULL)
}

for _table in Base.metadata.tables.values():
    _to_remove = [idx for idx in _table.indexes if idx.name in _SQLITE_INCOMPATIBLE_INDEXES]
    for idx in _to_remove:
        _table.indexes.discard(idx)


_schema_created = False


@pytest.fixture(autouse=True)
def _no_background_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    """No-op the wrap_up-extraction Taskiq dispatch in tests.

    The task is exercised directly via its ``.original_func``; an API wrap_up
    submission only needs ``.kiq()`` to be a no-op. A real fire-and-forget
    ``InMemoryBroker`` task outlives the test's event loop and its aiosqlite
    connection then calls back into a closed loop — a teardown
    ResourceWarning/thread-exception that ``filterwarnings=["error"]`` escalates
    to a failure (flaky under xdist). Every test that submits a wrap_up already
    asserts the state is NOT yet extracted, so a no-op matches that behaviour.
    """
    from slate.infrastructure.tasks import wrap_up_extraction

    async def _noop_kiq(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(wrap_up_extraction.extract_wrap_up_state_task, "kiq", _noop_kiq)


@pytest.fixture(autouse=True)
async def _setup_database() -> AsyncIterator[None]:
    """Ensure schema exists and clean all data before each test.

    The schema is created lazily on the first test and reused for the
    rest of the session.  Data is wiped via DELETE (much faster than
    ``create_all`` / ``drop_all`` on every test).
    """
    global _schema_created

    if not _schema_created:
        async with _test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        _schema_created = True

    # Wipe data: disable FKs, delete all rows, re-enable FKs.
    async with _test_engine.begin() as conn:
        await conn.execute(text("PRAGMA foreign_keys=OFF"))
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
        await conn.execute(text("PRAGMA foreign_keys=ON"))

    yield


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
    from slate.api.v1.auth import _check_login_rate, _check_register_rate
    from slate.api.v1.auth_mfa import _check_mfa_login_rate, _check_mfa_verify_rate
    from slate.api.v1.auth_password import (
        _check_change_rate,
        _check_forgot_rate,
        _check_reset_rate,
    )
    from slate.config import settings
    from slate.deps import get_db
    from slate.deps.capture import (
        get_igdb_client_dep,
        get_llm_client_dep,
        get_stt_client_dep,
    )
    from slate.infrastructure.llm.dummy import DummyLLMClient
    from slate.infrastructure.stt.dummy import DummySTTClient
    from slate.main import app

    # Tests run over plain http://; a Secure cookie would never be sent back by
    # httpx, so relax it for the cookie-mode auth tests (prod stays Secure).
    settings.auth_cookie_secure = False

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_llm_client_dep] = lambda: DummyLLMClient()
    app.dependency_overrides[get_igdb_client_dep] = lambda: None
    app.dependency_overrides[get_stt_client_dep] = lambda: DummySTTClient()

    # Disable rate limiting in tests to avoid false 429 responses.
    async def _noop() -> None:
        pass

    app.dependency_overrides[_check_login_rate] = _noop
    app.dependency_overrides[_check_register_rate] = _noop
    app.dependency_overrides[_check_forgot_rate] = _noop
    app.dependency_overrides[_check_reset_rate] = _noop
    app.dependency_overrides[_check_change_rate] = _noop
    app.dependency_overrides[_check_mfa_login_rate] = _noop
    app.dependency_overrides[_check_mfa_verify_rate] = _noop

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
    "password": "StrongPass123",
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


# ---------------------------------------------------------------------------
# Cleanup: dispose engines at session end to avoid ResourceWarning
# ---------------------------------------------------------------------------


def pytest_sessionfinish(session: Any, exitstatus: int) -> None:
    """Dispose async engines so connections are closed before process exit."""
    import asyncio

    async def _dispose() -> None:
        await _test_engine.dispose()
        from slate.infrastructure.db.session import engine as real_engine

        await real_engine.dispose()

    loop = asyncio.new_event_loop()
    loop.run_until_complete(_dispose())
    loop.close()
