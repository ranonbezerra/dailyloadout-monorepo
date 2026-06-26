"""ASGI middleware: request-body size cap + security response headers.

Kept out of ``main.py`` so the app factory stays lean (and under the 300-line
cap). Both are pure-ASGI so they run before/around the route handlers without
buffering the body.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import structlog
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = structlog.get_logger()

# Response sent when Content-Length exceeds the cap, before any body is read.
_TOO_LARGE_BODY = b'{"detail":"Request body too large."}'


class MaxBodySizeMiddleware:
    """Reject requests whose ``Content-Length`` exceeds *max_body_bytes* with 413.

    This is a coarse backstop checked from the request headers BEFORE the body is
    read, in addition to the per-endpoint upload caps. Requests without a
    ``Content-Length`` header pass through untouched (per-endpoint checks still
    apply).
    """

    def __init__(self, app: ASGIApp, max_body_bytes: int) -> None:
        self._app = app
        self._max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        content_length = _content_length(scope)
        if content_length is not None and content_length > self._max_body_bytes:
            await _send_413(send)
            return

        await self._app(scope, receive, send)


def _content_length(scope: Scope) -> int | None:
    for name, value in scope.get("headers", []):
        if name == b"content-length":
            try:
                return int(value)
            except ValueError:
                return None
    return None


async def _send_413(send: Send) -> None:
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(_TOO_LARGE_BODY)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": _TOO_LARGE_BODY})


_RL_TOO_MANY_BODY = b'{"detail":"Rate limit exceeded. Please slow down."}'


class DefaultUserRateLimitMiddleware:
    """Generous per-user rate-limit backstop applied to EVERY authenticated request.

    A safety net so a NEW authenticated route is metered by default even if its
    author forgets to attach an explicit ``rate_limit`` dependency. It identifies
    the caller by the ``sub`` (user public_id) of a best-effort-decoded bearer
    JWT — no DB hit. Anonymous/unauthenticated requests (no valid bearer token)
    pass straight through; the per-route auth dependency rejects them.

    Generous by design (it's a backstop, not the primary control) and:

    - a **no-op when rate limiting is disabled** in settings (tests + "limiter
      off" deploys), mirroring the ``rate_limit`` dependency, and
    - **fail-open** on any limiter/Redis error — the backstop never hard-fails a
      request.
    """

    def __init__(self, app: ASGIApp, *, per_minute: int) -> None:
        self._app = app
        self._per_minute = per_minute

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        # Local imports keep this module import-light and avoid an import cycle
        # with the settings/limiter/auth modules at app-construction time.
        from fastapi import HTTPException

        from dailyloadout.api.v1._rate_limit import _enforce
        from dailyloadout.config import settings

        if settings.rate_limit_enabled:
            identity = _bearer_subject(scope)
            if identity is not None:
                try:
                    # fail_closed=False: a Redis error returns (allows) inside
                    # _enforce, so the backstop fails open.
                    await _enforce("default_user", identity, self._per_minute, 60)
                except HTTPException as exc:
                    if exc.status_code == 429:
                        await _send_429(send)
                        return
                except Exception:
                    logger.warning("default_rate_limit_error", exc_info=True)

        await self._app(scope, receive, send)


def _bearer_subject(scope: Scope) -> str | None:
    """Return the ``sub`` of a best-effort-decoded bearer JWT, else ``None``."""
    token: str | None = None
    for name, value in scope.get("headers", []):
        if name == b"authorization":
            raw = value.decode("latin-1")
            if raw.lower().startswith("bearer "):
                token = raw[7:].strip()
            break
    if not token:
        return None
    try:
        from dailyloadout.core.auth.security import decode_access_token

        payload = decode_access_token(token)
    except Exception:
        return None
    subject = payload.get("sub")
    return str(subject) if subject is not None else None


async def _send_429(send: Send) -> None:
    await send(
        {
            "type": "http.response.start",
            "status": 429,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(_RL_TOO_MANY_BODY)).encode()),
                (b"retry-after", b"60"),
            ],
        }
    )
    await send({"type": "http.response.body", "body": _RL_TOO_MANY_BODY})


class SecurityHeadersMiddleware:
    """Attach baseline security headers to every HTTP response.

    Sets HSTS, ``X-Content-Type-Options``, ``X-Frame-Options`` and
    ``Referrer-Policy``. HSTS is advertised regardless of scheme — browsers only
    honor it over HTTPS, and behind a TLS-terminating proxy the app sees http.
    """

    def __init__(self, app: ASGIApp, hsts_max_age: int) -> None:
        self._app = app
        self._extra_headers: list[tuple[bytes, bytes]] = [
            (
                b"strict-transport-security",
                f"max-age={hsts_max_age}; includeSubDomains".encode(),
            ),
            (b"x-content-type-options", b"nosniff"),
            (b"x-frame-options", b"DENY"),
            (b"referrer-policy", b"no-referrer"),
        ]

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        send_with_headers = self._wrap_send(send)
        await self._app(scope, receive, send_with_headers)

    def _wrap_send(self, send: Send) -> Callable[[Message], Awaitable[None]]:
        async def wrapped(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                present = {name for name, _ in headers}
                for name, value in self._extra_headers:
                    if name not in present:
                        headers.append((name, value))
                message = {**message, "headers": headers}
            await send(message)

        return wrapped
