"""Pydantic request / response schemas for the pick layer."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from slate.core.library.schemas import LibraryEntryResponse

# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

PickMood = Literal["chill", "focused", "energetic", "adventurous"]
MentalEnergy = Literal["low", "medium", "high"]


class PickCreateRequest(BaseModel):
    """Body for ``POST /v1/picks``."""

    mood: PickMood
    available_minutes: int = Field(ge=10, le=480)
    mental_energy: MentalEnergy
    context: str | None = Field(default=None, max_length=120)
    count: int = Field(default=1, ge=1, le=3)


class PickAcceptRequest(BaseModel):
    """Optional body for ``POST /v1/picks/{id}/accept``.

    Mirrors the play_session-start recap stage: pass a pre-generated
    *recap_text* (e.g. from the preview flow) to start the play_session with a
    recap, or omit it to start without one.
    """

    recap_text: str | None = None


class PickStartRequest(BaseModel):
    """Body for ``POST /v1/picks/start`` — AI-pick a game and start a
    play_session in one step (the DECIDE=AI entrance to the play_session pipeline)."""

    mood: PickMood
    available_minutes: int = Field(ge=10, le=480)
    mental_energy: MentalEnergy
    context: str | None = Field(default=None, max_length=120)
    recap_text: str | None = None


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class PickResponse(BaseModel):
    """Full pick with related library entry."""

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


class PickListItem(BaseModel):
    """Pick summary for list views."""

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


class PickListResponse(BaseModel):
    """Paginated list of picks."""

    items: list[PickListItem]
    total: int


__all__ = [
    "MentalEnergy",
    "PickCreateRequest",
    "PickListItem",
    "PickListResponse",
    "PickMood",
    "PickResponse",
]
