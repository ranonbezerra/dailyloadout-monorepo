"""Tests for composing + persisting a play_session wrap-up embedding (Epic 24)."""

from __future__ import annotations

from typing import cast

from slate.core.play_session.embedding import build_embedding_text, embed_session
from slate.infrastructure.db.repositories.play_session_embedding import (
    PlaySessionEmbeddingRepository,
)
from slate.infrastructure.embedding import DummyEmbeddingClient


class _RecordingRepo:
    """Stub PlaySessionEmbeddingRepository that records set_embedding calls (no DB)."""

    def __init__(self) -> None:
        self.calls: list[tuple[int, list[float], str]] = []

    async def set_embedding(
        self, play_session_id: int, embedding: list[float], model: str
    ) -> None:
        self.calls.append((play_session_id, embedding, model))


class _BrokenEmbeddingClient(DummyEmbeddingClient):
    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("embedding backend down")


class TestBuildEmbeddingText:
    def test_combines_raw_note_and_state(self) -> None:
        text = build_embedding_text(
            "Beat Margit, low on flasks",
            {"location": "Stormveil", "current_quest": None, "next_action": "rest", "level": "27"},
        )
        assert "Beat Margit" in text
        assert "location: Stormveil" in text
        assert "next_action: rest" in text
        assert "current_quest" not in text  # None fields are dropped

    def test_empty_inputs_yield_empty(self) -> None:
        assert build_embedding_text(None, None) == ""
        assert build_embedding_text("", {}) == ""


class TestEmbedSession:
    async def test_stores_vector_and_model(self) -> None:
        repo = _RecordingRepo()
        client = DummyEmbeddingClient(dimensions=64)
        stored = await embed_session(
            client,
            cast(PlaySessionEmbeddingRepository, repo),
            42,
            "beat Margit",
            {"location": "Stormveil"},
        )
        assert stored is True
        assert len(repo.calls) == 1
        ps_id, vector, model = repo.calls[0]
        assert ps_id == 42
        assert len(vector) == 64
        assert model == "dummy-embed"

    async def test_empty_text_skips_without_storing(self) -> None:
        repo = _RecordingRepo()
        stored = await embed_session(
            DummyEmbeddingClient(), cast(PlaySessionEmbeddingRepository, repo), 1, None, None
        )
        assert stored is False
        assert repo.calls == []

    async def test_backend_failure_is_swallowed(self) -> None:
        # A failing embedding backend must never break extraction.
        repo = _RecordingRepo()
        stored = await embed_session(
            _BrokenEmbeddingClient(), cast(PlaySessionEmbeddingRepository, repo), 1, "note", None
        )
        assert stored is False
        assert repo.calls == []
