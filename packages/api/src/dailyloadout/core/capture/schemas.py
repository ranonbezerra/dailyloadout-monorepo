"""Pydantic request / response schemas for the capture layer."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from dailyloadout.core.library.schemas import GameResponse, LibraryStatus

# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class CaptureTextRequest(BaseModel):
    """Body for ``POST /v1/captures/text``."""

    raw_text: str = Field(min_length=3, max_length=2000)
    input_type: Literal["text", "voice"] = "text"


class TranscribeResponse(BaseModel):
    """Response from ``POST /v1/captures/transcribe``."""

    text: str
    language: str | None = None
    duration_seconds: float | None = None


class CandidateConfirmRequest(BaseModel):
    """Body for confirming a capture candidate into the library."""

    platform_id: int
    status: LibraryStatus = "backlog"


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class CaptureCandidateResponse(BaseModel):
    """A single extracted game candidate from a capture."""

    public_id: UUID
    title: str
    platform_hint: str | None = None
    igdb_title: str | None = None
    igdb_cover_url: str | None = None
    igdb_summary: str | None = None
    igdb_genres: list[str] | None = None
    confidence: float | None = None
    status: str
    matched_game: GameResponse | None = None

    model_config = {"from_attributes": True}


class CaptureResponse(BaseModel):
    """Full capture with its candidates."""

    public_id: UUID
    input_type: str
    raw_text: str | None = None
    status: str
    error_message: str | None = None
    candidates: list[CaptureCandidateResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CaptureListItem(BaseModel):
    """Capture summary for list views."""

    public_id: UUID
    input_type: str
    raw_text: str | None = None
    status: str
    error_message: str | None = None
    candidate_titles: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CaptureListResponse(BaseModel):
    """Paginated list of captures."""

    items: list[CaptureListItem]
    total: int


# Valid capture statuses (for documentation / validation).
CaptureStatus = Literal[
    "queued",
    "processing",
    "review",
    "committed",
    "partially_committed",
    "failed",
    "cancelled",
]

CandidateStatus = Literal["pending", "confirmed", "rejected"]


__all__ = [
    "CandidateConfirmRequest",
    "CandidateStatus",
    "CaptureCandidateResponse",
    "CaptureListItem",
    "CaptureListResponse",
    "CaptureResponse",
    "CaptureStatus",
    "CaptureTextRequest",
    "TranscribeResponse",
]
