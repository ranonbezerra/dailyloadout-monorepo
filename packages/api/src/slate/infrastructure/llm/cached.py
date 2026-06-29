"""Caching decorator for the LLM client (ROADMAP Epic 18).

Caches the generic ``complete()`` escape hatch — the deep-research graph renders
its own prompts and fires the same grade/refine/synthesize prompts across runs,
so identical (prompt, role, json) calls are de-duped. The structured methods
(captures, recap, pick, wrap_up extraction) pass straight through: their
inputs vary per request and several are intentionally non-idempotent.

Empty output (a backend failure returns "") is never cached.
"""

from __future__ import annotations

from slate.infrastructure.cache.base import AbstractCache
from slate.infrastructure.cache.keys import NS_LLM, llm_key
from slate.infrastructure.cache.layer import cached_call

from .base import (
    AbstractLLMClient,
    ExtractedGame,
    ExtractedState,
    LLMRole,
    PickSelection,
)


class CachedLLMClient(AbstractLLMClient):
    """An ``AbstractLLMClient`` that caches ``complete()`` around an inner client."""

    def __init__(self, inner: AbstractLLMClient, cache: AbstractCache, ttl_seconds: int) -> None:
        self._inner = inner
        self._cache = cache
        self._ttl = ttl_seconds

    async def complete(self, prompt: str, *, role: LLMRole = "fast", json: bool = False) -> str:
        return await cached_call(
            cache=self._cache,
            key=llm_key("complete", role, json, prompt),
            ttl_seconds=self._ttl,
            namespace=NS_LLM,
            compute=lambda: self._inner.complete(prompt, role=role, json=json),
            cache_if=bool,  # don't cache empty (backend-failure) output
        )

    # -- Pass-through (uncached) -----------------------------------------

    async def parse_capture_text(self, text: str) -> list[ExtractedGame]:
        return await self._inner.parse_capture_text(text)

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
