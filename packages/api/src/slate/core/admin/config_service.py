"""Backoffice dynamic-config service (Epic 21, Phase 3).

Reads and edits the curated operational knobs: list every key with its
effective/override/baseline values, set an override (validated against the
registry), or clear it back to the env/code baseline. Every write is audited and
invalidates the in-process overlay cache so the change takes effect promptly.
Layer discipline: orchestrates the repos + overlay; never touches a Session.
"""

from __future__ import annotations

from slate.config import settings
from slate.core.admin.logging import log_admin_event
from slate.core.admin.schemas import ConfigEntry, ConfigListResponse
from slate.infrastructure.config.dynamic import DynamicConfig
from slate.infrastructure.config.registry import (
    CONFIG_REGISTRY,
    ConfigKeySpec,
    validate_value,
)
from slate.infrastructure.db.models import User
from slate.infrastructure.db.repositories.admin import AdminAuditRepository
from slate.infrastructure.db.repositories.app_config import AppConfigRepository

ACTION_CONFIG_SET = "config.set"
ACTION_CONFIG_CLEAR = "config.clear"


class UnknownConfigKeyError(Exception):
    """Raised when a config action names a key outside the curated registry."""


class AdminConfigService:
    """Read/edit the curated dynamic operational config."""

    def __init__(
        self,
        config_repo: AppConfigRepository,
        audit_repo: AdminAuditRepository,
        overlay: DynamicConfig,
    ) -> None:
        self._config = config_repo
        self._audit = audit_repo
        self._overlay = overlay

    async def list_config(self) -> ConfigListResponse:
        """Return every curated key with effective/override/baseline values."""
        overrides = await self._config.list_with_updater()
        items: list[ConfigEntry] = []
        for spec in CONFIG_REGISTRY.values():
            baseline = self._baseline(spec)
            pair = overrides.get(spec.key)
            if pair is not None:
                row, updater_pid = pair
                override_value = _as_value(row.value)
                items.append(
                    ConfigEntry(
                        key=spec.key,
                        kind=spec.kind,
                        category=spec.category,
                        description=spec.description,
                        effective_value=override_value,
                        override_value=override_value,
                        baseline_value=baseline,
                        is_overridden=True,
                        min_value=spec.min_value,
                        max_value=spec.max_value,
                        updated_at=row.updated_at,
                        updated_by=updater_pid,
                    )
                )
            else:
                items.append(
                    ConfigEntry(
                        key=spec.key,
                        kind=spec.kind,
                        category=spec.category,
                        description=spec.description,
                        effective_value=baseline,
                        override_value=None,
                        baseline_value=baseline,
                        is_overridden=False,
                        min_value=spec.min_value,
                        max_value=spec.max_value,
                        updated_at=None,
                        updated_by=None,
                    )
                )
        return ConfigListResponse(items=items)

    async def set_override(self, actor: User, key: str, value: bool | int) -> ConfigListResponse:
        """Validate and store an override for *key*, audited; return the new list.

        Raises ``UnknownConfigKeyError`` for a non-curated key and
        ``ConfigValidationError`` (from the registry) for a bad type/range.
        """
        spec = self._require_spec(key)
        typed = validate_value(spec, value)
        await self._config.upsert(key, typed, actor.id)
        self._overlay.invalidate(key)
        await self._audit.record(
            admin_user_id=actor.id,
            action=ACTION_CONFIG_SET,
            detail=f"{key} = {typed}",
        )
        log_admin_event(
            "admin_config_set",
            actor=actor,
            action=ACTION_CONFIG_SET,
            config_key=key,
            config_value=typed,
        )
        return await self.list_config()

    async def clear_override(self, actor: User, key: str) -> ConfigListResponse:
        """Delete the override for *key* (revert to baseline), audited."""
        self._require_spec(key)
        await self._config.delete(key)
        self._overlay.invalidate(key)
        await self._audit.record(
            admin_user_id=actor.id,
            action=ACTION_CONFIG_CLEAR,
            detail=key,
        )
        log_admin_event(
            "admin_config_cleared",
            actor=actor,
            action=ACTION_CONFIG_CLEAR,
            config_key=key,
        )
        return await self.list_config()

    # ── Internals ──
    @staticmethod
    def _require_spec(key: str) -> ConfigKeySpec:
        spec = CONFIG_REGISTRY.get(key)
        if spec is None:
            raise UnknownConfigKeyError(key)
        return spec

    @staticmethod
    def _baseline(spec: ConfigKeySpec) -> bool | int:
        return _as_value(getattr(settings, spec.settings_attr))


def _as_value(raw: object) -> bool | int:
    """Narrow a stored/baseline value to the bool|int the schema expects."""
    if isinstance(raw, bool | int):
        return raw
    raise TypeError(f"config value must be bool or int, got {type(raw).__name__}")
