"""App-level hardening: body-size cap, security headers, docs gating."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from slate.api.middleware import MaxBodySizeMiddleware, SecurityHeadersMiddleware
from slate.api.request_logging import RequestLoggingMiddleware


class _LogSpy:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, object]]] = []

    def info(self, event: str, **fields: object) -> None:
        self.events.append((event, fields))

    def exception(self, event: str, **fields: object) -> None:
        self.events.append((event, fields))


async def test_security_headers_present(async_client: AsyncClient) -> None:
    resp = await async_client.get("/health")
    assert resp.status_code == 200
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["referrer-policy"] == "no-referrer"
    assert "max-age=" in resp.headers["strict-transport-security"]
    assert "includeSubDomains" in resp.headers["strict-transport-security"]


async def test_cors_allows_x_auth_mode(async_client: AsyncClient) -> None:
    resp = await async_client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-Auth-Mode",
        },
    )
    allowed = resp.headers.get("access-control-allow-headers", "").lower()
    assert "x-auth-mode" in allowed


async def test_body_size_cap_returns_413() -> None:
    """A Content-Length over the cap is rejected with 413 before handling."""

    async def _app(scope: dict, receive: object, send: object) -> None:  # pragma: no cover
        raise AssertionError("handler should not run for oversized body")

    wrapped = MaxBodySizeMiddleware(_app, max_body_bytes=10)
    transport = ASGITransport(app=wrapped)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/anything", content=b"x" * 50)
    assert resp.status_code == 413
    assert "too large" in resp.json()["detail"].lower()


async def test_body_size_cap_allows_small_body() -> None:
    async def _app(scope: dict, receive: object, send: object) -> None:
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    wrapped = MaxBodySizeMiddleware(_app, max_body_bytes=1000)
    transport = ASGITransport(app=wrapped)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/anything", content=b"x" * 10)
    assert resp.status_code == 204


async def test_security_headers_passthrough_for_non_http_scope() -> None:
    """A non-http scope (e.g. lifespan) is forwarded untouched."""
    calls: list[str] = []

    async def _app(scope: dict, receive: object, send: object) -> None:
        calls.append(scope["type"])

    mw = SecurityHeadersMiddleware(_app, hsts_max_age=10)
    await mw({"type": "lifespan"}, None, None)  # type: ignore[arg-type]
    assert calls == ["lifespan"]

    body_mw = MaxBodySizeMiddleware(_app, max_body_bytes=10)
    await body_mw({"type": "lifespan"}, None, None)  # type: ignore[arg-type]
    assert calls == ["lifespan", "lifespan"]


async def test_request_logging_adds_request_id_and_logs_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spy = _LogSpy()
    monkeypatch.setattr("slate.api.request_logging.logger", spy)

    async def _app(scope: dict, receive: object, send: object) -> None:
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    wrapped = RequestLoggingMiddleware(_app, skip_successful_health=False)
    transport = ASGITransport(app=wrapped)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/anything?token=SECRET", headers={"X-Request-ID": "rid-123"})

    assert resp.status_code == 204
    assert resp.headers["x-request-id"] == "rid-123"
    assert len(spy.events) == 1
    event, fields = spy.events[0]
    assert event == "http_request_completed"
    assert fields["request_id"] == "rid-123"
    assert fields["method"] == "GET"
    assert fields["path"] == "/anything"
    assert fields["status_code"] == 204
    assert "SECRET" not in str(fields)


async def test_request_logging_skips_successful_health(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spy = _LogSpy()
    monkeypatch.setattr("slate.api.request_logging.logger", spy)

    async def _app(scope: dict, receive: object, send: object) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    transport = ASGITransport(app=RequestLoggingMiddleware(_app))
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/health")

    assert resp.status_code == 200
    assert resp.headers["x-request-id"]
    assert spy.events == []


async def test_request_logging_logs_failures_once(monkeypatch: pytest.MonkeyPatch) -> None:
    spy = _LogSpy()
    monkeypatch.setattr("slate.api.request_logging.logger", spy)

    async def _app(scope: dict, receive: object, send: object) -> None:
        raise RuntimeError("boom")

    transport = ASGITransport(app=RequestLoggingMiddleware(_app))
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        with pytest.raises(RuntimeError, match="boom"):
            await ac.get("/broken")

    assert len(spy.events) == 1
    event, fields = spy.events[0]
    assert event == "http_request_failed"
    assert fields["path"] == "/broken"
    assert fields["status_code"] == 500


def test_docs_gated_off_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """Outside dev/test the app exposes no /docs and no /openapi.json."""
    import slate.main as main_mod

    monkeypatch.setattr(main_mod.settings, "app_env", "production")
    app = main_mod.create_app()

    assert app.openapi_url is None
    routes = {getattr(r, "path", None) for r in app.routes}
    assert "/docs" not in routes


def test_docs_on_in_dev() -> None:
    import slate.main as main_mod

    app = main_mod.create_app()
    routes = {getattr(r, "path", None) for r in app.routes}
    assert "/docs" in routes
    assert app.openapi_url == "/openapi.json"
