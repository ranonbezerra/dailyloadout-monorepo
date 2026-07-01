"""Tests for the SMTP mailer, the Turnstile CAPTCHA hook, and the fail-closed
auth rate limiter."""

from __future__ import annotations

from email.message import EmailMessage
from typing import Any

import pytest
from fastapi import HTTPException, Request

from slate.api.v1 import _rate_limit
from slate.config import settings
from slate.deps import captcha
from slate.deps.captcha import verify_turnstile
from slate.infrastructure.email.mailer import Mailer, send_verification_email


def _make_request(headers: dict[str, str] | None = None, body: bytes = b"") -> Request:
    raw_headers = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    scope = {
        "type": "http",
        "method": "POST",
        "headers": raw_headers,
        "client": ("1.2.3.4", 1234),
    }
    received = {"called": False}

    async def receive() -> dict[str, Any]:
        if received["called"]:
            return {"type": "http.request", "body": b"", "more_body": False}
        received["called"] = True
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(scope, receive)


# =====================================================================
# Mailer
# =====================================================================


class TestMailer:
    def test_unconfigured_skips(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "smtp_host", "")
        mailer = Mailer()
        assert mailer.configured is False
        assert mailer.send(to="a@b.com", subject="s", body="b") is False

    def test_send_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
        monkeypatch.setattr(settings, "smtp_user", "")
        sent: list[EmailMessage] = []
        mailer = Mailer()

        def _fake_deliver(message: EmailMessage) -> None:
            sent.append(message)

        monkeypatch.setattr(mailer, "_deliver", _fake_deliver)
        assert mailer.send(to="x@y.com", subject="Hi", body="Body") is True
        assert sent[0]["To"] == "x@y.com"
        assert sent[0]["Subject"] == "Hi"

    def test_send_swallows_errors(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
        mailer = Mailer()

        def _boom(message: EmailMessage) -> None:
            raise OSError("connection refused")

        monkeypatch.setattr(mailer, "_deliver", _boom)
        # Best-effort: a delivery error never propagates.
        assert mailer.send(to="x@y.com", subject="Hi", body="Body") is False

    def test_deliver_opens_smtp_and_logs_in(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
        monkeypatch.setattr(settings, "smtp_user", "user")
        monkeypatch.setattr(settings, "smtp_password", "pw")
        calls: dict[str, Any] = {"starttls": 0, "login": None, "sent": None}

        class _FakeSMTP:
            def __init__(self, host: str, port: int, timeout: int) -> None:
                calls["host"] = host

            def __enter__(self) -> _FakeSMTP:
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def starttls(self) -> None:
                calls["starttls"] += 1

            def login(self, user: str, password: str) -> None:
                calls["login"] = (user, password)

            def send_message(self, message: EmailMessage) -> None:
                calls["sent"] = message["To"]

        import slate.infrastructure.email.mailer as mailer_mod

        monkeypatch.setattr(mailer_mod.smtplib, "SMTP", _FakeSMTP)
        mailer = Mailer()
        assert mailer.send(to="d@e.com", subject="S", body="B") is True
        assert calls["starttls"] == 1
        assert calls["login"] == ("user", "pw")
        assert calls["sent"] == "d@e.com"

    def test_send_verification_email_composes_link(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
        monkeypatch.setattr(settings, "smtp_user", "")
        monkeypatch.setattr(settings, "email_verification_base_url", "https://app.test/verify")
        captured: list[str] = []
        mailer = Mailer()
        monkeypatch.setattr(mailer, "_deliver", lambda msg: captured.append(msg.get_content()))
        assert send_verification_email(mailer, to="z@y.com", token="TOK") is True
        assert "https://app.test/verify?token=TOK" in captured[0]


# =====================================================================
# Turnstile CAPTCHA hook
# =====================================================================


class TestTurnstile:
    async def test_noop_when_secret_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "turnstile_secret", "")
        # No token, but the dependency is a no-op without a configured secret.
        await verify_turnstile(_make_request())

    async def test_missing_token_403(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "turnstile_secret", "sk")
        with pytest.raises(HTTPException) as exc:
            await verify_turnstile(_make_request())
        assert exc.value.status_code == 403

    async def test_valid_token_passes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "turnstile_secret", "sk")

        async def _ok(token: str, remote_ip: str | None) -> bool:
            return True

        monkeypatch.setattr(captcha, "_siteverify", _ok)
        await verify_turnstile(_make_request(headers={"cf-turnstile-response": "tok"}))

    async def test_failed_token_403(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "turnstile_secret", "sk")

        async def _fail(token: str, remote_ip: str | None) -> bool:
            return False

        monkeypatch.setattr(captcha, "_siteverify", _fail)
        with pytest.raises(HTTPException) as exc:
            await verify_turnstile(_make_request(headers={"cf-turnstile-response": "tok"}))
        assert exc.value.status_code == 403

    async def test_token_from_body(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "turnstile_secret", "sk")
        seen: list[str] = []

        async def _ok(token: str, remote_ip: str | None) -> bool:
            seen.append(token)
            return True

        monkeypatch.setattr(captcha, "_siteverify", _ok)
        await verify_turnstile(
            _make_request(
                headers={"content-type": "application/json"},
                body=b'{"cf-turnstile-response": "body-tok"}',
            )
        )
        assert seen == ["body-tok"]

    async def test_siteverify_network_error_is_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "turnstile_secret", "sk")

        class _BoomClient:
            async def __aenter__(self) -> _BoomClient:
                return self

            async def __aexit__(self, *args: object) -> None:
                return None

            async def post(self, *args: object, **kwargs: object) -> None:
                raise OSError("network down")

        monkeypatch.setattr(captcha.httpx, "AsyncClient", lambda *a, **k: _BoomClient())
        assert await captcha._siteverify("tok", "1.2.3.4") is False

    async def test_siteverify_success_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "turnstile_secret", "sk")

        class _Resp:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, bool]:
                return {"success": True}

        class _Client:
            async def __aenter__(self) -> _Client:
                return self

            async def __aexit__(self, *args: object) -> None:
                return None

            async def post(self, *args: object, **kwargs: object) -> _Resp:
                return _Resp()

        monkeypatch.setattr(captcha.httpx, "AsyncClient", lambda *a, **k: _Client())
        assert await captcha._siteverify("tok", None) is True

    @staticmethod
    def _patch_siteverify_payload(
        monkeypatch: pytest.MonkeyPatch, payload: dict[str, object]
    ) -> None:
        monkeypatch.setattr(settings, "turnstile_secret", "sk")

        class _Resp:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, object]:
                return payload

        class _Client:
            async def __aenter__(self) -> _Client:
                return self

            async def __aexit__(self, *args: object) -> None:
                return None

            async def post(self, *args: object, **kwargs: object) -> _Resp:
                return _Resp()

        monkeypatch.setattr(captcha.httpx, "AsyncClient", lambda *a, **k: _Client())

    async def test_siteverify_failure_with_error_codes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._patch_siteverify_payload(
            monkeypatch, {"success": False, "error-codes": ["timeout-or-duplicate"]}
        )
        assert await captcha._siteverify("tok", None) is False

    async def test_siteverify_rejects_wrong_hostname(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "turnstile_allowed_hostnames", ["slate.app"])
        self._patch_siteverify_payload(monkeypatch, {"success": True, "hostname": "evil.example"})
        assert await captcha._siteverify("tok", None) is False

    async def test_siteverify_rejects_wrong_action(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "turnstile_expected_action", "register")
        self._patch_siteverify_payload(monkeypatch, {"success": True, "action": "login"})
        assert await captcha._siteverify("tok", None) is False

    async def test_siteverify_accepts_matching_hostname_and_action(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "turnstile_allowed_hostnames", ["slate.app"])
        monkeypatch.setattr(settings, "turnstile_expected_action", "register")
        self._patch_siteverify_payload(
            monkeypatch, {"success": True, "hostname": "slate.app", "action": "register"}
        )
        assert await captcha._siteverify("tok", None) is True


