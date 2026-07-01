"""Backoffice cache flush endpoint + the invalidate_all_cache helper (Epic 18)."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient
from sqlalchemy import func, select

from slate.core.cache.invalidation import _ALL_NAMESPACES, invalidate_all_cache
from slate.infrastructure.cache.layer import cached_call, process_tier, reset_cache_stats
from slate.infrastructure.db.models import AdminAuditLog, User
from slate.infrastructure.db.repositories.admin import AdminRepository
from tests.conftest import _TestSessionFactory
from tests.test_cache_layer import FakeCache


async def _register(client: AsyncClient, email: str) -> dict[str, Any]:
    payload = {
        "email": email,
        "password": "SecurePass1",  # pragma: allowlist secret
        "display_name": "Cache Admin",
    }
    resp = await client.post("/v1/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _admin_headers(
    client: AsyncClient, email: str = "cacheadmin@example.com"
) -> dict[str, str]:
    tokens = await _register(client, email)
    async with _TestSessionFactory() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one()
        await AdminRepository(session).grant(user.id)
        await session.commit()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


# ── invalidate_all_cache helper ──────────────────────────────────────────


async def test_invalidate_all_cache_clears_namespaces_and_tier() -> None:
    cache = FakeCache()
    # One key under each cache namespace + a durable counter under another prefix.
    for ns in _ALL_NAMESPACES:
        cache.store[f"{ns}:sample"] = 1
    cache.store["ratelimit:user:1"] = 99  # NOT a cache namespace
    process_tier.set("ref:platforms", ["pc"], ttl_seconds=60)

    cleared = await invalidate_all_cache(cache=cache)

    assert set(cleared) == set(_ALL_NAMESPACES)
    assert all(f"{ns}:sample" not in cache.store for ns in _ALL_NAMESPACES)
    assert cache.store["ratelimit:user:1"] == 99  # durable counter untouched
    assert process_tier.get("ref:platforms") == (False, None)  # tier cleared


# ── POST /internal/v1/cache/flush ────────────────────────────────────────


class TestFlushEndpoint:
    async def test_admin_flush_clears_and_audits(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        resp = await async_client.post("/internal/v1/cache/flush", headers=headers)

        assert resp.status_code == 200, resp.text
        assert set(resp.json()["cleared_namespaces"]) == set(_ALL_NAMESPACES)

        async with _TestSessionFactory() as session:
            audited = (
                await session.execute(
                    select(func.count())
                    .select_from(AdminAuditLog)
                    .where(AdminAuditLog.action == "cache.flush")
                )
            ).scalar_one()
        assert audited == 1

    async def test_non_admin_forbidden(self, async_client: AsyncClient) -> None:
        tokens = await _register(async_client, "plainuser@example.com")
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        resp = await async_client.post("/internal/v1/cache/flush", headers=headers)
        assert resp.status_code == 403

    async def test_unauthenticated_rejected(self, async_client: AsyncClient) -> None:
        resp = await async_client.post("/internal/v1/cache/flush")
        assert resp.status_code == 401


# ── GET /internal/v1/cache/stats (admin observability) ───────────────────


class TestStatsEndpoint:
    async def test_admin_reads_counters(self, async_client: AsyncClient) -> None:
        reset_cache_stats()
        cache = FakeCache()

        async def compute() -> int:
            return 1

        # One miss then one hit under a known namespace.
        await cached_call(cache=cache, key="k", ttl_seconds=10, namespace="probe", compute=compute)
        await cached_call(cache=cache, key="k", ttl_seconds=10, namespace="probe", compute=compute)

        headers = await _admin_headers(async_client, "statsadmin@example.com")
        resp = await async_client.get("/internal/v1/cache/stats", headers=headers)

        assert resp.status_code == 200
        assert resp.json()["probe"] == {"hit": 1, "miss": 1, "hit_rate": 0.5}

    async def test_non_admin_forbidden(self, async_client: AsyncClient) -> None:
        tokens = await _register(async_client, "statsplain@example.com")
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        resp = await async_client.get("/internal/v1/cache/stats", headers=headers)
        assert resp.status_code == 403

    async def test_unauthenticated_rejected(self, async_client: AsyncClient) -> None:
        resp = await async_client.get("/internal/v1/cache/stats")
        assert resp.status_code == 401
