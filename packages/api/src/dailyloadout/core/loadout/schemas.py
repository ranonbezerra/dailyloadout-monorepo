"""Pydantic request / response schemas for the loadout layer."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from dailyloadout.core.library.schemas import LibraryEntryResponse

# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

LoadoutMood = Literal["chill", "focused", "energetic", "adventurous"]
MentalEnergy = Literal["low", "medium", "high"]


class LoadoutCreateRequest(BaseModel):
    """Body for ``POST /v1/loadouts``."""

    mood: LoadoutMood
    available_minutes: int = Field(ge=10, le=480)
    mental_energy: MentalEnergy
    context: str | None = Field(default=None, max_length=120)
    count: int = Field(default=1, ge=1, le=3)


class LoadoutAcceptRequest(BaseModel):
    """Optional body for ``POST /v1/loadouts/{id}/accept``.

    Mirrors the mission-start briefing stage: pass a pre-generated
    *briefing_text* (e.g. from the preview flow) to start the mission with a
    briefing, or omit it to start without one.
    """

    briefing_text: str | None = None


class LoadoutStartRequest(BaseModel):
    """Body for ``POST /v1/loadouts/start`` — AI-pick a game and start a
    mission in one step (the DECIDE=AI entrance to the mission pipeline)."""

    mood: LoadoutMood
    available_minutes: int = Field(ge=10, le=480)
    mental_energy: MentalEnergy
    context: str | None = Field(default=None, max_length=120)
    briefing_text: str | None = None


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class LoadoutResponse(BaseModel):
    """Full loadout with related library entry."""

    public_id: UUID
    library_entry: LibraryEntryResponse | None = None
    mood: str
    available_minutes: int
    mental_energy: str
    context: str | None = None
    reasoning: str | None = None
    action: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LoadoutListItem(BaseModel):
    """Loadout summary for list views."""

    public_id: UUID
    library_entry: LibraryEntryResponse | None = None
    mood: str
    available_minutes: int
    mental_energy: str
    context: str | None = None
    reasoning: str | None = None
    action: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class LoadoutListResponse(BaseModel):
    """Paginated list of loadouts."""

    items: list[LoadoutListItem]
    total: int


__all__ = [
    "LoadoutCreateRequest",
    "LoadoutListItem",
    "LoadoutListResponse",
    "LoadoutMood",
    "LoadoutResponse",
    "MentalEnergy",
]
