"""Production-guard validation in config.py and new security defaults."""

from __future__ import annotations

import pytest

from dailyloadout.config import Settings, _validate_production_settings


def test_cookie_secure_defaults_true() -> None:
    assert Settings().auth_cookie_secure is True


def test_igdb_candidate_cap_lowered() -> None:
    assert Settings().library_import_max_candidates == 40


def test_dev_env_skips_validation() -> None:
    # Insecure values are allowed in development/testing.
    s = Settings(app_env="development", auth_cookie_secure=False)
    _validate_production_settings(s)  # should not raise


def test_production_rejects_default_secret() -> None:
    s = Settings(app_env="production", secret_key="change-me-in-prod", auth_cookie_secure=True)
    with pytest.raises(RuntimeError, match="secret_key"):
        _validate_production_settings(s)


def test_production_rejects_insecure_cookie() -> None:
    s = Settings(app_env="production", secret_key="real-secret", auth_cookie_secure=False)
    with pytest.raises(RuntimeError, match="auth_cookie_secure"):
        _validate_production_settings(s)


def test_production_accepts_hardened_settings() -> None:
    s = Settings(
        app_env="production",
        secret_key="real-secret",  # pragma: allowlist secret
        auth_cookie_secure=True,
        auth_cookie_samesite="none",
    )
    _validate_production_settings(s)  # should not raise
