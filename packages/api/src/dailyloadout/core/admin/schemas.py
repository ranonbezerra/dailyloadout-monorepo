"""Pydantic schemas for the backoffice admin surface."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt


class AdminMeResponse(BaseModel):
    """The authenticated admin's identity — used by the backoffice to confirm
    that the current session holds admin rights before rendering the panel.
    """

    model_config = ConfigDict(from_attributes=True)

    public_id: UUID
    email: str
    display_name: str


# ── Users management ────────────────────────────────────────────────────


class AdminUserSummary(BaseModel):
    """A user as shown in the backoffice list/search table."""

    model_config = ConfigDict(from_attributes=True)

    public_id: UUID
    email: str
    display_name: str
    email_verified: bool
    is_banned: bool
    created_at: datetime


class AdminUserListResponse(BaseModel):
    """A page of users plus the total matching count for pagination."""

    items: list[AdminUserSummary]
    total: int
    limit: int
    offset: int


class AdminUserDetail(AdminUserSummary):
    """The full backoffice view of a single user.

    Adds fields the list omits: profile metadata, whether the account is an
    admin / has a password (vs. OAuth-only), and the live active-session count.
    """

    avatar_url: str | None
    locale: str
    timezone: str
    is_admin: bool
    has_password: bool
    active_sessions: int


class BanRequest(BaseModel):
    """Optional reason recorded in the audit trail when banning a user."""

    reason: str | None = Field(default=None, max_length=500)


# ── Audit log ───────────────────────────────────────────────────────────


class AdminAuditEntry(BaseModel):
    """One audited admin action, with actor and target identities resolved."""

    action: str
    detail: str | None
    created_at: datetime
    admin_public_id: UUID | None
    admin_email: str | None
    target_public_id: UUID | None
    target_email: str | None


class AdminAuditListResponse(BaseModel):
    """A page of audit entries plus the total count for pagination."""

    items: list[AdminAuditEntry]
    total: int
    limit: int
    offset: int


# ── Dynamic operational config ──────────────────────────────────────────


class ConfigEntry(BaseModel):
    """One curated operational knob: its effective value, override, and baseline.

    ``effective_value`` is what the app actually uses now (override if set, else
    baseline). ``override_value`` is the runtime override (``None`` when unset).
    ``baseline_value`` is the env/code default the override sits on top of.
    """

    key: str
    kind: str
    category: str
    description: str
    effective_value: bool | int
    override_value: bool | int | None
    baseline_value: bool | int
    is_overridden: bool
    min_value: int | None
    max_value: int | None
    updated_at: datetime | None
    updated_by: UUID | None


class ConfigListResponse(BaseModel):
    """Every curated knob with its current effective/override/baseline values."""

    items: list[ConfigEntry]


class DashboardSummary(BaseModel):
    """At-a-glance backoffice metrics for the dashboard landing screen."""

    users_total: int
    users_banned: int
    users_unverified: int
    admins: int
    missions_active: int
    catalogue_size: int
    config_overrides: int
    recent_actions: list[AdminAuditEntry]


class ConfigSetRequest(BaseModel):
    """A new override value for a curated key.

    ``StrictBool | StrictInt`` (bool first) prevents Pydantic from coercing
    ``5`` into ``True`` or ``true`` into ``1``; the registry then enforces the
    key's actual type and bounds.
    """

    value: StrictBool | StrictInt
