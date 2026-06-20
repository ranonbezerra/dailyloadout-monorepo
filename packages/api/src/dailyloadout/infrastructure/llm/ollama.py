"""Ollama-backed LLM client for extracting game titles from text."""

from __future__ import annotations

import json
import re
from pathlib import Path

import httpx
import structlog
from jinja2 import Template

from dailyloadout.config import Settings

from .base import AbstractLLMClient, ExtractedGame, ExtractedState, LoadoutPick

logger = structlog.get_logger()

_PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"


def _load_prompt(name: str) -> Template:
    """Load a Jinja2 prompt template from the ``prompts/`` directory."""
    path = _PROMPTS_DIR / name
    return Template(path.read_text(encoding="utf-8"))


_CAPTURE_PARSE_TEMPLATE = _load_prompt("capture_parse.j2")
_CAPTURE_PARSE_VISION_TEMPLATE = _load_prompt("capture_parse_vision.j2")
_BRIEFING_TEMPLATE = _load_prompt("briefing.j2")
_DEBRIEF_EXTRACT_TEMPLATE = _load_prompt("debrief_extract.j2")
_LOADOUT_PICK_TEMPLATE = _load_prompt("loadout_pick.j2")

# Regex to find JSON array or object in free-text LLM output (handles
# markdown fences, preamble, etc.)
_JSON_BLOCK_RE = re.compile(
    r"```(?:json)?\s*([\[\{].*?[\]\}])\s*```"  # fenced code block
    r"|"
    r"([\[\{][\s\S]*[\]\}])",  # bare JSON
    re.DOTALL,
)


def _extract_json(text: str) -> str | None:
    """Extract the first JSON array or object from *text*.

    Vision models don't support ``format: "json"`` reliably, so the
    response may contain markdown fences or preamble text around the
    JSON payload.  This helper extracts the JSON portion.
    """
    text = text.strip()
    # Fast path: response is already valid JSON.
    if text.startswith(("[", "{")):
        return text
    m = _JSON_BLOCK_RE.search(text)
    if m:
        return m.group(1) or m.group(2)
    return None


class OllamaClient(AbstractLLMClient):
    """LLM client that calls a local Ollama instance."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._model = settings.ollama_fast_model
        self._smart_model = settings.ollama_smart_model
        self._vision_model = settings.ollama_vision_model
        self._timeout = settings.llm_timeout_seconds
        self._max_games_per_shelf = settings.capture_max_games_per_shelf

    async def parse_capture_text(self, text: str) -> list[ExtractedGame]:
        """Extract game titles from *text* using Ollama's generate endpoint."""
        prompt = _CAPTURE_PARSE_TEMPLATE.render(text=text)

        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/api/generate",
                    json=payload,
                )
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                logger.warning("ollama_request_failed", error=str(exc))
                return []

        try:
            body = resp.json()
            raw_text = body.get("response", "")
            parsed = json.loads(raw_text)

            # The LLM might return a dict with a key wrapping the array,
            # or a single game object instead of an array.
            if isinstance(parsed, dict):
                for key in ("games", "results", "titles"):
                    if key in parsed and isinstance(parsed[key], list):
                        parsed = parsed[key]
                        break
                else:
                    if "title" in parsed:
                        parsed = [parsed]
                    else:
                        logger.warning(
                            "ollama_unexpected_json_structure",
                            raw=raw_text,
                        )
                        return []

            if not isinstance(parsed, list):
                logger.warning("ollama_not_a_list", raw=raw_text)
                return []

            results: list[ExtractedGame] = []
            for item in parsed:
                if not isinstance(item, dict) or "title" not in item:
                    continue
                results.append(
                    ExtractedGame(
                        title=str(item["title"]),
                        platform_hint=item.get("platform_hint"),
                        confidence=float(item["confidence"])
                        if item.get("confidence") is not None
                        else None,
                    )
                )
            return results

        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.warning("ollama_parse_error", error=str(exc))
            return []

    async def parse_capture_image(self, image_base64: str) -> list[ExtractedGame]:
        """Extract game titles from an image using Ollama's vision endpoint."""
        prompt = _CAPTURE_PARSE_VISION_TEMPLATE.render(
            max_games=self._max_games_per_shelf,
        )

        payload = {
            "model": self._vision_model,
            "prompt": prompt,
            "images": [image_base64],
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/api/generate",
                    json=payload,
                )
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                logger.warning("ollama_vision_request_failed", error=str(exc))
                return []

        try:
            body = resp.json()
            raw_text = body.get("response", "")
            json_str = _extract_json(raw_text)
            if not json_str:
                logger.warning("ollama_vision_no_json_found", raw=raw_text[:500])
                return []
            parsed = json.loads(json_str)

            # The LLM might return a dict with a key wrapping the array,
            # or a single game object instead of an array.
            if isinstance(parsed, dict):
                for key in ("games", "results", "titles"):
                    if key in parsed and isinstance(parsed[key], list):
                        parsed = parsed[key]
                        break
                else:
                    if "title" in parsed:
                        parsed = [parsed]
                    else:
                        logger.warning(
                            "ollama_vision_unexpected_json_structure",
                            raw=raw_text,
                        )
                        return []

            if not isinstance(parsed, list):
                logger.warning("ollama_vision_not_a_list", raw=raw_text)
                return []

            results: list[ExtractedGame] = []
            for item in parsed[: self._max_games_per_shelf]:
                if not isinstance(item, dict) or "title" not in item:
                    continue
                results.append(
                    ExtractedGame(
                        title=str(item["title"]),
                        platform_hint=item.get("platform_hint"),
                        confidence=float(item["confidence"])
                        if item.get("confidence") is not None
                        else None,
                    )
                )
            return results

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
        prompt = _BRIEFING_TEMPLATE.render(
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

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/api/generate",
                    json=payload,
                )
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                logger.warning("ollama_briefing_failed", error=str(exc))
                return ""

        body: dict[str, str] = resp.json()
        return body.get("response", "").strip()

    async def extract_debrief_state(
        self,
        game_title: str,
        debrief_text: str,
    ) -> ExtractedState:
        """Extract structured state from a debrief using the fast LLM model."""
        prompt = _DEBRIEF_EXTRACT_TEMPLATE.render(
            game_title=game_title,
            debrief_text=debrief_text,
        )

        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/api/generate",
                    json=payload,
                )
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                logger.warning("ollama_debrief_extract_failed", error=str(exc))
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
        prompt = _LOADOUT_PICK_TEMPLATE.render(
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

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/api/generate",
                    json=payload,
                )
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                logger.warning("ollama_loadout_pick_failed", error=str(exc))
                raise

        body = resp.json()
        raw_text = body.get("response", "")
        parsed = json.loads(raw_text)

        return LoadoutPick(
            library_entry_public_id=str(parsed["library_entry_public_id"]),
            reasoning=str(parsed.get("reasoning", "")),
        )
