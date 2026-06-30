"""Tests for the semantic LLM cache repository (Epic 27, SQLite/Python path)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from slate.infrastructure.db.repositories.llm_cache import LlmSemanticCacheRepository
from tests.conftest import _TestSessionFactory


def _soon() -> datetime:
    return datetime.now(UTC) + timedelta(hours=1)


def _past() -> datetime:
    return datetime.now(UTC) - timedelta(hours=1)


async def _insert(
    repo: LlmSemanticCacheRepository,
    embedding: list[float],
    completion: str,
    *,
    namespace: str = "ns",
    model: str = "gemma3:12b",
    role: str = "smart",
    json_mode: bool = False,
    expires_at: datetime | None = None,
) -> None:
    expires_at = expires_at or _soon()
    await repo.insert(
        namespace=namespace,
        model=model,
        role=role,
        json_mode=json_mode,
        embedding=embedding,
        completion=completion,
        expires_at=expires_at,
    )


def _find(repo: LlmSemanticCacheRepository, embedding: list[float], **kw: object):
    return repo.find_nearest(
        namespace=kw.get("namespace", "ns"),  # type: ignore[arg-type]
        model=kw.get("model", "gemma3:12b"),  # type: ignore[arg-type]
        role=kw.get("role", "smart"),  # type: ignore[arg-type]
        json_mode=kw.get("json_mode", False),  # type: ignore[arg-type]
        embedding=embedding,
        min_similarity=kw.get("min_similarity", 0.9),  # type: ignore[arg-type]
    )


class TestSemanticCacheRepo:
    async def test_hit_returns_completion_above_threshold(self) -> None:
        async with _TestSessionFactory() as s:
            repo = LlmSemanticCacheRepository(s)
            await _insert(repo, [1.0, 0.0, 0.0, 0.0], "cached answer")
            hit = await _find(repo, [1.0, 0.05, 0.0, 0.0])
            assert hit is not None
            completion, similarity = hit
            assert completion == "cached answer"
            assert similarity > 0.9

    async def test_miss_below_threshold(self) -> None:
        async with _TestSessionFactory() as s:
            repo = LlmSemanticCacheRepository(s)
            await _insert(repo, [1.0, 0.0, 0.0, 0.0], "cached")
            assert await _find(repo, [0.0, 0.0, 0.0, 1.0]) is None  # orthogonal → sim 0

    async def test_returns_nearest_of_many(self) -> None:
        async with _TestSessionFactory() as s:
            repo = LlmSemanticCacheRepository(s)
            await _insert(repo, [1.0, 0.0, 0.0, 0.0], "far-ish")
            await _insert(repo, [1.0, 0.2, 0.0, 0.0], "nearest")
            hit = await _find(repo, [1.0, 0.18, 0.0, 0.0], min_similarity=0.5)
            assert hit is not None and hit[0] == "nearest"

    async def test_scope_isolation(self) -> None:
        async with _TestSessionFactory() as s:
            repo = LlmSemanticCacheRepository(s)
            await _insert(repo, [1.0, 0.0, 0.0, 0.0], "other-user", namespace="userA")
            # Same vector, different namespace/model/role/json — none should match.
            q = [1.0, 0.0, 0.0, 0.0]
            assert await _find(repo, q, namespace="userB") is None
            assert await _find(repo, q, namespace="userA", model="other") is None
            assert await _find(repo, q, namespace="userA", role="fast") is None
            assert await _find(repo, q, namespace="userA", json_mode=True) is None
            assert await _find(repo, q, namespace="userA") is not None  # exact scope hits

    async def test_expired_entry_is_ignored(self) -> None:
        async with _TestSessionFactory() as s:
            repo = LlmSemanticCacheRepository(s)
            await _insert(repo, [1.0, 0.0, 0.0, 0.0], "stale", expires_at=_past())
            assert await _find(repo, [1.0, 0.0, 0.0, 0.0]) is None
