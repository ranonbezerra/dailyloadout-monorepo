"""Shared parsing helpers for LLM response post-processing."""

from __future__ import annotations

import re

import structlog

from .base import ExtractedGame

logger = structlog.get_logger()

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


def _parse_game_list(
    parsed: object,
    raw_text: str,
    *,
    log_prefix: str = "ollama",
    max_items: int | None = None,
) -> list[ExtractedGame] | None:
    """Unwrap dict-wrapped arrays and convert items to :class:`ExtractedGame`.

    Returns ``None`` when the structure is unrecognisable (caller should
    return ``[]`` and has already logged the raw text).  Otherwise returns
    the parsed list of :class:`ExtractedGame` objects.
    """
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
                    f"{log_prefix}_unexpected_json_structure",
                    raw=raw_text,
                )
                return None

    if not isinstance(parsed, list):
        logger.warning(f"{log_prefix}_not_a_list", raw=raw_text)
        return None

    items: list[dict[str, object]] = parsed
    if max_items is not None:
        items = items[:max_items]

    results: list[ExtractedGame] = []
    for item in items:
        if not isinstance(item, dict) or "title" not in item:
            continue
        raw_conf = item.get("confidence")
        results.append(
            ExtractedGame(
                title=str(item["title"]),
                platform_hint=item.get("platform_hint"),  # type: ignore[arg-type]
                confidence=float(str(raw_conf)) if raw_conf is not None else None,
            )
        )
    return results
