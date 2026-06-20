"""Tests for the mission endpoints (v1/missions)."""

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


async def _start_mission(
    client: AsyncClient,
    headers: dict[str, str],
    entry_public_id: str,
    briefing_text: str | None = None,
) -> dict[str, Any]:
    """Start a mission and return the parsed response."""
    body: dict[str, Any] = {"library_entry_public_id": entry_public_id}
    if briefing_text is not None:
        body["briefing_text"] = briefing_text
    resp = await client.post(
        "/v1/missions",
        json=body,
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _preview_briefing(
    client: AsyncClient,
    headers: dict[str, str],
    entry_public_id: str,
    position_override: str | None = None,
) -> dict[str, Any]:
    """Preview a briefing without starting a mission."""
    body: dict[str, Any] = {"library_entry_public_id": entry_public_id}
    if position_override is not None:
        body["position_override"] = position_override
    resp = await client.post(
        "/v1/missions/preview-briefing",
        json=body,
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


# =====================================================================
# Test: Start mission
# =====================================================================


class TestStartMission:
    async def test_start_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        mission = await _start_mission(async_client, auth_headers, entry["public_id"])

        assert mission["library_entry"]["public_id"] == entry["public_id"]
        assert mission["ended_at"] is None
        assert mission["ended_via"] is None
        assert mission["started_at"] is not None
        # First mission — no prior debriefs, but briefing should still be generated.
        assert mission["briefing_text"] is not None

    async def test_start_first_mission_briefing(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """First mission should get a welcome-style briefing."""
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        mission = await _start_mission(async_client, auth_headers, entry["public_id"])

        briefing = mission["briefing_text"].lower()
        assert "first mission" in briefing or "welcome" in briefing

    async def test_start_conflict_active_mission(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Cannot start a second mission while one is active."""
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        await _start_mission(async_client, auth_headers, entry["public_id"])

        resp = await async_client.post(
            "/v1/missions",
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
            "/v1/missions",
            json={"library_entry_public_id": str(uuid4())},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_start_unauthorized(
        self,
        async_client: AsyncClient,
    ) -> None:
        resp = await async_client.post(
            "/v1/missions",
            json={"library_entry_public_id": str(uuid4())},
        )
        assert resp.status_code == 401


# =====================================================================
# Test: Get active mission
# =====================================================================


class TestGetActiveMission:
    async def test_no_active_mission(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        resp = await async_client.get("/v1/missions/active", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() is None

    async def test_has_active_mission(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        started = await _start_mission(async_client, auth_headers, entry["public_id"])

        resp = await async_client.get("/v1/missions/active", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data is not None
        assert data["public_id"] == started["public_id"]


# =====================================================================
# Test: Submit debrief
# =====================================================================


class TestSubmitDebrief:
    async def test_debrief_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        mission = await _start_mission(async_client, auth_headers, entry["public_id"])

        resp = await async_client.patch(
            f"/v1/missions/{mission['public_id']}/debrief",
            json={"debrief_text": "Beat the Mantis Lords. Heading to Greenpath."},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["debrief_text"] == "Beat the Mantis Lords. Heading to Greenpath."
        assert data["ended_via"] == "debrief_completed"
        assert data["ended_at"] is not None
        # Extraction is now async — extracted_state is null in the immediate response.
        assert data["extracted_state"] is None

    async def test_debrief_extraction_via_sync_fallback(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Sync fallback extracts state when a preview is requested."""
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        mission = await _start_mission(async_client, auth_headers, entry["public_id"])

        await async_client.patch(
            f"/v1/missions/{mission['public_id']}/debrief",
            json={"debrief_text": "Found the Mantis Claw. Need to go to City of Tears next."},
            headers=auth_headers,
        )

        # Preview briefing — sync fallback should extract the first debrief.
        preview = await _preview_briefing(async_client, auth_headers, entry["public_id"])
        assert preview["last_session_context"] is not None
        assert preview["last_session_context"]["next_action"] is not None

        # Library entry should also be updated via fallback.
        resp = await async_client.get("/v1/library", headers=auth_headers)
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["mission_next_action"] is not None

    async def test_debrief_already_ended(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        mission = await _start_mission(async_client, auth_headers, entry["public_id"])

        # End the mission first.
        await async_client.post(
            f"/v1/missions/{mission['public_id']}/end",
            json={"ended_via": "paused_app"},
            headers=auth_headers,
        )

        # Try debrief on ended mission.
        resp = await async_client.patch(
            f"/v1/missions/{mission['public_id']}/debrief",
            json={"debrief_text": "Some text here."},
            headers=auth_headers,
        )
        assert resp.status_code == 409

    async def test_debrief_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        resp = await async_client.patch(
            f"/v1/missions/{uuid4()}/debrief",
            json={"debrief_text": "Some text here."},
            headers=auth_headers,
        )
        assert resp.status_code == 404


# =====================================================================
# Test: Retroactive debrief (unregistered session)
# =====================================================================


class TestRetroactiveDebrief:
    async def test_retroactive_creates_mission_and_updates_preview(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Submitting a retroactive debrief creates a pre-ended mission
        and returns an updated preview with extracted context."""
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)

        resp = await async_client.post(
            "/v1/missions/retroactive-debrief",
            json={
                "library_entry_public_id": entry["public_id"],
                "debrief_text": "Played for 3 hours. Beat Soul Master and got to City of Tears.",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        preview = resp.json()
        assert preview["last_session_context"] is not None
        assert preview["briefing_text"] is not None

        # Verify the retroactive mission exists in the timeline.
        resp = await async_client.get("/v1/missions", headers=auth_headers)
        data = resp.json()
        assert data["total"] == 1
        retro = data["items"][0]
        assert retro["mission_type"] == "retroactive"
        assert retro["ended_via"] == "retroactive"

    async def test_retroactive_entry_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        resp = await async_client.post(
            "/v1/missions/retroactive-debrief",
            json={
                "library_entry_public_id": str(uuid4()),
                "debrief_text": "Some session notes.",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_retroactive_does_not_block_active_mission(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Retroactive debrief should work even with an active mission
        for a different game, since it creates a pre-ended mission."""
        entry1 = await _create_library_entry(async_client, auth_headers, seed_platforms)
        entry2 = await _create_library_entry(
            async_client, auth_headers, seed_platforms, game_text="I bought Celeste"
        )

        # Start a regular mission for entry1.
        await _start_mission(async_client, auth_headers, entry1["public_id"])

        # Submit retroactive debrief for entry2 — should succeed
        # because the retroactive mission is pre-ended.
        resp = await async_client.post(
            "/v1/missions/retroactive-debrief",
            json={
                "library_entry_public_id": entry2["public_id"],
                "debrief_text": "Cleared chapter 3 of Celeste.",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200


# =====================================================================
# Test: End mission (no debrief)
# =====================================================================


class TestEndMission:
    async def test_end_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        mission = await _start_mission(async_client, auth_headers, entry["public_id"])

        resp = await async_client.post(
            f"/v1/missions/{mission['public_id']}/end",
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
        mission = await _start_mission(async_client, auth_headers, entry["public_id"])

        await async_client.post(
            f"/v1/missions/{mission['public_id']}/end",
            json={"ended_via": "paused_app"},
            headers=auth_headers,
        )

        resp = await async_client.post(
            f"/v1/missions/{mission['public_id']}/end",
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
        """After ending a mission, a new one can be started."""
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        mission = await _start_mission(async_client, auth_headers, entry["public_id"])

        await async_client.post(
            f"/v1/missions/{mission['public_id']}/end",
            json={"ended_via": "paused_app"},
            headers=auth_headers,
        )

        # Should be able to start a new mission now.
        second = await _start_mission(async_client, auth_headers, entry["public_id"])
        assert second["public_id"] != mission["public_id"]


# =====================================================================
# Test: Briefing with context from debriefs
# =====================================================================


class TestBriefingWithContext:
    async def test_second_mission_uses_debrief_context(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """The second mission's briefing should reference the first debrief."""
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)

        # First mission with debrief.
        m1 = await _start_mission(async_client, auth_headers, entry["public_id"])
        await async_client.patch(
            f"/v1/missions/{m1['public_id']}/debrief",
            json={"debrief_text": "Beat the Mantis Lords. Heading to Greenpath next."},
            headers=auth_headers,
        )

        # Second mission should have a briefing referencing the debrief.
        m2 = await _start_mission(async_client, auth_headers, entry["public_id"])
        assert m2["briefing_text"] is not None
        # The dummy LLM uses debrief data — should reference it.
        briefing = m2["briefing_text"].lower()
        assert "previously" in briefing or "hollow knight" in briefing


# =====================================================================
# Test: Regenerate briefing
# =====================================================================


class TestRegenerateBriefing:
    async def test_regenerate_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        mission = await _start_mission(async_client, auth_headers, entry["public_id"])

        resp = await async_client.post(
            f"/v1/missions/{mission['public_id']}/briefing/regenerate",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["briefing_text"] is not None

    async def test_regenerate_ended_mission(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        mission = await _start_mission(async_client, auth_headers, entry["public_id"])

        await async_client.post(
            f"/v1/missions/{mission['public_id']}/end",
            json={"ended_via": "paused_app"},
            headers=auth_headers,
        )

        resp = await async_client.post(
            f"/v1/missions/{mission['public_id']}/briefing/regenerate",
            headers=auth_headers,
        )
        assert resp.status_code == 409


# =====================================================================
# Test: List missions
# =====================================================================


class TestListMissions:
    async def test_list_empty(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        resp = await async_client.get("/v1/missions", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_with_missions(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)

        # Start and end two missions.
        m1 = await _start_mission(async_client, auth_headers, entry["public_id"])
        await async_client.post(
            f"/v1/missions/{m1['public_id']}/end",
            json={"ended_via": "paused_app"},
            headers=auth_headers,
        )

        m2 = await _start_mission(async_client, auth_headers, entry["public_id"])
        await async_client.post(
            f"/v1/missions/{m2['public_id']}/end",
            json={"ended_via": "paused_app"},
            headers=auth_headers,
        )

        resp = await async_client.get("/v1/missions", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2


# =====================================================================
# Test: Get single mission
# =====================================================================


class TestGetMission:
    async def test_get_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        mission = await _start_mission(async_client, auth_headers, entry["public_id"])

        resp = await async_client.get(f"/v1/missions/{mission['public_id']}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["public_id"] == mission["public_id"]

    async def test_get_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        resp = await async_client.get(f"/v1/missions/{uuid4()}", headers=auth_headers)
        assert resp.status_code == 404


# =====================================================================
# Test: Anti-hallucination validator
# =====================================================================


class TestAntiHallucination:
    def test_valid_briefing(self) -> None:
        from dailyloadout.core.mission.anti_hallucination import validate_briefing

        result = validate_briefing(
            briefing_text="You were at Greenpath fighting the Mantis Lords.",
            context_text="Location: Greenpath. Next action: fight the Mantis Lords.",
        )
        assert not result.is_suspicious
        assert result.overlap_ratio >= 0.70

    def test_suspicious_briefing(self) -> None:
        from dailyloadout.core.mission.anti_hallucination import validate_briefing

        result = validate_briefing(
            briefing_text="You were at Harkenburg Castle fighting King Aldric the Terrible.",
            context_text="Location: Greenpath. Next action: find the Mothwing Cloak.",
        )
        assert result.is_suspicious
        assert result.overlap_ratio < 0.70
        assert len(result.missing_tokens) > 0

    def test_empty_briefing(self) -> None:
        from dailyloadout.core.mission.anti_hallucination import validate_briefing

        result = validate_briefing(
            briefing_text="just some lowercase text without proper nouns",
            context_text="any context",
        )
        assert not result.is_suspicious
        assert result.overlap_ratio == 1.0


# =====================================================================
# Test: Actionable briefing (suggestions + position override)
# =====================================================================


class TestActionableBriefing:
    async def test_preview_returns_last_session_context(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Preview for a second mission should return the first's extracted state."""
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)

        # First preview: no prior sessions.
        p1 = await _preview_briefing(async_client, auth_headers, entry["public_id"])
        assert p1["last_session_context"] is None

        # First mission: start, debrief, end.
        m1 = await _start_mission(async_client, auth_headers, entry["public_id"])
        await async_client.patch(
            f"/v1/missions/{m1['public_id']}/debrief",
            json={"debrief_text": "Beat the Mantis Lords, heading to City of Tears"},
            headers=auth_headers,
        )

        # Second preview: should carry context from the first.
        p2 = await _preview_briefing(async_client, auth_headers, entry["public_id"])
        assert p2["last_session_context"] is not None
        assert p2["last_session_context"]["next_action"] is not None

    async def test_briefing_contains_suggestions(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Briefing should contain actionable 'What you could do' section."""
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)

        # First mission with debrief.
        m1 = await _start_mission(async_client, auth_headers, entry["public_id"])
        await async_client.patch(
            f"/v1/missions/{m1['public_id']}/debrief",
            json={"debrief_text": "Explored the Forgotten Crossroads"},
            headers=auth_headers,
        )

        # Second mission should have suggestions.
        m2 = await _start_mission(async_client, auth_headers, entry["public_id"])
        assert m2["briefing_text"] is not None
        assert "What you could do" in m2["briefing_text"]

    async def test_regenerate_with_position_override(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Regenerate with position override should include the correction."""
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)

        # First mission with debrief.
        m1 = await _start_mission(async_client, auth_headers, entry["public_id"])
        await async_client.patch(
            f"/v1/missions/{m1['public_id']}/debrief",
            json={"debrief_text": "Reached Greenpath after beating Gruz Mother"},
            headers=auth_headers,
        )

        # Second mission.
        m2 = await _start_mission(async_client, auth_headers, entry["public_id"])

        # Regenerate with correction.
        resp = await async_client.post(
            f"/v1/missions/{m2['public_id']}/briefing/regenerate",
            json={"current_position": "Actually at City of Tears now"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "City of Tears" in data["briefing_text"]

    async def test_regenerate_without_body_still_works(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Regenerate without a body (backwards compatible) should work."""
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        m = await _start_mission(async_client, auth_headers, entry["public_id"])

        resp = await async_client.post(
            f"/v1/missions/{m['public_id']}/briefing/regenerate",
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
        p = await _preview_briefing(async_client, auth_headers, entry["public_id"])
        assert p["last_session_context"] is None


# =====================================================================
# Test: Auto-clamp (repository + worker)
# =====================================================================


class TestAutoClamp:
    async def test_stale_mission_gets_clamped(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """A mission older than max_hours should be auto-clamped."""
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        mission = await _start_mission(async_client, auth_headers, entry["public_id"])

        # Backdate started_at so the mission looks stale.
        from dailyloadout.infrastructure.db.models import Mission
        from tests.conftest import _TestSessionFactory

        async with _TestSessionFactory() as session:
            m = await session.get(Mission, 1)
            assert m is not None
            m.started_at = datetime.now(UTC) - timedelta(hours=25)
            await session.commit()

        # Run the auto-clamp worker.
        from dailyloadout.infrastructure.db.repositories.mission import MissionRepository
        from dailyloadout.workers.mission_auto_clamp import auto_clamp_stale_missions

        async with _TestSessionFactory() as session:
            repo = MissionRepository(session)
            clamped = await auto_clamp_stale_missions(repo, max_hours=24)
            await session.commit()

        assert clamped == 1

        # Verify via API: mission is now ended.
        resp = await async_client.get(f"/v1/missions/{mission['public_id']}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["ended_via"] == "auto_clamp"
        assert data["ended_at"] is not None

    async def test_fresh_mission_not_clamped(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """A recently started mission should not be auto-clamped."""
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        await _start_mission(async_client, auth_headers, entry["public_id"])

        from dailyloadout.infrastructure.db.repositories.mission import MissionRepository
        from dailyloadout.workers.mission_auto_clamp import auto_clamp_stale_missions
        from tests.conftest import _TestSessionFactory

        async with _TestSessionFactory() as session:
            repo = MissionRepository(session)
            clamped = await auto_clamp_stale_missions(repo, max_hours=24)
            await session.commit()

        assert clamped == 0

        # Mission should still be active.
        resp = await async_client.get("/v1/missions/active", headers=auth_headers)
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
        mission = await _start_mission(async_client, auth_headers, entry["public_id"])

        from dailyloadout.infrastructure.db.models import Mission
        from tests.conftest import _TestSessionFactory

        stale_start = datetime.now(UTC) - timedelta(hours=30)
        async with _TestSessionFactory() as session:
            m = await session.get(Mission, 1)
            assert m is not None
            m.started_at = stale_start
            await session.commit()

        from dailyloadout.infrastructure.db.repositories.mission import MissionRepository
        from dailyloadout.workers.mission_auto_clamp import auto_clamp_stale_missions

        async with _TestSessionFactory() as session:
            repo = MissionRepository(session)
            await auto_clamp_stale_missions(repo, max_hours=24)
            await session.commit()

        resp = await async_client.get(f"/v1/missions/{mission['public_id']}", headers=auth_headers)
        data = resp.json()
        ended_at = datetime.fromisoformat(data["ended_at"])
        expected = stale_start + timedelta(hours=24)
        # Strip tzinfo for comparison — SQLite loses timezone.
        ended_naive = ended_at.replace(tzinfo=None)
        expected_naive = expected.replace(tzinfo=None)
        assert abs((ended_naive - expected_naive).total_seconds()) < 2

    async def test_can_start_new_mission_after_clamp(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """After auto-clamp, the user should be able to start a new mission."""
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)
        await _start_mission(async_client, auth_headers, entry["public_id"])

        from dailyloadout.infrastructure.db.models import Mission
        from tests.conftest import _TestSessionFactory

        async with _TestSessionFactory() as session:
            m = await session.get(Mission, 1)
            assert m is not None
            m.started_at = datetime.now(UTC) - timedelta(hours=25)
            await session.commit()

        from dailyloadout.infrastructure.db.repositories.mission import MissionRepository
        from dailyloadout.workers.mission_auto_clamp import auto_clamp_stale_missions

        async with _TestSessionFactory() as session:
            repo = MissionRepository(session)
            await auto_clamp_stale_missions(repo, max_hours=24)
            await session.commit()

        # Should be able to start a new mission now.
        new_mission = await _start_mission(async_client, auth_headers, entry["public_id"])
        assert new_mission["ended_at"] is None

    async def test_multiple_stale_missions_all_clamped(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Multiple stale missions from different users get clamped in one sweep."""
        entry = await _create_library_entry(async_client, auth_headers, seed_platforms)

        # Start and manually end first, then start a second — both will be backdated.
        m1 = await _start_mission(async_client, auth_headers, entry["public_id"])
        await async_client.post(
            f"/v1/missions/{m1['public_id']}/end",
            json={"ended_via": "paused_app"},
            headers=auth_headers,
        )
        m2 = await _start_mission(async_client, auth_headers, entry["public_id"])

        # Register a second user with their own stale mission.
        resp = await async_client.post(
            "/v1/auth/register",
            json={
                "email": "player2@example.com",
                "password": "strongpassword123",
                "display_name": "Player Two",
            },
        )
        headers2 = {"Authorization": f"Bearer {resp.json()['access_token']}"}
        entry2 = await _create_library_entry(
            async_client, headers2, seed_platforms, game_text="I bought Celeste"
        )
        m3 = await _start_mission(async_client, headers2, entry2["public_id"])

        # Backdate only active missions (m2 and m3).
        from dailyloadout.infrastructure.db.models import Mission
        from tests.conftest import _TestSessionFactory

        async with _TestSessionFactory() as session:
            for mid in (m2, m3):
                row = await session.get(Mission, 2 if mid is m2 else 3)
                assert row is not None
                row.started_at = datetime.now(UTC) - timedelta(hours=25)
            await session.commit()

        from dailyloadout.infrastructure.db.repositories.mission import MissionRepository
        from dailyloadout.workers.mission_auto_clamp import auto_clamp_stale_missions

        async with _TestSessionFactory() as session:
            repo = MissionRepository(session)
            clamped = await auto_clamp_stale_missions(repo, max_hours=24)
            await session.commit()

        assert clamped == 2
