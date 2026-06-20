"""Pydantic request / response schemas for the mission layer."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from dailyloadout.core.library.schemas import LibraryEntryResponse

# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class MissionStartRequest(BaseModel):
    """Body for ``POST /v1/missions``."""

    library_entry_public_id: UUID
    briefing_text: str | None = Field(
        default=None,
        description="Pre-generated briefing from a preview call. Skips LLM generation.",
    )


class BriefingPreviewRequest(BaseModel):
    """Body for ``POST /v1/missions/preview-briefing``."""

    library_entry_public_id: UUID
    position_override: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional player-provided correction of their current in-game position.",
    )


class RetroactiveDebriefRequest(BaseModel):
    """Body for ``POST /v1/missions/retroactive-debrief``."""

    library_entry_public_id: UUID
    debrief_text: str = Field(min_length=3, max_length=5000)


class MissionDebriefRequest(BaseModel):
    """Body for ``PATCH /v1/missions/{public_id}/debrief``."""

    debrief_text: str = Field(min_length=3, max_length=5000)


class MissionEndRequest(BaseModel):
    """Body for ``POST /v1/missions/{public_id}/end``."""

    ended_via: Literal["paused_app"] = "paused_app"


class RegenerateBriefingRequest(BaseModel):
    """Body for ``POST /v1/missions/{public_id}/briefing/regenerate``."""

    current_position: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional player-provided correction of their current in-game position.",
    )


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class MissionResponse(BaseModel):
    """Full mission with related library entry."""

    public_id: UUID
    library_entry: LibraryEntryResponse
    mission_type: str = "regular"
    briefing_text: str | None = None
    debrief_text: str | None = None
    extracted_state: dict[str, Any] | None = None
    ended_via: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    last_session_context: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class MissionListItem(BaseModel):
    """Mission summary for list views."""

    public_id: UUID
    library_entry: LibraryEntryResponse
    mission_type: str = "regular"
    ended_via: str | None = None
    started_at: datetime
    ended_at: datetime | None = None

    model_config = {"from_attributes": True}


class MissionListResponse(BaseModel):
    """Paginated list of missions."""

    items: list[MissionListItem]
    total: int


class BriefingPreviewResponse(BaseModel):
    """Briefing preview without creating a mission."""

    library_entry: LibraryEntryResponse
    briefing_text: str | None = None
    last_session_context: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


# Valid ended_via values (for documentation / validation).
EndedVia = Literal["debrief_completed", "paused_app", "auto_clamp", "retroactive"]

MissionType = Literal["regular", "retroactive"]

MissionStatus = Literal["active", "ended"]


__all__ = [
    "BriefingPreviewRequest",
    "BriefingPreviewResponse",
    "EndedVia",
    "MissionDebriefRequest",
    "MissionEndRequest",
    "MissionListItem",
    "MissionListResponse",
    "MissionResponse",
    "MissionStartRequest",
    "MissionStatus",
    "MissionType",
    "RegenerateBriefingRequest",
    "RetroactiveDebriefRequest",
]
