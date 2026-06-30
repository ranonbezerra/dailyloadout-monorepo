"""Tests for the post-VPS-audit hardening (logs, Sentry scrub, headers, PIL)."""

from __future__ import annotations

import io
import logging

import pytest
from httpx import AsyncClient
from PIL import Image

from slate.api._access_log import (
    RedactQueryStringFilter,
    install_access_log_redaction,
)
from slate.config import Settings, _validate_production_settings
from slate.core.capture.exceptions import InvalidUploadError
from slate.core.capture.ingestion import _verify_image_bytes
from slate.infrastructure import observability


def _prod(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "app_env": "production",
        "secret_key": "x" * 48,
        "auth_cookie_secure": True,
        "turnstile_secret": "ts",  # pragma: allowlist secret
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


# ── access-log query-string redaction (#4) ──────────────────────────────


def test_access_log_filter_strips_query() -> None:
    record = logging.makeLogRecord({})
    path = "/v1/auth/oauth/google/callback?code=SECRET&state=x"
    record.args = ("1.2.3.4", "GET", path, "1.1", 302)
    assert RedactQueryStringFilter().filter(record) is True
    assert record.args[2] == "/v1/auth/oauth/google/callback"
    assert "SECRET" not in str(record.args)


def test_access_log_filter_keeps_path_without_query() -> None:
    record = logging.makeLogRecord({})
    record.args = ("1.2.3.4", "GET", "/health", "1.1", 200)
    RedactQueryStringFilter().filter(record)
    assert record.args[2] == "/health"


def test_install_access_log_redaction_is_idempotent() -> None:
    log = logging.getLogger("uvicorn.access")
    before = [f for f in log.filters if isinstance(f, RedactQueryStringFilter)]
    install_access_log_redaction()
    install_access_log_redaction()
    added = [f for f in log.filters if isinstance(f, RedactQueryStringFilter)]
    assert len(added) == len(before) + 1
    log.removeFilter(added[-1])


# ── Sentry PII scrubber (#10) ────────────────────────────────────────────


def test_init_sentry_noop_without_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(observability.sentry.settings, "sentry_dsn", "")
    observability.init_sentry()  # must not raise / must not import sentry_sdk


def test_scrub_redacts_headers_body_and_query() -> None:
    event = {
        "request": {
            "headers": {"Authorization": "Bearer x", "Cookie": "a=b", "User-Agent": "ua"},
            "data": {
                "email": "a@b.com",
                "password": "hunter2",  # pragma: allowlist secret
            },
            "query_string": "code=SECRET&state=y",
            "url": "https://api/v1/auth/oauth/google/callback?code=SECRET",
        }
    }
    out = observability.sentry._scrub(event, {})
    req = out["request"]
    assert req["headers"]["Authorization"] == "[redacted]"
    assert req["headers"]["Cookie"] == "[redacted]"
    assert req["headers"]["User-Agent"] == "ua"
    assert "data" not in req
    assert req["query_string"] == "[redacted]"
    assert "?" not in req["url"]


# ── secret_key length + trusted_hosts (#8) ───────────────────────────────


def test_prod_rejects_short_secret_key() -> None:
    with pytest.raises(RuntimeError, match="too short"):
        _validate_production_settings(_prod(secret_key="short"))  # pragma: allowlist secret


def test_prod_accepts_long_secret_key() -> None:
    _validate_production_settings(_prod())  # 48-char secret, must not raise


def test_trusted_hosts_default_allows_all() -> None:
    assert Settings().trusted_hosts == ["*"]


# ── security headers: CSP + Permissions-Policy (#9) ──────────────────────


async def test_csp_and_permissions_policy_headers(async_client: AsyncClient) -> None:
    resp = await async_client.get("/health")
    assert resp.headers["content-security-policy"] == "default-src 'none'; frame-ancestors 'none'"
    assert "permissions-policy" in resp.headers
    assert resp.headers["x-frame-options"] == "DENY"


# ── Pillow decompression-bomb guard (#3) ─────────────────────────────────


def test_pillow_max_pixels_is_bounded() -> None:
    assert Image.MAX_IMAGE_PIXELS is not None
    assert Image.MAX_IMAGE_PIXELS <= 40_000_000


def test_verify_rejects_decompression_bomb(monkeypatch: pytest.MonkeyPatch) -> None:
    buf = io.BytesIO()
    Image.new("RGB", (200, 200)).save(buf, format="PNG")
    data = buf.getvalue()
    # A valid small image passes...
    _verify_image_bytes(data)
    # ...but with the cap dropped below its pixel count it's rejected as a bomb.
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 100)
    with pytest.raises(InvalidUploadError):
        _verify_image_bytes(data)
