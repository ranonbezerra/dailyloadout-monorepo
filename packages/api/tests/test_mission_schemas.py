"""Unit tests for the mission schemas' typed ExtractedState (no more dict[str, Any])."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from dailyloadout.core.library.schemas import (
    GameResponse,
    LibraryEntryResponse,
    PlatformResponse,
)
from dailyloadout.core.mission.schemas import (
    BriefingPreviewResponse,
    ExtractedState,
    MissionResponse,
)


def _library_entry() -> LibraryEntryResponse:
    return LibraryEntryResponse(
        public_id=uuid4(),
        status="playing",
        game=GameResponse(
            public_id=uuid4(),
            slug="hk",
            title="Hollow Knight",
            metadata_source="user",
            created_at=datetime.now(UTC),
        ),
        platform=PlatformResponse(id=1, slug="pc", label="PC", family="pc"),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def test_extracted_state_defaults_are_optional() -> None:
    state = ExtractedState()
    assert state.location is None
    assert state.next_action is None
    assert state.level is None
    assert state.current_quest is None


def test_extracted_state_ignores_unknown_keys() -> None:
    # Backward compatibility: older JSONB rows may carry extra keys.
    state = ExtractedState.model_validate(
        {"next_action": "Reach Greenpath", "legacy_field": "ignored"}
    )
    assert state.next_action == "Reach Greenpath"
    assert not hasattr(state, "legacy_field")


def test_mission_response_coerces_dict_extracted_state() -> None:
    raw = {
        "public_id": uuid4(),
        "library_entry": _library_entry(),
        "extracted_state": {"location": "City of Tears", "next_action": "Find the elevator"},
        "started_at": datetime.now(UTC),
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    resp = MissionResponse.model_validate(raw)
    assert isinstance(resp.extracted_state, ExtractedState)
    assert resp.extracted_state.location == "City of Tears"
    # Serializes back to a dict shape clients already expect.
    assert resp.model_dump()["extracted_state"]["next_action"] == "Find the elevator"


def test_preview_response_typed_last_session_context() -> None:
    raw = {
        "library_entry": _library_entry(),
        "briefing_text": "Welcome back.",
        "last_session_context": {"level": "12"},
    }
    resp = BriefingPreviewResponse.model_validate(raw)
    assert isinstance(resp.last_session_context, ExtractedState)
    assert resp.last_session_context.level == "12"
