"""Breached-password check — a hexagonal port, local by default, HIBP optional.

NIST 800-63B recommends rejecting passwords known to be compromised. Same shape as
the LLM / research / embedding ports: a local, dependency-free default, with an
optional cloud adapter selected by env — so the hosted build can opt into the full
breach corpus while a self-hosted instance never phones home.

- ``local`` (default): the curated common-password blocklist (``password_breach``).
- ``hibp``: Have I Been Pwned's Pwned Passwords range API via **k-anonymity** — only
  the first 5 hex chars of the SHA-1 leave the server; the password never does.
  **Best-effort / fail-open**: any network/HTTP error means "not breached", so a
  third-party outage can never block registration.
- ``null``: always allow (tests / disabled).
"""

from __future__ import annotations

import hashlib
from typing import Protocol

import httpx
import structlog

from slate.config import settings
from slate.core.auth.password_breach import is_common_password

logger = structlog.get_logger()

_HIBP_RANGE_URL = "https://api.pwnedpasswords.com/range/"


class BreachedPasswordError(ValueError):
    """Raised when a chosen password is known-compromised / too common."""


class AbstractBreachedPasswordChecker(Protocol):
    """Port: is this password known to be compromised?"""

    async def is_breached(self, password: str) -> bool: ...


class LocalBlocklistChecker:
    """Offline default — the curated common-password blocklist."""

    async def is_breached(self, password: str) -> bool:
        return is_common_password(password)


class NullBreachChecker:
    """No-op checker (tests / explicitly disabled)."""

    async def is_breached(self, password: str) -> bool:
        return False


class HIBPChecker:
    """Have I Been Pwned Pwned-Passwords check via k-anonymity (best-effort)."""

    async def is_breached(self, password: str) -> bool:
        # HIBP's range API is defined over SHA-1; this is protocol, not a security
        # choice (the password never leaves the box — only a 5-char hash prefix does).
        digest = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()  # noqa: S324  # nosec
        prefix, suffix = digest[:5], digest[5:]
        try:
            async with httpx.AsyncClient(timeout=settings.hibp_timeout_seconds) as client:
                resp = await client.get(
                    f"{_HIBP_RANGE_URL}{prefix}",
                    headers={"Add-Padding": "true"},  # uniform response size (privacy)
                )
                resp.raise_for_status()
                text = resp.text
        except Exception:
            # Fail-open: never block a signup on a HIBP outage.
            logger.warning("hibp_lookup_failed", exc_info=True)
            return False
        # Each line is "SUFFIX:count"; the password is breached if its suffix appears
        # with a non-zero count (padded rows carry count 0).
        for line in text.splitlines():
            candidate, _, count = line.partition(":")
            if candidate.strip() == suffix and count.strip() not in ("", "0"):
                return True
        return False


def get_breach_checker() -> AbstractBreachedPasswordChecker:
    """Return the configured breach checker (``password_breach_provider``)."""
    provider = settings.password_breach_provider
    if provider == "hibp":
        return HIBPChecker()
    if provider == "null":
        return NullBreachChecker()
    return LocalBlocklistChecker()


async def assert_password_not_breached(
    checker: AbstractBreachedPasswordChecker, password: str
) -> None:
    """Raise ``BreachedPasswordError`` if *password* is known-compromised/too-common."""
    if await checker.is_breached(password):
        raise BreachedPasswordError(
            "This password has appeared in a data breach — choose a stronger one"
        )
