"""Production config guard: wildcard host/CORS rejection (security hardening)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest

from slate.config import Settings
from slate.config_validation import validate_production_settings


def _prod(**overrides: Any) -> Settings:
    base: dict[str, Any] = {
        "is_production": True,
        "secret_key": "x" * 40,
        "auth_cookie_secure": True,
        "auth_cookie_samesite": "lax",
        "single_user_mode": False,
        "turnstile_secret": "t",
        "trusted_hosts": ["api.slate.app"],
        "cors_origins": ["https://slate.app"],
    }
    base.update(overrides)
    return cast(Settings, SimpleNamespace(**base))


class TestProdGuard:
    def test_valid_prod_config_passes(self) -> None:
        validate_production_settings(_prod())  # no raise

    def test_rejects_wildcard_trusted_hosts(self) -> None:
        with pytest.raises(RuntimeError, match="trusted_hosts"):
            validate_production_settings(_prod(trusted_hosts=["*"]))

    def test_rejects_wildcard_cors(self) -> None:
        with pytest.raises(RuntimeError, match="cors_origins"):
            validate_production_settings(_prod(cors_origins=["*"]))

    def test_rejects_localhost_cors(self) -> None:
        with pytest.raises(RuntimeError, match="cors_origins"):
            validate_production_settings(_prod(cors_origins=["http://localhost:3000"]))

    def test_dev_skips_every_check(self) -> None:
        # Non-production relaxes everything so localhost dev keeps working.
        validate_production_settings(
            _prod(is_production=False, trusted_hosts=["*"], secret_key="short")
        )