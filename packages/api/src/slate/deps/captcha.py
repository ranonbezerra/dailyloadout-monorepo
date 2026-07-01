"""Cloudflare Turnstile CAPTCHA verification dependency (config-driven).

The dependency is a **no-op when ``turnstile_secret`` is empty** (dev / not
configured), so local development and the test suite are unaffected. When the
secret is set, the ``cf-turnstile-response`` token (from header or JSON body) is
validated against Cloudflare's siteverify endpoint, and a missing/failed token
is rejected with **403**.
"""

from __future__ import annotations

import contextlib

import httpx
import structlog
from fastapi import HTTPException, Request, status

from slate.config import settings

logger = structlog.get_logger()

_HEADER_NAME = "cf-turnstile-response"
_BODY_FIELD = "cf-turnstile-response"


async def _extract_token(request: Request) -> str:
    """Read the Turnstile token from the header, falling back to the JSON body."""
    header_token = request.headers.get(_HEADER_NAME)
    if header_token:
        return header_token

    # Best-effort JSON body read; non-JSON bodies simply yield no token.
    with contextlib.suppress(Exception):
        body = await request.json()
        if isinstance(body, dict):
            value = body.get(_BODY_FIELD)
            if isinstance(value, str):
                return value
    return ""


async def _siteverify(token: str, remote_ip: str | None) -> bool:
    """Call Cloudflare siteverify; any error/failure means "not verified"."""
    payload = {"secret": settings.turnstile_secret, "response": token}
    if remote_ip:
        payload["remoteip"] = remote_ip
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(settings.turnstile_verify_url, data=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        logger.warning("turnstile_verify_error", exc_info=True)
        return False

    if not data.get("success"):
        # Surface Cloudflare's reason (e.g. timeout-or-duplicate, invalid token).
        logger.warning("turnstile_verify_rejected", error_codes=data.get("error-codes"))
        return False

    # Defense-in-depth: reject a token solved on a different site (same sitekey)
    # or a different widget/action, when the binding is configured.
    allowed_hosts = settings.turnstile_allowed_hostnames
    if allowed_hosts and data.get("hostname") not in allowed_hosts:
        logger.warning("turnstile_hostname_mismatch", hostname=data.get("hostname"))
        return False
    expected_action = settings.turnstile_expected_action
    if expected_action and data.get("action") != expected_action:
        logger.warning("turnstile_action_mismatch", action=data.get("action"))
        return False
    return True


async def verify_turnstile(request: Request) -> None:
    """Reject the request (403) when Turnstile is configured and verification fails.

    No-op when ``turnstile_secret`` is empty.
    """
    if not settings.turnstile_secret:
        return

    remote_ip = request.client.host if request.client else None
    path = str(request.scope.get("path", ""))

    token = await _extract_token(request)
    if not token:
        logger.warning("turnstile_token_missing", path=path, client_ip=remote_ip)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CAPTCHA verification required",
        )

    if not await _siteverify(token, remote_ip):
        logger.warning("turnstile_verify_failed", path=path, client_ip=remote_ip)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CAPTCHA verification failed",
        )
