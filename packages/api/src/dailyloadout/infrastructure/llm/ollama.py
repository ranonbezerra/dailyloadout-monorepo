"""Ollama-backed LLM client for extracting game titles from text."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import structlog
from jinja2.sandbox import SandboxedEnvironment

from dailyloadout.config import Settings
from dailyloadout.config import settings as _settings

from .base import AbstractLLMClient, ExtractedGame, ExtractedState, LLMRole, LoadoutPick
from .parsers import _extract_json, _parse_game_list

logger = structlog.get_logger()

# Process-shared ceiling on concurrent outbound model calls to the host Ollama
# server. Created lazily on first use so it binds to the running event loop (a
# module-import-time Semaphore would attach to the wrong/no loop). Only the real
# OllamaClient acquires it; the Dummy client (tests) never touches it.
_ollama_semaphore: asyncio.Semaphore | None = None


def _get_ollama_semaphore() -> asyncio.Semaphore:
    """Return the process-wide Ollama concurrency semaphore (lazy-initialized)."""
    global _ollama_semaphore
    if _ollama_semaphore is None:
        _ollama_semaphore = asyncio.Semaphore(_settings.ollama_max_concurrency)
    return _ollama_semaphore


_PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"

_jinja_env = SandboxedEnvironment(autoescape=False)


def _load_prompt(name: str) -> str:
    """Load a Jinja2 prompt template source from the ``prompts/`` directory."""
    path = _PROMPTS_DIR / name
    return path.read_text(encoding="utf-8")


_CAPTURE_PARSE_SRC = _load_prompt("capture_parse.j2")
_CAPTURE_PARSE_VISION_SRC = _load_prompt("capture_parse_vision.j2")
_BRIEFING_SRC = _load_prompt("briefing.j2")
_DEBRIEF_EXTRACT_SRC = _load_prompt("debrief_extract.j2")
_LOADOUT_PICK_SRC = _load_prompt("loadout_pick.j2")


class OllamaClient(AbstractLLMClient):
    """LLM client that calls a local Ollama instance."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._model = settings.ollama_fast_model
        self._smart_model = settings.ollama_smart_model
        self._vision_model = settings.ollama_vision_model
        self._timeout = settings.llm_timeout_seconds
        self._max_games_per_shelf = settings.capture_max_games_per_shelf
        self._max_output_tokens = settings.llm_max_output_tokens
        self._http_client: httpx.AsyncClient | None = None

    def _payload(self, payload: dict[str, object]) -> dict[str, object]:
        """Inject the ``options.num_predict`` output-token cap into *payload*."""
        existing = payload.get("options")
        options: dict[str, object] = dict(existing) if isinstance(existing, dict) else {}
        options.setdefault("num_predict", self._max_output_tokens)
        return {**payload, "options": options}

    async def _get_client(self) -> httpx.AsyncClient:
        """Return a reusable HTTP client (connection pooling)."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=self._timeout)
        return self._http_client

    # -- shared HTTP helper ---------------------------------------------------

    async def _call_generate(
        self,
        payload: dict[str, object],
        log_key: str,
    ) -> httpx.Response | None:
        """POST to Ollama ``/api/generate``. Returns *None* on HTTP error.

        The outbound model call is gated by the process-wide concurrency
        semaphore (held ONLY around the HTTP round-trip) so a burst can't
        oversubscribe the host.
        """
        client = await self._get_client()
        try:
            async with _get_ollama_semaphore():
                resp = await client.post(
                    f"{self._base_url}/api/generate",
                    json=self._payload(payload),
                )
            resp.raise_for_status()
            return resp
        except httpx.HTTPError as exc:
            logger.warning(log_key, error=str(exc))
            return None

    # -- public methods -------------------------------------------------------

    async def parse_capture_text(self, text: str) -> list[ExtractedGame]:
        """Extract game titles from *text* using Ollama's generate endpoint."""
        prompt = _jinja_env.from_string(_CAPTURE_PARSE_SRC).render(text=text)
        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }

        resp = await self._call_generate(payload, "ollama_request_failed")
        if resp is None:
            return []

        try:
            body = resp.json()
            raw_text = body.get("response", "")
            parsed = json.loads(raw_text)

            results = _parse_game_list(parsed, raw_text, log_prefix="ollama")
            return results if results is not None else []

        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.warning("ollama_parse_error", error=str(exc))
            return []

    async def parse_capture_image(self, image_base64: str) -> list[ExtractedGame]:
        """Extract game titles from an image using Ollama's vision endpoint."""
        prompt = _jinja_env.from_string(_CAPTURE_PARSE_VISION_SRC).render(
            max_games=self._max_games_per_shelf,
        )
        payload = {
            "model": self._vision_model,
            "prompt": prompt,
            "images": [image_base64],
            "stream": False,
        }

        resp = await self._call_generate(payload, "ollama_vision_request_failed")
        if resp is None:
            return []

        try:
            body = resp.json()
            raw_text = body.get("response", "")
            json_str = _extract_json(raw_text)
            if not json_str:
                logger.warning("ollama_vision_no_json_found", raw=raw_text[:500])
                return []
            parsed = json.loads(json_str)

            results = _parse_game_list(
                parsed,
                raw_text,
                log_prefix="ollama_vision",
                max_items=self._max_games_per_shelf,
            )
            return results if results is not None else []

        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.warning("ollama_vision_parse_error", error=str(exc))
            return []

    async def generate_briefing(
        self,
        game_title: str,
        previous_debriefs: list[dict[str, object]],
        current_next_action: str | None = None,
        position_override: str | None = None,
    ) -> str:
        """Generate a mission briefing using the smart LLM model."""
        prompt = _jinja_env.from_string(_BRIEFING_SRC).render(
            game_title=game_title,
            previous_debriefs=previous_debriefs,
            current_next_action=current_next_action,
            position_override=position_override,
        )
        payload = {
            "model": self._smart_model,
            "prompt": prompt,
            "stream": False,
        }

        resp = await self._call_generate(payload, "ollama_briefing_failed")
        if resp is None:
            return ""

        body: dict[str, str] = resp.json()
        return body.get("response", "").strip()

    async def extract_debrief_state(
        self,
        game_title: str,
        debrief_text: str,
    ) -> ExtractedState:
        """Extract structured state from a debrief using the fast LLM model."""
        prompt = _jinja_env.from_string(_DEBRIEF_EXTRACT_SRC).render(
            game_title=game_title,
            debrief_text=debrief_text,
        )
        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }

        resp = await self._call_generate(payload, "ollama_debrief_extract_failed")
        if resp is None:
            return ExtractedState()

        try:
            body = resp.json()
            raw_text = body.get("response", "")
            parsed = json.loads(raw_text)

            if not isinstance(parsed, dict):
                logger.warning("ollama_debrief_not_a_dict", raw=raw_text)
                return ExtractedState()

            return ExtractedState(
                location=parsed.get("location"),
                next_action=parsed.get("next_action"),
                level=str(parsed["level"]) if parsed.get("level") is not None else None,
                current_quest=parsed.get("current_quest"),
            )
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.warning("ollama_debrief_parse_error", error=str(exc))
            return ExtractedState()

    async def pick_loadout_game(
        self,
        candidates: list[dict[str, object]],
        mood: str,
        available_minutes: int,
        mental_energy: str,
        context: str | None = None,
    ) -> LoadoutPick:
        """Pick a game from candidates using the smart LLM model."""
        prompt = _jinja_env.from_string(_LOADOUT_PICK_SRC).render(
            candidates=candidates,
            mood=mood,
            available_minutes=available_minutes,
            mental_energy=mental_energy,
            context=context,
        )
        payload = {
            "model": self._smart_model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }

        resp = await self._call_generate(payload, "ollama_loadout_pick_failed")
        if resp is None:
            raise httpx.HTTPError("Ollama loadout pick request failed")

        try:
            body = resp.json()
            raw_text = body.get("response", "")
            parsed = json.loads(raw_text)

            return LoadoutPick(
                library_entry_public_id=str(parsed["library_entry_public_id"]),
                reasoning=str(parsed.get("reasoning", "")),
            )
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.warning("ollama_loadout_pick_parse_error", error=str(exc))
            raise httpx.HTTPError("Failed to parse loadout pick response") from exc

    async def complete(
        self,
        prompt: str,
        *,
        role: LLMRole = "fast",
        json: bool = False,
    ) -> str:
        """Run a single completion for a pre-rendered *prompt*."""
        model = self._smart_model if role == "smart" else self._model
        payload: dict[str, object] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if json:
            payload["format"] = "json"

        resp = await self._call_generate(payload, "ollama_complete_failed")
        if resp is None:
            return ""

        body: dict[str, str] = resp.json()
        return body.get("response", "").strip()
