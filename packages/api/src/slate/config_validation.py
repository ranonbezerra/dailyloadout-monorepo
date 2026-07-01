"""Fail-fast production configuration guard (split out of config.py).

Dev/test may relax these so http://localhost keeps working; any other environment
is treated as production and must be hardened. Imported + invoked at the bottom of
``config.py`` after ``settings`` is built.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from slate.config import Settings


def validate_production_settings(s: Settings) -> None:
    """Raise ``RuntimeError`` on insecure production configuration."""
    if not s.is_production:
        return

    if s.secret_key == "change-me-in-prod":
        raise RuntimeError(
            "FATAL: secret_key is still the default value. "
            "Set the SECRET_KEY environment variable before running in production."
        )

    if len(s.secret_key) < 32:
        raise RuntimeError(
            "FATAL: secret_key is too short for production (< 32 chars). "
            "Use a high-entropy value (e.g. `secrets.token_urlsafe(48)`)."
        )

    if not s.auth_cookie_secure:
        raise RuntimeError(
            "FATAL: auth_cookie_secure must be True in production. "
            "Refresh-token cookies must only be sent over HTTPS."
        )

    if s.auth_cookie_samesite == "none" and not s.auth_cookie_secure:
        raise RuntimeError("FATAL: auth_cookie_samesite='none' requires auth_cookie_secure=True.")

    if s.single_user_mode:
        raise RuntimeError(
            "FATAL: single_user_mode must be False in production. "
            "It bypasses JWT auth and returns a fixed account for every request."
        )

    if not s.turnstile_secret:
        raise RuntimeError(
            "FATAL: turnstile_secret must be set in production. The registration "
            "CAPTCHA is the primary defence against mass account creation."
        )

    # Host/CORS hardening: a wildcard Host allowlist accepts any Host header
    # (routing / cache-poisoning), and a wildcard/localhost CORS origin with
    # allow_credentials=True would let any site ride the user's cookies.
    if "*" in s.trusted_hosts:
        raise RuntimeError(
            "FATAL: trusted_hosts must not be ['*'] in production — pin the API domain(s)."
        )

    bad_origin = next(
        (
            o
            for o in s.cors_origins
            if o == "*" or o.startswith(("http://localhost", "http://127."))
        ),
        None,
    )
    if bad_origin is not None:
        raise RuntimeError(
            f"FATAL: cors_origins must not include '*' or localhost in production "
            f"(allow_credentials is on); found {bad_origin!r}."
        )
