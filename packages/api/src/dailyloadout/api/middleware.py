"""ASGI middleware: request-body size cap + security response headers.

Kept out of ``main.py`` so the app factory stays lean (and under the 300-line
cap). Both are pure-ASGI so they run before/around the route handlers without
buffering the body.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.types import ASGIApp, Message, Receive, Scope, Send

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
