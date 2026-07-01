"""Per-account rate-limit helpers: body-identity extraction + disabled no-op."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import Request

from slate.api.v1 import _rate_limit
from slate.api.v1._rate_limit import account_email_identity, account_rate_limit


def _json_request(body: bytes, content_type: str = "application/json") -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "headers": [(b"content-type", content_type.encode())],
        "client": ("1.2.3.4", 1234),
    }
    state = {"sent": False}

    async def receive() -> dict[str, Any]:
        if state["sent"]:
            return {"type": "http.request", "body": b"", "more_body": False}
        state["sent"] = True
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(scope, receive)


class TestAccountEmailIdentity:
    async def test_extracts_and_normalizes_email(self) -> None:
        req = _json_request(b'{"email": "  Player@Example.COM  ", "password": "x"}')
        assert await account_email_identity(req) == "email:player@example.com"

    async def test_missing_email_returns_none(self) -> None:
        assert await account_email_identity(_json_request(b'{"password": "x"}')) is None

    async def test_non_json_body_returns_none(self) -> None:
        assert await account_email_identity(_json_request(b"not json")) is None


class TestAccountRateLimitDisabled:
    async def test_noop_when_rate_limiting_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # With the limiter disabled (the pytest default), the dependency must not
        # touch Redis / the extractor — it returns immediately.
        called = {"extract": False}

        async def _extract(_req: Request) -> str | None:
            called["extract"] = True
            return "email:x@y.com"

        async def _disabled(_key: str) -> bool:
            return False

        monkeypatch.setattr(_rate_limit.dynamic_config, "get_bool", _disabled)
        dep = account_rate_limit("acct_test", 5, 60, _extract)
        await dep(_json_request(b'{"email": "x@y.com"}'))  # no raise, no enforce
        assert called["extract"] is False
