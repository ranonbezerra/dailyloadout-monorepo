"""uvicorn access-log hardening: strip query strings from logged request lines.

The OAuth callback (`/v1/auth/oauth/{provider}/callback?state=…&code=…`) carries
a single-use authorization code in the query string. uvicorn's default access
logger writes the full request line (path + query), so the code would land in
stdout / journald / any log shipper on the VPS. This filter rewrites the logged
path to drop everything after ``?`` for every request, so no query param (OAuth
code/state, a stray token) is ever persisted in access logs.

Keeps access logging on (useful for ops) — only the query string is redacted.
The reverse proxy (Caddy) must likewise avoid logging query strings.
"""

from __future__ import annotations

import logging


class RedactQueryStringFilter(logging.Filter):
    """Drop the ``?query`` from the request path in uvicorn.access records."""

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        # uvicorn.access args: (client_addr, method, full_path, http_version, status)
        if isinstance(args, tuple) and len(args) >= 3 and isinstance(args[2], str):
            path = args[2]
            if "?" in path:
                record.args = (*args[:2], path.split("?", 1)[0], *args[3:])
        return True


def install_access_log_redaction() -> None:
    """Attach the redaction filter to the uvicorn access logger (idempotent)."""
    access_logger = logging.getLogger("uvicorn.access")
    if not any(isinstance(f, RedactQueryStringFilter) for f in access_logger.filters):
        access_logger.addFilter(RedactQueryStringFilter())
