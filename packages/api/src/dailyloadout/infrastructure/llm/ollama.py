"""Ollama-backed LLM client for extracting game titles from text."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import structlog
from jinja2 import Template

from dailyloadout.config import Settings

from .base import AbstractLLMClient, ExtractedGame

logger = structlog.get_logger()

_PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"


def _load_prompt(name: str) -> Template:
    """Load a Jinja2 prompt template from the ``prompts/`` directory."""
    path = _PROMPTS_DIR / name
    return Template(path.read_text(encoding="utf-8"))


_CAPTURE_PARSE_TEMPLATE = _load_prompt("capture_parse.j2")
_CAPTURE_PARSE_VISION_TEMPLATE = _load_prompt("capture_parse_vision.j2")


class OllamaClient(AbstractLLMClient):
    """LLM client that calls a local Ollama instance."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._model = settings.ollama_fast_model
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
                logger.warning("ollama_vision_request_failed", error=str(exc))
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
