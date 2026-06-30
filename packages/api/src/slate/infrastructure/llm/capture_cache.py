"""Two-layer cache over capture-parse: exact (Redis) + semantic (pgvector) (Epic 27).

Capture inputs are public game names that repeat with near-duplicate spellings, so
the semantic layer reuses a parse across "Elden Ring" / "elden ring (pc)" that the
exact hash misses. A single GLOBAL namespace is safe — nothing here is user-private.
Both layers degrade to a live call on any failure; one flag disables the whole thing.

Only ``parse_capture_text`` is cached; every other method passes straight through.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from slate.infrastructure.cache.base import AbstractCache
from slate.infrastructure.cache.keys import NS_CAPTURE, capture_key
from slate.infrastructure.db.repositories.llm_cache import LlmSemanticCacheRepository
from slate.infrastructure.embedding.base import AbstractEmbeddingClient

from .base import AbstractLLMClient, ExtractedGame, ExtractedState, LLMRole, PickSelection

logger = structlog.get_logger()

_WS = re.compile(r"\s+")
# Capture always runs the fast model in JSON mode; these tag the cache scope.
_ROLE = "fast"
_JSON = True


@dataclass
class CaptureCacheStats:
    """Per-layer outcome counters, so the hit-rate gain over exact-only is legible."""

    exact_hits: int = 0
    semantic_hits: int = 0
    misses: int = 0

    @property
    def total(self) -> int:
        return self.exact_hits + self.semantic_hits + self.misses

    @property
    def hit_rate(self) -> float:
        return (self.exact_hits + self.semantic_hits) / self.total if self.total else 0.0

    @property
    def exact_hit_rate(self) -> float:
        return self.exact_hits / self.total if self.total else 0.0

    @property
    def semantic_gain(self) -> float:
        """The slice of requests the semantic layer caught that exact-match missed."""
        return self.semantic_hits / self.total if self.total else 0.0


def _normalize(text: str) -> str:
    """Lowercase + collapse whitespace, so trivial spelling variants share a key."""
    return _WS.sub(" ", text.strip().lower())


def _games_to_payload(games: list[ExtractedGame]) -> list[dict[str, object]]:
    return [
        {"title": g.title, "platform_hint": g.platform_hint, "confidence": g.confidence}
        for g in games
    ]


def _payload_to_games(payload: object) -> list[ExtractedGame]:
    if not isinstance(payload, list):
        return []
    games: list[ExtractedGame] = []
    for d in payload:
        if not isinstance(d, dict) or not d.get("title"):
            continue
        hint = d.get("platform_hint")
        conf = d.get("confidence")
        games.append(
            ExtractedGame(
                title=str(d["title"]),
                platform_hint=str(hint) if hint is not None else None,
                confidence=float(conf) if isinstance(conf, (int, float)) else None,
            )
        )
    return games


class SemanticCaptureCache(AbstractLLMClient):
    """``parse_capture_text`` with an exact (Redis) cache and a semantic (pgvector) one."""

    def __init__(
        self,
        inner: AbstractLLMClient,
        embedding: AbstractEmbeddingClient,
        exact_cache: AbstractCache,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        model: str,
        ttl_seconds: int,
        threshold: float,
        enabled: bool = True,
    ) -> None:
        self._inner = inner
        self._embedding = embedding
        self._exact = exact_cache
        self._session_factory = session_factory
        self._model = model
        self._ttl = ttl_seconds
        self._threshold = threshold
        self._enabled = enabled
        self.stats = CaptureCacheStats()

    async def parse_capture_text(self, text: str) -> list[ExtractedGame]:
        normalized = _normalize(text)
        if not self._enabled or not normalized:
            return await self._inner.parse_capture_text(text)

        key = capture_key(self._model, normalized)
        cached = await self._exact.get_json(key)
        if cached is not None:
            self.stats.exact_hits += 1
            logger.info("capture_cache", layer="exact", outcome="hit")
            return _payload_to_games(cached)

        games = await self._semantic_or_live(normalized, text)
        if games:  # never cache an empty / failed parse
            await self._exact.set_json(key, _games_to_payload(games), self._ttl)
        return games

    async def _semantic_or_live(self, normalized: str, text: str) -> list[ExtractedGame]:
        embedding = await self._embed(normalized)
        if embedding is not None:
            hit = await self._semantic_lookup(embedding)
            if hit is not None:
                self.stats.semantic_hits += 1
                logger.info("capture_cache", layer="semantic", outcome="hit")
                return hit

        self.stats.misses += 1
        logger.info("capture_cache", layer="live", outcome="miss")
        games = await self._inner.parse_capture_text(text)
        if embedding is not None and games:
            await self._semantic_store(embedding, games)
        return games

    async def _embed(self, normalized: str) -> list[float] | None:
        try:
            return await self._embedding.embed_one(normalized)
        except Exception:
            logger.warning("capture_cache_embed_failed", exc_info=True)
            return None

    async def _semantic_lookup(self, embedding: list[float]) -> list[ExtractedGame] | None:
        try:
            async with self._session_factory() as session:
                repo = LlmSemanticCacheRepository(session)
                hit = await repo.find_nearest(
                    namespace=NS_CAPTURE,
                    model=self._model,
                    role=_ROLE,
                    json_mode=_JSON,
                    embedding=embedding,
                    min_similarity=self._threshold,
                )
            return _payload_to_games(json.loads(hit[0])) if hit else None
        except Exception:
            logger.warning("capture_cache_semantic_lookup_failed", exc_info=True)
            return None

    async def _semantic_store(self, embedding: list[float], games: list[ExtractedGame]) -> None:
        try:
            async with self._session_factory() as session:
                repo = LlmSemanticCacheRepository(session)
                await repo.insert(
                    namespace=NS_CAPTURE,
                    model=self._model,
                    role=_ROLE,
                    json_mode=_JSON,
                    embedding=embedding,
                    completion=json.dumps(_games_to_payload(games)),
                    expires_at=datetime.now(UTC) + timedelta(seconds=self._ttl),
                )
                await session.commit()
        except Exception:
            logger.warning("capture_cache_semantic_store_failed", exc_info=True)

    # -- Pass-through (uncached) -----------------------------------------

    async def parse_capture_image(self, image_base64: str) -> list[ExtractedGame]:
        return await self._inner.parse_capture_image(image_base64)

    async def generate_recap(
        self,
        game_title: str,
        previous_wrap_ups: list[dict[str, object]],
        current_next_action: str | None = None,
        position_override: str | None = None,
    ) -> str:
        return await self._inner.generate_recap(
            game_title, previous_wrap_ups, current_next_action, position_override
        )

    async def extract_wrap_up_state(self, game_title: str, wrap_up_text: str) -> ExtractedState:
        return await self._inner.extract_wrap_up_state(game_title, wrap_up_text)

    async def select_game(
        self,
        candidates: list[dict[str, object]],
        mood: str,
        available_minutes: int,
        mental_energy: str,
        context: str | None = None,
    ) -> PickSelection:
        return await self._inner.select_game(
            candidates, mood, available_minutes, mental_energy, context=context
        )

    async def complete(self, prompt: str, *, role: LLMRole = "fast", json: bool = False) -> str:
        return await self._inner.complete(prompt, role=role, json=json)
