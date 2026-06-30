"""Request-scoped structured logging middleware."""

from __future__ import annotations

import time
from typing import cast
from uuid import uuid4

import structlog
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from slate.api.middleware import _bearer_subject

logger = structlog.get_logger()

_REQUEST_ID_HEADER = b"x-request-id"
_MAX_REQUEST_ID_CHARS = 128


class RequestLoggingMiddleware:
    """Bind request context and emit one operational log per HTTP request."""

    def __init__(self, app: ASGIApp, *, skip_successful_health: bool = True) -> None:
        self._app = app
        self._skip_successful_health = skip_successful_health

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        request_id = _request_id(scope) or uuid4().hex
        path = str(scope.get("path") or "")
        method = str(scope.get("method") or "")
        client_ip = _client_ip(scope)
        user_public_id = _bearer_subject(scope)
        status_code = 500
        started = time.perf_counter()
        failed = False

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=method,
            path=path,
            client_ip=client_ip,
            user_public_id=user_public_id,
        )

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                headers = list(message.get("headers", []))
                if not any(name.lower() == _REQUEST_ID_HEADER for name, _ in headers):
                    headers.append((_REQUEST_ID_HEADER, request_id.encode("ascii", "ignore")))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self._app(scope, receive, send_with_request_id)
        except Exception:
            failed = True
            duration_ms = _duration_ms(started)
            logger.exception(
                "http_request_failed",
                request_id=request_id,
                method=method,
                path=path,
                client_ip=client_ip,
                user_public_id=user_public_id,
                status_code=status_code,
                duration_ms=duration_ms,
            )
            raise
        finally:
            duration_ms = _duration_ms(started)
            if not failed and not _skip_health(path, status_code, self._skip_successful_health):
                logger.info(
                    "http_request_completed",
                    request_id=request_id,
                    method=method,
                    path=path,
                    client_ip=client_ip,
                    user_public_id=user_public_id,
                    status_code=status_code,
                    duration_ms=duration_ms,
                )
            structlog.contextvars.clear_contextvars()


def _request_id(scope: Scope) -> str | None:
    for name, value in scope.get("headers", []):
        header_name = cast(bytes, name)
        if header_name.lower() == _REQUEST_ID_HEADER:
            cleaned = cast(bytes, value).decode("latin-1", errors="ignore").strip()
            if cleaned:
                return cleaned[:_MAX_REQUEST_ID_CHARS]
    return None


def _client_ip(scope: Scope) -> str | None:
    client = scope.get("client")
    if isinstance(client, tuple) and client:
        return str(client[0])
    return None


def _duration_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)


def _skip_health(path: str, status_code: int, enabled: bool) -> bool:
    return enabled and path == "/health" and status_code < 500
