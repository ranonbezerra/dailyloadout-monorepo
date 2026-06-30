"""Optional Sentry init with mandatory PII scrubbing.

Sentry is OFF unless ``sentry_dsn`` is set. When enabled, the default FastAPI
integration would ship request headers (Authorization, Cookie), bodies (login/
register → email + plaintext password), and the OAuth callback URL (with the
authorization ``code``) to a third party. This init enforces ``send_default_pii
=False`` AND a ``before_send`` that strips those, so turning Sentry on can never
leak secrets/PII. The ``sentry-sdk`` dependency is an optional extra — a missing
install is logged and ignored, never fatal.
"""

from __future__ import annotations

from typing import Any

import structlog

from slate.config import settings

logger = structlog.get_logger()

# Request headers that must never reach Sentry.
_SENSITIVE_HEADERS = frozenset({"authorization", "cookie", "set-cookie", "cf-turnstile-response"})
# Query params that must never reach Sentry (OAuth code/state, stray tokens).
_SENSITIVE_QUERY_KEYS = ("code", "state", "token", "access_token", "refresh_token")


def _scrub(event: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any]:
    """Strip auth headers, request bodies, and sensitive query params."""
    request = event.get("request")
    if isinstance(request, dict):
        headers = request.get("headers")
        if isinstance(headers, dict):
            for name in list(headers):
                if name.lower() in _SENSITIVE_HEADERS:
                    headers[name] = "[redacted]"
        # Never ship request bodies (may contain passwords / tokens).
        request.pop("data", None)
        query = request.get("query_string")
        if isinstance(query, str) and any(k in query for k in _SENSITIVE_QUERY_KEYS):
            request["query_string"] = "[redacted]"
        url = request.get("url")
        if isinstance(url, str) and "?" in url:
            request["url"] = url.split("?", 1)[0]
    return event


def init_sentry() -> None:
    """Initialise Sentry with PII scrubbing, if a DSN is configured."""
    if not settings.sentry_dsn:
        return
    try:
        import sentry_sdk
    except ImportError:
        logger.warning("sentry_dsn_set_but_sdk_missing")
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        send_default_pii=False,
        before_send=_scrub,
        environment=settings.app_env,
    )
    logger.info("sentry_initialised", pii_scrubbing=True)
