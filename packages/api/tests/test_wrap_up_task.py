"""Tests for the async wrap_up extraction Taskiq task."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from httpx import AsyncClient

from tests.test_play_session import _create_library_entry, _start_play_session


async def _setup_ended_play_session(
    client: AsyncClient,
    headers: dict[str, str],
    seed_platforms: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Create a library entry, start a play_session, submit a wrap_up, return both."""
    entry = await _create_library_entry(client, headers, seed_platforms)
    play_session = await _start_play_session(client, headers, entry["public_id"])

    resp = await client.patch(
        f"/v1/play-sessions/{play_session['public_id']}/wrap-up",
        json={"wrap_up_text": "Found the Mantis Claw. Heading to City of Tears."},
        headers=headers,
    )
    assert resp.status_code == 200
    play_session = resp.json()
    assert play_session["extracted_state"] is None  # async — not yet extracted

    return entry, play_session


class TestWrapUpExtractionTask:
    async def test_task_extracts_and_persists_state(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Calling the task function directly extracts state and saves it."""
        await _setup_ended_play_session(async_client, auth_headers, seed_platforms)

        from tests.conftest import _TestSessionFactory

        # Patch the session factory at the module where it's imported from,
        # so the lazy import inside the task function picks up the test DB.
        with patch(
            "slate.infrastructure.db.session.async_session_factory",
            _TestSessionFactory,
        ):
            from slate.infrastructure.tasks.wrap_up_extraction import (
                extract_wrap_up_state_task,
            )

            # Call the underlying coroutine directly (not via .kiq()).
            await extract_wrap_up_state_task.original_func(
                play_session_id=1,
                game_title="Hollow Knight",
                wrap_up_text="Found the Mantis Claw. Heading to City of Tears.",
                user_id=1,
            )

        # Verify the extracted state is persisted.
        from slate.infrastructure.db.models import PlaySession

        async with _TestSessionFactory() as session:
            row = await session.get(PlaySession, 1)
            assert row is not None
            assert row.extracted_state is not None
            state = row.extracted_state
            assert state.get("next_action") is not None

    async def test_task_refuses_cross_user_write(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """A forged message with a non-owner user_id must not write extracted state."""
        await _setup_ended_play_session(async_client, auth_headers, seed_platforms)

        from tests.conftest import _TestSessionFactory

        with patch(
            "slate.infrastructure.db.session.async_session_factory",
            _TestSessionFactory,
        ):
            from slate.infrastructure.tasks.wrap_up_extraction import (
                extract_wrap_up_state_task,
            )

            await extract_wrap_up_state_task.original_func(
                play_session_id=1,
                game_title="Hollow Knight",
                wrap_up_text="cross-user attempt",
                user_id=999,  # not the owner
            )

        from slate.infrastructure.db.models import PlaySession

        async with _TestSessionFactory() as session:
            row = await session.get(PlaySession, 1)
            assert row is not None
            assert row.extracted_state is None  # ownership guard blocked the write

    async def test_task_updates_library_entry_next_action(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Task updates the denormalized play_session_next_action on library entry."""
        await _setup_ended_play_session(async_client, auth_headers, seed_platforms)

        from tests.conftest import _TestSessionFactory

        with patch(
            "slate.infrastructure.db.session.async_session_factory",
            _TestSessionFactory,
        ):
            from slate.infrastructure.tasks.wrap_up_extraction import (
                extract_wrap_up_state_task,
            )

            await extract_wrap_up_state_task.original_func(
                play_session_id=1,
                game_title="Hollow Knight",
                wrap_up_text="Found the Mantis Claw. Heading to City of Tears.",
                user_id=1,
            )

        # Check library entry's play_session_next_action is updated.
        resp = await async_client.get("/v1/library", headers=auth_headers)
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["platforms"][0]["play_session_next_action"] is not None
