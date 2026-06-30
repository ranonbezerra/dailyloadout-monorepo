"""Tracing decorator for the LLM client (Epic 23, observability half).

Wraps any ``AbstractLLMClient`` and emits one span per call — operation, model
role, latency, and output size, plus a redacted prompt/output preview when
``trace_capture_enabled``. The Ollama client enriches the active span with token
counts via ``add_span_attrs``; cloud adapters can add cost the same way.
"""

from __future__ import annotations

from slate.config import settings
from slate.infrastructure.observability.tracing import redact, span

from .base import (
    AbstractLLMClient,
    ExtractedGame,
    ExtractedState,
    LLMRole,
    PickSelection,
)

_CAPTURE_MAX_CHARS = 500


def _capture(**fields: object) -> dict[str, object]:
    """Return redacted capture attrs, or nothing when capture is disabled."""
    if not settings.trace_capture_enabled:
        return {}
    return {k: redact(str(v), _CAPTURE_MAX_CHARS) for k, v in fields.items()}


class TracedLLMClient(AbstractLLMClient):
    """An ``AbstractLLMClient`` that emits a span around each call to *inner*."""

    def __init__(self, inner: AbstractLLMClient) -> None:
        self._inner = inner

    async def parse_capture_text(self, text: str) -> list[ExtractedGame]:
        async with span("llm.parse_capture_text", role="fast", op="capture") as s:
            result = await self._inner.parse_capture_text(text)
            s.attrs["output_count"] = len(result)
            s.attrs.update(_capture(input=text))
            return result

    async def parse_capture_image(self, image_base64: str) -> list[ExtractedGame]:
        async with span("llm.parse_capture_image", role="vision", op="capture") as s:
            result = await self._inner.parse_capture_image(image_base64)
            s.attrs["output_count"] = len(result)
            return result

    async def generate_recap(
        self,
        game_title: str,
        previous_wrap_ups: list[dict[str, object]],
        current_next_action: str | None = None,
        position_override: str | None = None,
    ) -> str:
        async with span("llm.generate_recap", role="smart", op="recap") as s:
            result = await self._inner.generate_recap(
                game_title, previous_wrap_ups, current_next_action, position_override
            )
            s.attrs["output_chars"] = len(result)
            s.attrs.update(_capture(game_title=game_title, output=result))
            return result

    async def extract_wrap_up_state(self, game_title: str, wrap_up_text: str) -> ExtractedState:
        async with span("llm.extract_wrap_up_state", role="fast", op="wrap_up") as s:
            result = await self._inner.extract_wrap_up_state(game_title, wrap_up_text)
            s.attrs.update(_capture(input=wrap_up_text, output=result))
            return result

    async def select_game(
        self,
        candidates: list[dict[str, object]],
        mood: str,
        available_minutes: int,
        mental_energy: str,
        context: str | None = None,
    ) -> PickSelection:
        async with span("llm.select_game", role="smart", op="pick") as s:
            result = await self._inner.select_game(
                candidates, mood, available_minutes, mental_energy, context=context
            )
            s.attrs.update(_capture(output=result.library_entry_public_id))
            return result

    async def complete(self, prompt: str, *, role: LLMRole = "fast", json: bool = False) -> str:
        async with span("llm.complete", role=role, op="complete", json=json) as s:
            result = await self._inner.complete(prompt, role=role, json=json)
            s.attrs["output_chars"] = len(result)
            s.attrs.update(_capture(prompt=prompt, output=result))
            return result
