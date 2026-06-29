"""Backoffice (Epic 21) Phase 3: dynamic operational config overlay + API.

Covers the overlay precedence (override > env/baseline), its short cache +
write-through invalidation, registry validation, the ``/internal/v1/config``
surface (list/set/clear, validated + audited), and — the DoD proof — that
flipping a knob via the API takes effect in a real consumer with no redeploy.
"""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from slate.config import settings
from slate.infrastructure.config.dynamic import dynamic_config
from slate.infrastructure.db.models import AdminAuditLog, AppConfig, User
from slate.infrastructure.db.repositories.admin import AdminRepository
from tests.conftest import _TestSessionFactory


async def _register(client: AsyncClient, email: str) -> dict[str, Any]:
    payload = {
        "email": email,
        "password": "SecurePass1",  # pragma: allowlist secret
        "display_name": "Cfg User",
    }
    resp = await client.post("/v1/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _admin_headers(
    client: AsyncClient, email: str = "cfgadmin@example.com"
) -> dict[str, str]:
    tokens = await _register(client, email)
    async with _TestSessionFactory() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one()
        await AdminRepository(session).grant(user.id)
        await session.commit()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _set_override_row(key: str, value: object) -> None:
    """Insert an override directly and invalidate the overlay cache for it."""
    async with _TestSessionFactory() as session:
        session.add(AppConfig(key=key, value=value, updated_by=None))
        await session.commit()
    dynamic_config.invalidate(key)


# =====================================================================
# Overlay precedence + cache
# =====================================================================


class TestOverlay:
    async def test_baseline_when_no_override(self) -> None:
        dynamic_config.clear()
        assert await dynamic_config.get_int("cost_user_per_day") == settings.cost_user_per_day
        assert await dynamic_config.get_bool("rate_limit_enabled") == settings.rate_limit_enabled

    async def test_override_wins_over_baseline(self) -> None:
        await _set_override_row("cost_user_per_day", 42)
        assert await dynamic_config.get_int("cost_user_per_day") == 42

    async def test_cache_holds_until_invalidated(self) -> None:
        await _set_override_row("cost_global_per_day", 100)
        assert await dynamic_config.get_int("cost_global_per_day") == 100

        # Mutate the row WITHOUT invalidating: the cached value still wins.
        async with _TestSessionFactory() as session:
            row = (
                await session.execute(
                    select(AppConfig).where(AppConfig.key == "cost_global_per_day")
                )
            ).scalar_one()
            row.value = 999
            await session.commit()
        assert await dynamic_config.get_int("cost_global_per_day") == 100

        # Invalidation forces a fresh read.
        dynamic_config.invalidate("cost_global_per_day")
        assert await dynamic_config.get_int("cost_global_per_day") == 999

    async def test_type_and_key_guards(self) -> None:
        with pytest.raises(TypeError):
            await dynamic_config.get_int("rate_limit_enabled")  # bool key
        with pytest.raises(TypeError):
            await dynamic_config.get_bool("cost_user_per_day")  # int key
        with pytest.raises(KeyError):
            await dynamic_config.get_bool("not_a_real_key")


# =====================================================================
# Authorization
# =====================================================================

_ROUTES = [
    ("get", "/internal/v1/config"),
    ("put", "/internal/v1/config/cost_user_per_day"),
    ("delete", "/internal/v1/config/cost_user_per_day"),
]


class TestConfigAuthz:
    @pytest.mark.parametrize(("method", "path"), _ROUTES)
    async def test_unauthenticated_is_401(
        self, async_client: AsyncClient, method: str, path: str
    ) -> None:
        assert (await async_client.request(method, path)).status_code == 401

    @pytest.mark.parametrize(("method", "path"), _ROUTES)
    async def test_non_admin_is_403(
        self, async_client: AsyncClient, method: str, path: str
    ) -> None:
        tokens = await _register(async_client, "plain@example.com")
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        resp = await async_client.request(method, path, headers=headers, json={"value": 1})
        assert resp.status_code == 403


# =====================================================================
# Config API: list / set / clear
# =====================================================================


