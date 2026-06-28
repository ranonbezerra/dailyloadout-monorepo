"""Pydantic schemas for the backoffice admin surface."""

from __future__ import annotations

from datetime import date, datetime
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


class AdminGameSummary(BaseModel):
    """A game as shown in the backoffice catalogue table."""

    public_id: UUID
    slug: str
    title: str
    igdb_id: int | None
    source: str
    is_shared: bool
    cover_url: str | None
    owner_count: int
    created_at: datetime


class AdminGameList(BaseModel):
    """A page of games plus the total matching count and catalogue tallies."""

    items: list[AdminGameSummary]
    total: int
    limit: int
    offset: int
    catalogue_total: int
    catalogue_igdb: int
    catalogue_manual: int


class AdminGameDetail(AdminGameSummary):
    """The full backoffice view of a single game."""

    summary: str | None
    genres: list[str] | None
    first_release_date: date | None
    metadata_source: str
    created_by_email: str | None
    updated_at: datetime


class GameEditRequest(BaseModel):
    """Editable catalogue metadata (only provided fields change)."""

    title: str | None = Field(default=None, min_length=1, max_length=300)
    summary: str | None = Field(default=None, max_length=5000)


# ── Captures (moderation) ───────────────────────────────────────────────


class AdminCaptureSummary(BaseModel):
    """A capture as shown in the backoffice moderation table."""

    public_id: UUID
    user_email: str | None
    input_type: str
    status: str
    candidate_count: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class CaptureStatusCount(BaseModel):
    """A single ``(status, count)`` tally for the captures overview."""

    status: str
    count: int


class AdminCaptureList(BaseModel):
    """A page of captures plus the total count and per-status tallies."""

    items: list[AdminCaptureSummary]
    total: int
    limit: int
    offset: int
    status_counts: list[CaptureStatusCount]


class AdminCaptureCandidate(BaseModel):
    """An extracted candidate inside a capture's review queue."""

    public_id: UUID
    title: str
    status: str
    confidence: float | None
    igdb_id: int | None
    matched_game_title: str | None


class AdminCaptureDetail(AdminCaptureSummary):
    """The full backoffice view of one capture, with its candidates.

    ``reprocessable`` is True only when the source text survives (text/voice
    captures); photo/import captures store their upload in a temp file that is
    deleted after the first pass, so they cannot be re-run.
    """

    raw_text: str | None
    reprocessable: bool
    candidates: list[AdminCaptureCandidate]


# ── Missions (moderation) ───────────────────────────────────────────────


class AdminMissionSummary(BaseModel):
    """A mission as shown in the backoffice moderation table."""

    public_id: UUID
    user_email: str | None
    game_title: str | None
    status: str
    mission_type: str
    ended_via: str | None
    started_at: datetime
    ended_at: datetime | None


class MissionStatusCount(BaseModel):
    """A single ``(status, count)`` tally for the missions overview."""

    status: str
    count: int


class AdminMissionList(BaseModel):
    """A page of missions plus the total count and per-status tallies."""

    items: list[AdminMissionSummary]
    total: int
    limit: int
    offset: int
    status_counts: list[MissionStatusCount]


class AdminMissionDetail(AdminMissionSummary):
    """The full backoffice view of one mission.

    ``has_extracted_state`` reports whether the debrief LLM extraction ran
    (the raw JSON is omitted — it is untrusted model output, not moderation
    signal).
    """

    platform_label: str | None
    briefing_text: str | None
    debrief_text: str | None
    has_extracted_state: bool


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