# =====================================================================
# Fail-closed auth rate limiter
# =====================================================================


class _BrokenLimiter:
    async def try_acquire(self, *args: object, **kwargs: object) -> bool:
        raise ConnectionError("redis down")


class _User:
    def __init__(self, user_id: int) -> None:
        self.id = user_id


class TestFailClosedLimiter:
    @pytest.fixture(autouse=True)
    def _enable(self) -> Any:
        original = settings.rate_limit_enabled
        settings.rate_limit_enabled = True
        yield
        settings.rate_limit_enabled = original
        _rate_limit._limiters.clear()

    async def test_fail_closed_denies_on_redis_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def _broken(*args: object, **kwargs: object) -> _BrokenLimiter:
            return _BrokenLimiter()

        monkeypatch.setattr(_rate_limit, "_get_limiter", _broken)
        dep = _rate_limit.rate_limit("failclosed", times=1, seconds=60, by="ip", fail_closed=True)
        request = Request({"type": "http", "client": ("9.9.9.9", 1), "headers": []})
        with pytest.raises(HTTPException) as exc:
            await dep(request=request)  # type: ignore[call-arg]
        assert exc.value.status_code == 503

    async def test_fail_open_allows_on_redis_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def _broken(*args: object, **kwargs: object) -> _BrokenLimiter:
            return _BrokenLimiter()

        monkeypatch.setattr(_rate_limit, "_get_limiter", _broken)
        dep = _rate_limit.rate_limit("failopen", times=1, seconds=60, by="user")
        # fail_closed defaults False => request is allowed despite the error.
        for _ in range(3):
            await dep(current_user=_User(1))  # type: ignore[call-arg]

    async def test_fail_closed_noop_when_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        settings.rate_limit_enabled = False
        called = {"hit": False}

        async def _broken(*args: object, **kwargs: object) -> _BrokenLimiter:
            called["hit"] = True
            return _BrokenLimiter()

        monkeypatch.setattr(_rate_limit, "_get_limiter", _broken)
        dep = _rate_limit.rate_limit("failclosed", times=1, seconds=60, by="ip", fail_closed=True)
        request = Request({"type": "http", "client": ("9.9.9.9", 1), "headers": []})
        # Disabled => no-op regardless of fail_closed, limiter never built.
        await dep(request=request)  # type: ignore[call-arg]
        assert called["hit"] is False
