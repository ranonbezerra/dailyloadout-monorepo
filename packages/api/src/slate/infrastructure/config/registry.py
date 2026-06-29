"""The curated set of runtime-overridable operational knobs (Epic 21, Phase 3).

Only keys listed here can be overridden at runtime via the backoffice; every
other setting stays env-only (secrets/infra change *is* a deploy concern). Each
spec names the ``settings`` attribute it overlays (the env/code baseline) plus
the type and validation bounds enforced on write. Keeping this list small and
explicit is the whole point — it is the contract for what is safe to flip live.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ConfigKind = Literal["bool", "int"]


@dataclass(frozen=True, slots=True)
class ConfigKeySpec:
    """Metadata for one overridable key: its type, baseline, and bounds."""

    key: str
    kind: ConfigKind
    settings_attr: str
    category: str
    description: str
    min_value: int | None = None
    max_value: int | None = None


def _spec(spec: ConfigKeySpec) -> tuple[str, ConfigKeySpec]:
    return spec.key, spec


# The curated registry. Categories group the keys for the backoffice UI.
CONFIG_REGISTRY: dict[str, ConfigKeySpec] = dict(
    [
        # ── Kill-switches ──
        _spec(
            ConfigKeySpec(
                "rate_limit_enabled",
                "bool",
                "rate_limit_enabled",
                "kill_switch",
                "Master switch for per-user/IP rate limiting.",
            )
        ),
        _spec(
            ConfigKeySpec(
                "cost_guard_enabled",
                "bool",
                "cost_guard_enabled",
                "kill_switch",
                "Master switch for the LLM cost kill-switch (spend caps).",
            )
        ),
        _spec(
            ConfigKeySpec(
                "concierge_write_tools_enabled",
                "bool",
                "concierge_write_tools_enabled",
                "kill_switch",
                "Allow the Concierge to call write tools (create play_sessions, etc.).",
            )
        ),
        # ── Incident-tunable caps ──
        _spec(
            ConfigKeySpec(
                "cost_user_per_day",
                "int",
                "cost_user_per_day",
                "cap",
                "Per-user daily LLM cost ceiling (units ≈ requests).",
                min_value=0,
                max_value=1_000_000,
            )
        ),
        _spec(
            ConfigKeySpec(
                "cost_global_per_day",
                "int",
                "cost_global_per_day",
                "cap",
                "Global daily LLM cost ceiling across all users.",
                min_value=0,
                max_value=10_000_000,
            )
        ),
        _spec(
            ConfigKeySpec(
                "rate_limit_register_per_minute",
                "int",
                "rate_limit_register_per_minute",
                "cap",
                "Registrations/verification-resends allowed per IP per minute.",
                min_value=1,
                max_value=10_000,
            )
        ),
        _spec(
            ConfigKeySpec(
                "igdb_user_budget_per_day",
                "int",
                "igdb_user_budget_per_day",
                "cap",
                "Per-user daily IGDB search budget (bulk-import abuse cap).",
                min_value=0,
                max_value=1_000_000,
            )
        ),
        # ── Product rules ──
        _spec(
            ConfigKeySpec(
                "catalog_share_threshold",
                "int",
                "catalog_share_threshold",
                "product",
                "How many users must own a game before it joins the shared catalogue.",
                min_value=1,
                max_value=10_000,
            )
        ),
        _spec(
            ConfigKeySpec(
                "block_disposable_emails",
                "bool",
                "block_disposable_emails",
                "product",
                "Reject sign-ups from known disposable-email domains.",
            )
        ),
    ]
)


class ConfigValidationError(ValueError):
    """Raised when a proposed override value violates its key's spec."""


def validate_value(spec: ConfigKeySpec, value: object) -> bool | int:
    """Coerce/validate *value* against *spec*; return the typed value or raise.

    Rejects type mismatches (note: ``bool`` is *not* accepted for int keys, and
    ``int`` is *not* accepted for bool keys) and out-of-range integers.
    """
    if spec.kind == "bool":
        if not isinstance(value, bool):
            raise ConfigValidationError(f"{spec.key} expects a boolean")
        return value
    # int key
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigValidationError(f"{spec.key} expects an integer")
    if spec.min_value is not None and value < spec.min_value:
        raise ConfigValidationError(f"{spec.key} must be >= {spec.min_value}")
    if spec.max_value is not None and value > spec.max_value:
        raise ConfigValidationError(f"{spec.key} must be <= {spec.max_value}")
    return value
