"""Login step-up: per-account failure counter + conditional CAPTCHA gate."""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

from slate.config import settings
from slate.core.auth import login_stepup
from tests.conftest import _FakeStepupRedis

_EMAIL = "test@example.com"
_PASSWORD = "StrongPass123"  # pragma: allowlist secret


class TestStepupCounter:
    async def test_requires_captcha_after_threshold(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake = _FakeStepupRedis()
        monkeypatch.setattr(login_stepup, "get_redis_client", lambda: fake)
        email = "victim@example.com"

        assert await login_stepup.login_stepup_required(email) is False
        for _ in range(settings.login_stepup_after_failures):
            await login_stepup.record_login_failure(email)
        assert await login_stepup.login_stepup_required(email) is True

        # A successful login clears the counter.
        await login_stepup.reset_login_failures(email)
        assert await login_stepup.login_stepup_required(email) is False

    async def test_best_effort_fails_open_on_redis_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class _Boom:
            async def get(self, _k: str) -> str | None:
                raise RuntimeError("redis down")

            async def incr(self, _k: str) -> int:
                raise RuntimeError("redis down")

            async def delete(self, _k: str) -> None:
                raise RuntimeError("redis down")

        monkeypatch.setattr(login_stepup, "get_redis_client", lambda: _Boom())
        # Never raises; a Redis outage degrades to "no step-up", never a locked account.
        assert await login_stepup.login_stepup_required("x@example.com") is False
        await login_stepup.record_login_failure("x@example.com")
        await login_stepup.reset_login_failures("x@example.com")


class TestStepupGate:
    async def test_login_consults_stepup_and_proceeds(
        self,
        async_client: AsyncClient,
        register_user: dict[str, Any],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Force the step-up branch; Turnstile is a no-op in tests (no secret), so a
        # valid login still succeeds — this exercises the captcha gate on the path.
        async def _required(_email: str) -> bool:
            return True

        monkeypatch.setattr(login_stepup, "login_stepup_required", _required)
        resp = await async_client.post(
            "/v1/auth/login", json={"email": _EMAIL, "password": _PASSWORD}
        )
        assert resp.status_code == 200
