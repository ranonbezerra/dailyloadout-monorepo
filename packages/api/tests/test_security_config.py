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
        turnstile_secret="ts-secret",  # pragma: allowlist secret
    )
    _validate_production_settings(s)  # should not raise


def test_production_requires_turnstile_secret() -> None:
    s = Settings(
        app_env="production",
        secret_key="real-secret",  # pragma: allowlist secret
        auth_cookie_secure=True,
        turnstile_secret="",
    )
    with pytest.raises(RuntimeError, match="turnstile_secret"):
        _validate_production_settings(s)


def test_production_unknown_app_env_is_treated_as_production() -> None:
    # Fail-safe: an unknown / typo'd / empty app_env must NOT relax hardening.
    for env in ("prod", "", "Production", "staging"):
        s = Settings(app_env=env, secret_key="change-me-in-prod")
        assert s.is_production is True
        with pytest.raises(RuntimeError):
            _validate_production_settings(s)


def test_dev_env_normalized_case_and_whitespace() -> None:
    # "Development "/" TESTING" still count as dev (normalised), staying relaxed.
    assert Settings(app_env="Development ").is_production is False
    assert Settings(app_env=" testing").is_production is False