class TestConfigApi:
    async def test_list_returns_every_curated_key_at_baseline(
        self, async_client: AsyncClient
    ) -> None:
        headers = await _admin_headers(async_client)
        resp = await async_client.get("/internal/v1/config", headers=headers)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 9
        entry = {i["key"]: i for i in items}["cost_user_per_day"]
        assert entry["is_overridden"] is False
        assert entry["override_value"] is None
        assert entry["baseline_value"] == settings.cost_user_per_day
        assert entry["effective_value"] == settings.cost_user_per_day

    async def test_set_override_persists_audits_and_marks_overridden(
        self, async_client: AsyncClient
    ) -> None:
        headers = await _admin_headers(async_client)
        resp = await async_client.put(
            "/internal/v1/config/cost_user_per_day", headers=headers, json={"value": 7}
        )
        assert resp.status_code == 200
        entry = {i["key"]: i for i in resp.json()["items"]}["cost_user_per_day"]
        assert entry["is_overridden"] is True
        assert entry["override_value"] == 7
        assert entry["effective_value"] == 7
        assert entry["updated_by"] is not None  # the acting admin's public_id

        async with _TestSessionFactory() as session:
            row = (
                (await session.execute(select(AdminAuditLog).order_by(AdminAuditLog.id.desc())))
                .scalars()
                .first()
            )
            assert row is not None and row.action == "config.set"
            assert "cost_user_per_day" in (row.detail or "")

    async def test_set_rejects_bad_type_and_out_of_range(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        # bool for an int key → 422 (StrictBool|StrictInt + registry both reject)
        bad_type = await async_client.put(
            "/internal/v1/config/cost_user_per_day", headers=headers, json={"value": True}
        )
        assert bad_type.status_code == 422
        # out of range (max is 1_000_000)
        too_big = await async_client.put(
            "/internal/v1/config/cost_user_per_day", headers=headers, json={"value": 9_999_999}
        )
        assert too_big.status_code == 422

    async def test_set_unknown_key_is_404(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        resp = await async_client.put(
            "/internal/v1/config/made_up_key", headers=headers, json={"value": 1}
        )
        assert resp.status_code == 404

    async def test_clear_reverts_to_baseline_and_audits(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        await async_client.put(
            "/internal/v1/config/catalog_share_threshold", headers=headers, json={"value": 99}
        )
        resp = await async_client.delete(
            "/internal/v1/config/catalog_share_threshold", headers=headers
        )
        assert resp.status_code == 200
        entry = {i["key"]: i for i in resp.json()["items"]}["catalog_share_threshold"]
        assert entry["is_overridden"] is False
        assert entry["effective_value"] == settings.catalog_share_threshold

        async with _TestSessionFactory() as session:
            count = (
                await session.execute(
                    select(func.count())
                    .select_from(AdminAuditLog)
                    .where(AdminAuditLog.action == "config.clear")
                )
            ).scalar_one()
            assert count == 1

    async def test_clear_unknown_key_is_404(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        resp = await async_client.delete("/internal/v1/config/made_up_key", headers=headers)
        assert resp.status_code == 404


# =====================================================================
# Live effect (the DoD proof): flip a knob → a real consumer changes
# =====================================================================


class TestLiveEffect:
    async def test_disposable_email_block_can_be_flipped_live(
        self, async_client: AsyncClient
    ) -> None:
        # Baseline blocks disposable domains: registration is rejected (422).
        blocked = await async_client.post(
            "/v1/auth/register",
            json={
                "email": "throwaway@mailinator.com",
                "password": "SecurePass1",  # pragma: allowlist secret
                "display_name": "Throwaway",
            },
        )
        assert blocked.status_code == 422

        # An admin flips the knob off via the backoffice — no redeploy.
        headers = await _admin_headers(async_client)
        flip = await async_client.put(
            "/internal/v1/config/block_disposable_emails", headers=headers, json={"value": False}
        )
        assert flip.status_code == 200

        # The very next registration with the same disposable domain now succeeds.
        allowed = await async_client.post(
            "/v1/auth/register",
            json={
                "email": "throwaway@mailinator.com",
                "password": "SecurePass1",  # pragma: allowlist secret
                "display_name": "Throwaway",
            },
        )
        assert allowed.status_code == 201
