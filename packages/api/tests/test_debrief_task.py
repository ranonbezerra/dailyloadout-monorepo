"""Tests for the async debrief extraction Taskiq task."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from httpx import AsyncClient

from tests.test_mission import _create_library_entry, _start_mission


async def _setup_ended_mission(
    client: AsyncClient,
    headers: dict[str, str],
    seed_platforms: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Create a library entry, start a mission, submit a debrief, return both."""
    entry = await _create_library_entry(client, headers, seed_platforms)
    mission = await _start_mission(client, headers, entry["public_id"])

    resp = await client.patch(
        f"/v1/missions/{mission['public_id']}/debrief",
        json={"debrief_text": "Found the Mantis Claw. Heading to City of Tears."},
        headers=headers,
    )
    assert resp.status_code == 200
    mission = resp.json()
    assert mission["extracted_state"] is None  # async — not yet extracted

    return entry, mission


class TestDebriefExtractionTask:
    async def test_task_extracts_and_persists_state(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Calling the task function directly extracts state and saves it."""
        await _setup_ended_mission(async_client, auth_headers, seed_platforms)

        from tests.conftest import _TestSessionFactory

        # Patch the session factory at the module where it's imported from,
        # so the lazy import inside the task function picks up the test DB.
        with patch(
            "dailyloadout.infrastructure.db.session.async_session_factory",
            _TestSessionFactory,
        ):
            from dailyloadout.infrastructure.tasks.debrief_extraction import (
                extract_debrief_state_task,
            )

            # Call the underlying coroutine directly (not via .kiq()).
            await extract_debrief_state_task.original_func(
                mission_id=1,
                game_title="Hollow Knight",
                debrief_text="Found the Mantis Claw. Heading to City of Tears.",
            )

        # Verify the extracted state is persisted.
        from dailyloadout.infrastructure.db.models import Mission

        async with _TestSessionFactory() as session:
            row = await session.get(Mission, 1)
            assert row is not None
            assert row.extracted_state is not None
            state = row.extracted_state
            assert state.get("next_action") is not None

    async def test_task_updates_library_entry_next_action(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Task updates the denormalized mission_next_action on library entry."""
        await _setup_ended_mission(async_client, auth_headers, seed_platforms)

        from tests.conftest import _TestSessionFactory

        with patch(
            "dailyloadout.infrastructure.db.session.async_session_factory",
            _TestSessionFactory,
        ):
            from dailyloadout.infrastructure.tasks.debrief_extraction import (
                extract_debrief_state_task,
            )

            await extract_debrief_state_task.original_func(
                mission_id=1,
                game_title="Hollow Knight",
                debrief_text="Found the Mantis Claw. Heading to City of Tears.",
            )

        # Check library entry's mission_next_action is updated.
        resp = await async_client.get("/v1/library", headers=auth_headers)
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["platforms"][0]["mission_next_action"] is not None
