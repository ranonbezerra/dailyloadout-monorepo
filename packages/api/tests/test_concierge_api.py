"""Tests for the Backlog Concierge SSE chat endpoint."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import select

from tests.conftest import _TestSessionFactory


async def _seed_entry_for(email: str) -> None:
    from dailyloadout.infrastructure.db.models import Game, LibraryEntry, Platform, User

    async with _TestSessionFactory() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one()
        game = Game(slug=f"g-{uuid4().hex[:6]}", title="Hollow Knight", metadata_source="user")
        session.add(game)
        await session.flush()
        platform = Platform(slug=f"p-{uuid4().hex[:6]}", label="PC", family="pc")
        session.add(platform)
        await session.flush()
        session.add(
            LibraryEntry(
                user_id=user.id, game_id=game.id, platform_id=platform.id, status="playing"
            )
        )
        await session.commit()


def _parse_sse(body: str) -> list[dict[str, Any]]:
    return [json.loads(line[5:].strip()) for line in body.splitlines() if line.startswith("data:")]


async def test_chat_requires_auth(async_client: AsyncClient) -> None:
    resp = await async_client.post("/v1/concierge/chat", json={"message": "hi"})
    assert resp.status_code == 401


async def test_chat_streams_guarded_reply(
    async_client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await _seed_entry_for("test@example.com")

    resp = await async_client.post(
        "/v1/concierge/chat",
        json={"message": "What should I play tonight?"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]

    events = _parse_sse(resp.text)
    tokens = "".join(e["token"] for e in events if "token" in e)
    done = [e for e in events if e.get("done")]
    recs = [e["recommendation"] for e in events if "recommendation" in e]

    assert "give this a go" in tokens
    assert "RECOMMEND" not in tokens  # marker withheld from the prose stream
    assert len(recs) == 1  # surfaced as a validated recommendation event instead
    assert len(done) == 1
    assert done[0]["thread_id"]  # server-issued thread id for the next turn


async def test_chat_reuses_thread_id(
    async_client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await _seed_entry_for("test@example.com")

    resp = await async_client.post(
        "/v1/concierge/chat",
        json={"message": "Anything good?", "thread_id": "my-thread-123"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    done = [e for e in _parse_sse(resp.text) if e.get("done")]
    assert done[0]["thread_id"] == "my-thread-123"


async def test_chat_rejects_empty_message(
    async_client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await async_client.post(
        "/v1/concierge/chat", json={"message": ""}, headers=auth_headers
    )
    assert resp.status_code == 422


async def test_chat_emits_error_event_on_failure(
    async_client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """An agent failure degrades to a clean SSE error event, not a 500."""
    from dailyloadout.deps.concierge import get_concierge_service
    from dailyloadout.main import app

    class _BoomService:
        async def reply(self, **_: object) -> str:
            raise RuntimeError("model unavailable")

    app.dependency_overrides[get_concierge_service] = _BoomService
    try:
        resp = await async_client.post(
            "/v1/concierge/chat",
            json={"message": "what should I play?"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        events = _parse_sse(resp.text)
        errors = [e for e in events if "error" in e]
        assert errors and "unavailable" in errors[0]["error"]
        assert any(e.get("done") for e in events)
    finally:
        app.dependency_overrides.pop(get_concierge_service, None)


async def test_chat_times_out_without_hanging(
    async_client: AsyncClient, auth_headers: dict[str, str], monkeypatch: Any
) -> None:
    """A stalled agent closes the stream with a timeout event, never hangs."""
    import asyncio

    from dailyloadout.api.v1 import concierge as concierge_module
    from dailyloadout.deps.concierge import get_concierge_service
    from dailyloadout.main import app

    # Make the ceiling tiny and the agent slower than it.
    monkeypatch.setattr(concierge_module, "_REPLY_TIMEOUT_SECONDS", 0.05)

    class _SlowService:
        async def reply_stream(self, **_: object) -> Any:
            await asyncio.sleep(5)
            yield {"token": "too late"}

    app.dependency_overrides[get_concierge_service] = _SlowService
    try:
        resp = await async_client.post(
            "/v1/concierge/chat",
            json={"message": "what should I play?"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        events = _parse_sse(resp.text)
        errors = [e for e in events if "error" in e]
        assert errors and "too long" in errors[0]["error"]
        assert any(e.get("done") for e in events)  # stream always closes
    finally:
        app.dependency_overrides.pop(get_concierge_service, None)
