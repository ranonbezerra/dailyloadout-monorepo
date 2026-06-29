"""Tests for the play_session endpoints (v1/play_sessions)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from httpx import AsyncClient

# =====================================================================
# Helpers
# =====================================================================


async def _create_library_entry(
    client: AsyncClient,
    headers: dict[str, str],
    seed_platforms: list[dict[str, Any]],
    game_text: str = "I bought Hollow Knight",
) -> dict[str, Any]:
    """Submit a capture, confirm the candidate, and return the library entry."""
    resp = await client.post(
        "/v1/captures/text",
        json={"raw_text": game_text},
        headers=headers,
    )
    assert resp.status_code == 201
    capture = resp.json()

    candidate = capture["candidates"][0]
    platform_id = seed_platforms[0]["id"]

    resp = await client.post(
        f"/v1/captures/{capture['public_id']}/candidates/{candidate['public_id']}/confirm",
        json={"platform_id": platform_id, "status": "playing"},
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


async def _start_play_session(
    client: AsyncClient,
    headers: dict[str, str],
    entry_public_id: str,
    recap_text: str | None = None,
) -> dict[str, Any]:
    """Start a play_session and return the parsed response."""
    body: dict[str, Any] = {"library_entry_public_id": entry_public_id}
    if recap_text is not None:
        body["recap_text"] = recap_text
    resp = await client.post(
        "/v1/play-sessions",
        json=body,
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _preview_recap(
    client: AsyncClient,
    headers: dict[str, str],
    entry_public_id: str,
    position_override: str | None = None,
) -> dict[str, Any]:
    """Preview a recap without starting a play_session."""
    body: dict[str, Any] = {"library_entry_public_id": entry_public_id}
    if position_override is not None:
        body["position_override"] = position_override
    resp = await client.post(
        "/v1/play-sessions/preview-recap",
        json=body,
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


# =====================================================================
# Test: Start play_session
# =====================================================================


class TestStartPlaySession:
    async def test_start_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        play_session = await _start_play_session(async_client, auth_headers, entry["public_id"])

        assert play_session["library_entry"]["public_id"] == entry["public_id"]
        assert play_session["ended_at"] is None
        assert play_session["ended_via"] is None
        assert play_session["started_at"] is not None
        # First play_session — no prior wrap_ups, but recap should still be generated.
        assert play_session["recap_text"] is not None

    async def test_start_skip_recap(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """The 'just play' path starts with no recap and generates none."""
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        resp = await async_client.post(
            "/v1/play-sessions",
            json={"library_entry_public_id": entry["public_id"], "skip_recap": True},
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        play_session = resp.json()
        assert play_session["ended_at"] is None
        assert play_session["recap_text"] is None  # no recap generated

    async def test_start_first_play_session_recap(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """First play_session should get a welcome-style recap."""
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        play_session = await _start_play_session(async_client, auth_headers, entry["public_id"])

        recap = play_session["recap_text"].lower()
        assert "first play_session" in recap or "welcome" in recap

    async def test_start_deep_mode_uses_agent(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Deep mode routes through the recap agent (dummy in testing)."""
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        resp = await async_client.post(
            "/v1/play-sessions",
            json={"library_entry_public_id": entry["public_id"], "mode": "deep"},
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        play_session = resp.json()
        # DummyRecapAgent returns a deterministic deep-research recap.
        assert "Previously on" in play_session["recap_text"]

    async def test_start_invalid_mode_rejected(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """An unknown recap mode fails request validation."""
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        resp = await async_client.post(
            "/v1/play-sessions",
            json={"library_entry_public_id": entry["public_id"], "mode": "turbo"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_start_conflict_active_play_session(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Cannot start a second play_session while one is active."""
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        await _start_play_session(async_client, auth_headers, entry["public_id"])

        resp = await async_client.post(
            "/v1/play-sessions",
            json={"library_entry_public_id": entry["public_id"]},
            headers=auth_headers,
        )
        assert resp.status_code == 409

    async def test_start_entry_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        resp = await async_client.post(
            "/v1/play-sessions",
            json={"library_entry_public_id": str(uuid4())},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_start_unauthorized(
        self,
        async_client: AsyncClient,
    ) -> None:
        resp = await async_client.post(
            "/v1/play-sessions",
            json={"library_entry_public_id": str(uuid4())},
        )
        assert resp.status_code == 401


# =====================================================================
# Test: Get active play_session
# =====================================================================


class TestGetActivePlaySession:
    async def test_no_active_play_session(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        resp = await async_client.get("/v1/play-sessions/active", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() is None

    async def test_has_active_play_session(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        started = await _start_play_session(async_client, auth_headers, entry["public_id"])

        resp = await async_client.get("/v1/play-sessions/active", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data is not None
        assert data["public_id"] == started["public_id"]


# =====================================================================
# Test: Submit wrap_up
# =====================================================================


class TestSubmitWrapUp:
    async def test_wrap_up_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        play_session = await _start_play_session(async_client, auth_headers, entry["public_id"])

        resp = await async_client.patch(
            f"/v1/play-sessions/{play_session['public_id']}/wrap-up",
            json={"wrap_up_text": "Beat the Mantis Lords. Heading to Greenpath."},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["wrap_up_text"] == "Beat the Mantis Lords. Heading to Greenpath."
        assert data["ended_via"] == "wrap_up_completed"
        assert data["ended_at"] is not None
        # Extraction is now async — extracted_state is null in the immediate response.
        assert data["extracted_state"] is None

    async def test_wrap_up_extraction_via_sync_fallback(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Sync fallback extracts state when a preview is requested."""
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        play_session = await _start_play_session(async_client, auth_headers, entry["public_id"])

        await async_client.patch(
            f"/v1/play-sessions/{play_session['public_id']}/wrap-up",
            json={"wrap_up_text": "Found the Mantis Claw. Need to go to City of Tears next."},
            headers=auth_headers,
        )

        # Preview recap — sync fallback should extract the first wrap_up.
        preview = await _preview_recap(async_client, auth_headers, entry["public_id"])
        assert preview["last_session_context"] is not None
        assert preview["last_session_context"]["next_action"] is not None

        # Library entry should also be updated via fallback.
        resp = await async_client.get("/v1/library", headers=auth_headers)
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["platforms"][0]["play_session_next_action"] is not None

    async def test_wrap_up_already_ended(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        play_session = await _start_play_session(async_client, auth_headers, entry["public_id"])

        # End the play_session first.
        await async_client.post(
            f"/v1/play-sessions/{play_session['public_id']}/end",
            json={"ended_via": "paused_app"},
            headers=auth_headers,
        )

        # Try wrap_up on ended play_session.
        resp = await async_client.patch(
            f"/v1/play-sessions/{play_session['public_id']}/wrap-up",
            json={"wrap_up_text": "Some text here."},
            headers=auth_headers,
        )
        assert resp.status_code == 409

    async def test_wrap_up_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        resp = await async_client.patch(
            f"/v1/play-sessions/{uuid4()}/wrap-up",
            json={"wrap_up_text": "Some text here."},
            headers=auth_headers,
        )
        assert resp.status_code == 404


# =====================================================================
# Test: Retroactive wrap_up (unregistered session)
# =====================================================================


class TestRetroactiveWrapUp:
    async def test_retroactive_creates_play_session_and_updates_preview(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Submitting a retroactive wrap_up creates a pre-ended play_session
        and returns an updated preview with extracted context."""
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)

        resp = await async_client.post(
            "/v1/play-sessions/retroactive-wrap-up",
            json={
                "library_entry_public_id": entry["public_id"],
                "wrap_up_text": "Played for 3 hours. Beat Soul Master and got to City of Tears.",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        preview = resp.json()
        assert preview["last_session_context"] is not None
        assert preview["recap_text"] is not None

        # Verify the retroactive play_session exists in the timeline.
        resp = await async_client.get("/v1/play-sessions", headers=auth_headers)
        data = resp.json()
        assert data["total"] == 1
        retro = data["items"][0]
        assert retro["play_session_type"] == "retroactive"
        assert retro["ended_via"] == "retroactive"

    async def test_retroactive_entry_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        resp = await async_client.post(
            "/v1/play-sessions/retroactive-wrap-up",
            json={
                "library_entry_public_id": str(uuid4()),
                "wrap_up_text": "Some session notes.",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_retroactive_does_not_block_active_play_session(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Retroactive wrap_up should work even with an active play_session
        for a different game, since it creates a pre-ended play_session."""
        entry1 = await _create_library_entry(async_client, auth_headers, seed_platforms)
        entry2 = await _create_library_entry(
            async_client, auth_headers, seed_platforms, game_text="I bought Celeste"
        )

        # Start a regular play_session for entry1.
        await _start_play_session(async_client, auth_headers, entry1["public_id"])

        # Submit retroactive wrap_up for entry2 — should succeed
        # because the retroactive play_session is pre-ended.
        resp = await async_client.post(
            "/v1/play-sessions/retroactive-wrap-up",
            json={
                "library_entry_public_id": entry2["public_id"],
                "wrap_up_text": "Cleared chapter 3 of Celeste.",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200


# =====================================================================
# Test: End play_session (no wrap_up)
# =====================================================================


class TestEndPlaySession:
    async def test_end_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        play_session = await _start_play_session(async_client, auth_headers, entry["public_id"])

        resp = await async_client.post(
            f"/v1/play-sessions/{play_session['public_id']}/end",
            json={"ended_via": "paused_app"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ended_via"] == "paused_app"
        assert data["ended_at"] is not None

    async def test_end_already_ended(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        play_session = await _start_play_session(async_client, auth_headers, entry["public_id"])

        await async_client.post(
            f"/v1/play-sessions/{play_session['public_id']}/end",
            json={"ended_via": "paused_app"},
            headers=auth_headers,
        )

        resp = await async_client.post(
            f"/v1/play-sessions/{play_session['public_id']}/end",
            json={"ended_via": "paused_app"},
            headers=auth_headers,
        )
        assert resp.status_code == 409

    async def test_can_start_new_after_end(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """After ending a play_session, a new one can be started."""
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        play_session = await _start_play_session(async_client, auth_headers, entry["public_id"])

        await async_client.post(
            f"/v1/play-sessions/{play_session['public_id']}/end",
            json={"ended_via": "paused_app"},
            headers=auth_headers,
        )

        # Should be able to start a new play_session now.
        second = await _start_play_session(async_client, auth_headers, entry["public_id"])
        assert second["public_id"] != play_session["public_id"]


# =====================================================================
# Test: Recap with context from wrap_ups
# =====================================================================


class TestRecapWithContext:
    async def test_second_play_session_uses_wrap_up_context(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """The second play_session's recap should reference the first wrap_up."""
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)

        # First play_session with wrap_up.
        m1 = await _start_play_session(async_client, auth_headers, entry["public_id"])
        await async_client.patch(
            f"/v1/play-sessions/{m1['public_id']}/wrap-up",
            json={"wrap_up_text": "Beat the Mantis Lords. Heading to Greenpath next."},
            headers=auth_headers,
        )

        # Second play_session should have a recap referencing the wrap_up.
        m2 = await _start_play_session(async_client, auth_headers, entry["public_id"])
        assert m2["recap_text"] is not None
        # The dummy LLM uses wrap_up data — should reference it.
        recap = m2["recap_text"].lower()
        assert "previously" in recap or "hollow knight" in recap


# =====================================================================
# Test: Regenerate recap
# =====================================================================


class TestRegenerateRecap:
    async def test_regenerate_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        play_session = await _start_play_session(async_client, auth_headers, entry["public_id"])

        resp = await async_client.post(
            f"/v1/play-sessions/{play_session['public_id']}/recap/regenerate",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["recap_text"] is not None

    async def test_regenerate_ended_play_session(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        play_session = await _start_play_session(async_client, auth_headers, entry["public_id"])

        await async_client.post(
            f"/v1/play-sessions/{play_session['public_id']}/end",
            json={"ended_via": "paused_app"},
            headers=auth_headers,
        )

        resp = await async_client.post(
            f"/v1/play-sessions/{play_session['public_id']}/recap/regenerate",
            headers=auth_headers,
        )
        assert resp.status_code == 409


# =====================================================================
# Test: List play_sessions
# =====================================================================


class TestListPlaySessions:
    async def test_list_empty(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        resp = await async_client.get("/v1/play-sessions", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_with_play_sessions(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)

        # Start and end two play_sessions.
        m1 = await _start_play_session(async_client, auth_headers, entry["public_id"])
        await async_client.post(
            f"/v1/play-sessions/{m1['public_id']}/end",
            json={"ended_via": "paused_app"},
            headers=auth_headers,
        )

        m2 = await _start_play_session(async_client, auth_headers, entry["public_id"])
        await async_client.post(
            f"/v1/play-sessions/{m2['public_id']}/end",
            json={"ended_via": "paused_app"},
            headers=auth_headers,
        )

        resp = await async_client.get("/v1/play-sessions", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2


# =====================================================================
# Test: Get single play_session
# =====================================================================


class TestGetPlaySession:
    async def test_get_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        play_session = await _start_play_session(async_client, auth_headers, entry["public_id"])

        resp = await async_client.get(
            f"/v1/play-sessions/{play_session['public_id']}", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["public_id"] == play_session["public_id"]

    async def test_get_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        resp = await async_client.get(f"/v1/play-sessions/{uuid4()}", headers=auth_headers)
        assert resp.status_code == 404


# =====================================================================
# Test: Anti-hallucination validator
# =====================================================================


class TestAntiHallucination:
    def test_valid_recap(self) -> None:
        from slate.core.play_session.anti_hallucination import validate_recap

        result = validate_recap(
            recap_text="You were at Greenpath fighting the Mantis Lords.",
            context_text="Location: Greenpath. Next action: fight the Mantis Lords.",
        )
        assert not result.is_suspicious
        assert result.overlap_ratio >= 0.40

    def test_suspicious_recap(self) -> None:
        from slate.core.play_session.anti_hallucination import validate_recap

        result = validate_recap(
            recap_text="You were at Harkenburg Castle fighting King Aldric the Terrible.",
            context_text="Location: Greenpath. Next action: find the Mothwing Cloak.",
        )
        assert result.is_suspicious
        assert result.overlap_ratio < 0.40
        assert len(result.missing_tokens) > 0

    def test_empty_recap(self) -> None:
        from slate.core.play_session.anti_hallucination import validate_recap

        result = validate_recap(
            recap_text="just some lowercase text without proper nouns",
            context_text="any context",
        )
        assert not result.is_suspicious
        assert result.overlap_ratio == 1.0

    def test_only_numbers_in_recap(self) -> None:
        """Numbers are interesting tokens; they must also appear in context."""
        from slate.core.play_session.anti_hallucination import validate_recap

        # Both numbers present in context -- should be fully grounded.
        # Note: "Level" is also an interesting token ([A-Z][a-z]{2,}).
        # The context uses "Level" capitalised so it appears in context_tokens.
        result = validate_recap(
            recap_text="Level 42 with 100 gold",
            context_text="Level 42 character with 100 gold coins.",
        )
        assert not result.is_suspicious
        # Recap tokens: {"Level", "42", "100"}.
        # Context tokens: {"Level", "42", "100"}.
        # All three grounded -> ratio = 1.0.
        assert result.overlap_ratio == 1.0
        assert result.missing_tokens == []

        # Now test where the numbers are NOT in context -- suspicious.
        result_bad = validate_recap(
            recap_text="Level 42 with 100 gold",
            context_text="the player is exploring a dungeon",
        )
        # Recap tokens: {"Level", "42", "100"}.
        # Context has no interesting tokens (all lowercase, no numbers).
        # overlap = 0/3 = 0.0 -> suspicious.
        assert result_bad.is_suspicious
        assert result_bad.overlap_ratio < 0.40

    def test_mixed_case_tokens(self) -> None:
        """Tokens in the recap should match context via case-insensitive comparison."""
        from slate.core.play_session.anti_hallucination import validate_recap

        # Recap has "Greenpath" (capitalised), context has "GREENPATH"
        # (all-caps).  The validator lowercases both sides for comparison,
        # so "greenpath" == "greenpath" should count as grounded.
        result = validate_recap(
            recap_text="Head to Greenpath and find the Cloak.",
            context_text="Next area: GREENPATH. Obtain the CLOAK there.",
        )
        assert not result.is_suspicious
        # Recap tokens: {"Greenpath", "Cloak", "Head"}
        # Context tokens: {"GREENPATH", "CLOAK", "Obtain", "Next"}
        # Case-insensitive: "greenpath" in context_lower, "cloak" in
        # context_lower, "head" NOT in context_lower.
        # Grounded = 2/3 = 0.667 >= 0.40
        assert result.overlap_ratio >= 0.40
        assert len(result.missing_tokens) <= 1

    def test_entirely_grounded_recap(self) -> None:
        """When every interesting token from the recap exists in context,
        overlap_ratio must be exactly 1.0."""
        from slate.core.play_session.anti_hallucination import validate_recap

        result = validate_recap(
            recap_text="Explore Greenpath and defeat the Mantis Lords.",
            context_text="Location: Greenpath. Boss: Mantis Lords. Action: Explore.",
        )
        assert not result.is_suspicious
        assert result.overlap_ratio == 1.0
        assert result.missing_tokens == []

    def test_single_token_recap(self) -> None:
        """Edge case: recap with exactly one interesting token."""
        from slate.core.play_session.anti_hallucination import validate_recap

        # Single token present in context -- ratio = 1/1 = 1.0
        result_present = validate_recap(
            recap_text="Greenpath",
            context_text="You are at Greenpath.",
        )
        assert not result_present.is_suspicious
        assert result_present.overlap_ratio == 1.0
        assert result_present.missing_tokens == []

        # Single token absent from context -- ratio = 0/1 = 0.0
        result_absent = validate_recap(
            recap_text="Greenpath",
            context_text="You are at the crossroads.",
        )
        assert result_absent.is_suspicious
        assert result_absent.overlap_ratio == 0.0
        assert result_absent.missing_tokens == ["Greenpath"]

    def test_context_contains_game_title_referenced_in_recap(self) -> None:
        """Recap referencing the game title should be grounded when
        the title appears in the context."""
        from slate.core.play_session.anti_hallucination import validate_recap

        result = validate_recap(
            recap_text=(
                "Welcome back to Hollow Knight. "
                "Last time you explored Greenpath and found the Mothwing Cloak."
            ),
            context_text=(
                "Game: Hollow Knight. "
                "Previous session: explored Greenpath, acquired Mothwing Cloak."
            ),
        )
        # Recap tokens: {"Welcome", "Hollow", "Knight", "Last",
        #                    "Greenpath", "Mothwing", "Cloak"}
        # Context tokens: {"Game", "Hollow", "Knight", "Previous",
        #                   "Greenpath", "Mothwing", "Cloak"}
        # Missing from context: {"Welcome", "Last"}
        # Grounded: 5/7 ~ 0.714 >= 0.40
        assert not result.is_suspicious
        assert result.overlap_ratio >= 0.40
        # "Hollow" and "Knight" from the title are grounded
        assert "Hollow" not in result.missing_tokens
        assert "Knight" not in result.missing_tokens


# =====================================================================
# Test: Actionable recap (suggestions + position override)
# =====================================================================


class TestActionableRecap:
    async def test_preview_returns_last_session_context(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Preview for a second play_session should return the first's extracted state."""
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)

        # First preview: no prior sessions.
        p1 = await _preview_recap(async_client, auth_headers, entry["public_id"])
        assert p1["last_session_context"] is None

        # First play_session: start, wrap_up, end.
        m1 = await _start_play_session(async_client, auth_headers, entry["public_id"])
        await async_client.patch(
            f"/v1/play-sessions/{m1['public_id']}/wrap-up",
            json={"wrap_up_text": "Beat the Mantis Lords, heading to City of Tears"},
            headers=auth_headers,
        )

        # Second preview: should carry context from the first.
        p2 = await _preview_recap(async_client, auth_headers, entry["public_id"])
        assert p2["last_session_context"] is not None
        assert p2["last_session_context"]["next_action"] is not None

    async def test_recap_contains_suggestions(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Recap should contain actionable 'What you could do' section."""
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)

        # First play_session with wrap_up.
        m1 = await _start_play_session(async_client, auth_headers, entry["public_id"])
        await async_client.patch(
            f"/v1/play-sessions/{m1['public_id']}/wrap-up",
            json={"wrap_up_text": "Explored the Forgotten Crossroads"},
            headers=auth_headers,
        )

        # Second play_session should have suggestions.
        m2 = await _start_play_session(async_client, auth_headers, entry["public_id"])
        assert m2["recap_text"] is not None
        assert "What you could do" in m2["recap_text"]

    async def test_regenerate_with_position_override(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Regenerate with position override should include the correction."""
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)

        # First play_session with wrap_up.
        m1 = await _start_play_session(async_client, auth_headers, entry["public_id"])
        await async_client.patch(
            f"/v1/play-sessions/{m1['public_id']}/wrap-up",
            json={"wrap_up_text": "Reached Greenpath after beating Gruz Mother"},
            headers=auth_headers,
        )

        # Second play_session.
        m2 = await _start_play_session(async_client, auth_headers, entry["public_id"])

        # Regenerate with correction.
        resp = await async_client.post(
            f"/v1/play-sessions/{m2['public_id']}/recap/regenerate",
            json={"current_position": "Actually at City of Tears now"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "City of Tears" in data["recap_text"]

    async def test_regenerate_without_body_still_works(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Regenerate without a body (backwards compatible) should work."""
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        m = await _start_play_session(async_client, auth_headers, entry["public_id"])

        resp = await async_client.post(
            f"/v1/play-sessions/{m['public_id']}/recap/regenerate",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    async def test_first_preview_no_confirmation_needed(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """First preview has no prior context — lastSessionContext should be null."""
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        p = await _preview_recap(async_client, auth_headers, entry["public_id"])
        assert p["last_session_context"] is None


# =====================================================================
# Test: Auto-clamp (repository + worker)
# =====================================================================


class TestAutoClamp:
    async def test_stale_play_session_gets_clamped(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """A play_session older than max_hours should be auto-clamped."""
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        play_session = await _start_play_session(async_client, auth_headers, entry["public_id"])

        # Backdate started_at so the play_session looks stale.
        from slate.infrastructure.db.models import PlaySession
        from tests.conftest import _TestSessionFactory

        async with _TestSessionFactory() as session:
            m = await session.get(PlaySession, 1)
            assert m is not None
            m.started_at = datetime.now(UTC) - timedelta(hours=25)
            await session.commit()

        # Run the auto-clamp worker.
        from slate.infrastructure.db.repositories.play_session import (
            PlaySessionRepository,
        )
        from slate.workers.play_session_auto_clamp import (
            auto_clamp_stale_play_sessions,
        )

        async with _TestSessionFactory() as session:
            repo = PlaySessionRepository(session)
            clamped = await auto_clamp_stale_play_sessions(repo, max_hours=24)
            await session.commit()

        assert clamped == 1

        # Verify via API: play_session is now ended.
        resp = await async_client.get(
            f"/v1/play-sessions/{play_session['public_id']}", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ended_via"] == "auto_clamp"
        assert data["ended_at"] is not None

    async def test_fresh_play_session_not_clamped(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """A recently started play_session should not be auto-clamped."""
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        await _start_play_session(async_client, auth_headers, entry["public_id"])

        from slate.infrastructure.db.repositories.play_session import (
            PlaySessionRepository,
        )
        from slate.workers.play_session_auto_clamp import (
            auto_clamp_stale_play_sessions,
        )
        from tests.conftest import _TestSessionFactory

        async with _TestSessionFactory() as session:
            repo = PlaySessionRepository(session)
            clamped = await auto_clamp_stale_play_sessions(repo, max_hours=24)
            await session.commit()

        assert clamped == 0

        # PlaySession should still be active.
        resp = await async_client.get("/v1/play-sessions/active", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() is not None
        assert resp.json()["ended_at"] is None

    async def test_clamp_sets_ended_at_to_start_plus_max(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """ended_at should be started_at + max_hours, not current time."""
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        play_session = await _start_play_session(async_client, auth_headers, entry["public_id"])

        from slate.infrastructure.db.models import PlaySession
        from tests.conftest import _TestSessionFactory

        stale_start = datetime.now(UTC) - timedelta(hours=30)
        async with _TestSessionFactory() as session:
            m = await session.get(PlaySession, 1)
            assert m is not None
            m.started_at = stale_start
            await session.commit()

        from slate.infrastructure.db.repositories.play_session import (
            PlaySessionRepository,
        )
        from slate.workers.play_session_auto_clamp import (
            auto_clamp_stale_play_sessions,
        )

        async with _TestSessionFactory() as session:
            repo = PlaySessionRepository(session)
            await auto_clamp_stale_play_sessions(repo, max_hours=24)
            await session.commit()

        resp = await async_client.get(
            f"/v1/play-sessions/{play_session['public_id']}", headers=auth_headers
        )
        data = resp.json()
        ended_at = datetime.fromisoformat(data["ended_at"])
        expected = stale_start + timedelta(hours=24)
        # Strip tzinfo for comparison — SQLite loses timezone.
        ended_naive = ended_at.replace(tzinfo=None)
        expected_naive = expected.replace(tzinfo=None)
        assert abs((ended_naive - expected_naive).total_seconds()) < 2

    async def test_can_start_new_play_session_after_clamp(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """After auto-clamp, the user should be able to start a new play_session."""
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        await _start_play_session(async_client, auth_headers, entry["public_id"])

        from slate.infrastructure.db.models import PlaySession
        from tests.conftest import _TestSessionFactory

        async with _TestSessionFactory() as session:
            m = await session.get(PlaySession, 1)
            assert m is not None
            m.started_at = datetime.now(UTC) - timedelta(hours=25)
            await session.commit()

        from slate.infrastructure.db.repositories.play_session import (
            PlaySessionRepository,
        )
        from slate.workers.play_session_auto_clamp import (
            auto_clamp_stale_play_sessions,
        )

        async with _TestSessionFactory() as session:
            repo = PlaySessionRepository(session)
            await auto_clamp_stale_play_sessions(repo, max_hours=24)
            await session.commit()

        # Should be able to start a new play_session now.
        new_play_session = await _start_play_session(
            async_client, auth_headers, entry["public_id"]
        )
        assert new_play_session["ended_at"] is None

    async def test_multiple_stale_play_sessions_all_clamped(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Multiple stale play_sessions from different users get clamped in one sweep."""
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)

        # Start and manually end first, then start a second — both will be backdated.
        m1 = await _start_play_session(async_client, auth_headers, entry["public_id"])
        await async_client.post(
            f"/v1/play-sessions/{m1['public_id']}/end",
            json={"ended_via": "paused_app"},
            headers=auth_headers,
        )
        m2 = await _start_play_session(async_client, auth_headers, entry["public_id"])

        # Register a second user with their own stale play_session.
        resp = await async_client.post(
            "/v1/auth/register",
            json={
                "email": "player2@example.com",
                "password": "StrongPass123",  # pragma: allowlist secret
                "display_name": "Player Two",
            },
        )
        headers2 = {"Authorization": f"Bearer {resp.json()['access_token']}"}
        entry2 = await _create_library_entry(
            async_client, headers2, seed_platforms, game_text="I bought Celeste"
        )
        m3 = await _start_play_session(async_client, headers2, entry2["public_id"])

        # Backdate only active play_sessions (m2 and m3).
        from slate.infrastructure.db.models import PlaySession
        from tests.conftest import _TestSessionFactory

        async with _TestSessionFactory() as session:
            for mid in (m2, m3):
                row = await session.get(PlaySession, 2 if mid is m2 else 3)
                assert row is not None
                row.started_at = datetime.now(UTC) - timedelta(hours=25)
            await session.commit()

        from slate.infrastructure.db.repositories.play_session import (
            PlaySessionRepository,
        )
        from slate.workers.play_session_auto_clamp import (
            auto_clamp_stale_play_sessions,
        )

        async with _TestSessionFactory() as session:
            repo = PlaySessionRepository(session)
            clamped = await auto_clamp_stale_play_sessions(repo, max_hours=24)
            await session.commit()

        assert clamped == 2


# =====================================================================
# Test: Deep recap mode (preview)
# =====================================================================


class TestDeepRecapPreview:
    async def test_preview_deep_mode_returns_recap(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Preview with mode='deep' routes through the agent (dummy in testing)."""
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        resp = await async_client.post(
            "/v1/play-sessions/preview-recap",
            json={"library_entry_public_id": entry["public_id"], "mode": "deep"},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["recap_text"]

    async def test_preview_invalid_mode_rejected(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        resp = await async_client.post(
            "/v1/play-sessions/preview-recap",
            json={"library_entry_public_id": entry["public_id"], "mode": "turbo"},
            headers=auth_headers,
        )
        assert resp.status_code == 422
