"""Pydantic request / response schemas for the capture layer."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from slate.core.library.schemas import GameResponse, LibraryStatus
from slate.core.sanitization import strip_control_chars

# Bound the bulk-confirm payload: an import is at most a few hundred candidates,
# so these caps are generous but stop a runaway request.
_MAX_CONFIRM_IDS = 500
_MAX_TITLE_OVERRIDES = 500
_MAX_OVERRIDE_TITLE_LEN = 200

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


class CandidateRematchRequest(BaseModel):
    """Body for re-searching IGDB on a corrected candidate title.

    Used by the import-review screen: the user fixes a wrong title and asks for a
    fresh catalog match before committing, so the saved game's metadata
    (cover/summary/genres) lines up with the corrected title.
    """

    title: str = Field(min_length=1, max_length=_MAX_OVERRIDE_TITLE_LEN)


class BulkConfirmRequest(BaseModel):
    """Body for ``POST /v1/captures/{id}/candidates/bulk-confirm``.

    Confirm the listed candidates onto *platform_id*; every other pending
    candidate in the capture is rejected. Commits a whole library import at once.

    *title_overrides* maps a candidate's ``public_id`` to a corrected title — for
    fixing OCR mistakes before committing. An overridden candidate is committed
    as a user-authored title (its prior catalog match is dropped).

    *status_overrides* maps a candidate's ``public_id`` to a per-game library
    status, so each imported game can land as backlog/playing/etc. independently;
    candidates without an override fall back to the batch-level ``status``.
    """

    confirm_public_ids: list[UUID] = Field(default_factory=list, max_length=_MAX_CONFIRM_IDS)
    platform_id: int
    status: LibraryStatus = "backlog"
    title_overrides: dict[UUID, str] = Field(default_factory=dict, max_length=_MAX_TITLE_OVERRIDES)
    status_overrides: dict[UUID, LibraryStatus] = Field(
        default_factory=dict, max_length=_MAX_CONFIRM_IDS
    )

    @model_validator(mode="after")
    def _sanitize_overrides(self) -> BulkConfirmRequest:
        """Bound and clean ``title_overrides``.

        - Reject keys not present in ``confirm_public_ids`` (an override for a
          candidate that isn't being confirmed is meaningless and lets a caller
          smuggle extra titles).
        - Cap each override length and strip control chars (prompt-injection +
          catalog-poisoning guard).
        """
        confirm_set = set(self.confirm_public_ids)
        cleaned: dict[UUID, str] = {}
        for key, value in self.title_overrides.items():
            if key not in confirm_set:
                raise ValueError("title_overrides keys must be in confirm_public_ids.")
            stripped = strip_control_chars(value).strip()
            if len(stripped) > _MAX_OVERRIDE_TITLE_LEN:
                raise ValueError(
                    f"Override titles must be at most {_MAX_OVERRIDE_TITLE_LEN} characters."
                )
            cleaned[key] = stripped
        self.title_overrides = cleaned

        # A status override only makes sense for a candidate being confirmed.
        for key in self.status_overrides:
            if key not in confirm_set:
                raise ValueError("status_overrides keys must be in confirm_public_ids.")
        return self


class BulkConfirmResponse(BaseModel):
    """Outcome of a bulk confirm: how many were committed vs rejected."""

    confirmed: int
    rejected: int


class DuplicatesResponse(BaseModel):
    """Candidate ``public_id``s already in the library for a given platform."""

    duplicate_public_ids: list[UUID] = Field(default_factory=list)


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
    "BulkConfirmRequest",
    "BulkConfirmResponse",
    "CandidateConfirmRequest",
    "CandidateStatus",
    "CaptureCandidateResponse",
    "CaptureListItem",
    "CaptureListResponse",
    "CaptureResponse",
    "CaptureStatus",
    "CaptureTextRequest",
    "DuplicatesResponse",
    "TranscribeResponse",
]
