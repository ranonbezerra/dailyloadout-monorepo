"""Preload Ollama models on startup so the first request isn't a cold load.

A cold model load (especially the 7B concierge agent) can take tens of seconds
and, with no streamed output during the agent's first tool-deciding call, looks
like a hang. Warming the configured models in the background at startup means
the model is resident by the time the user sends a message.

Best-effort: any failure (Ollama down, model missing) is logged and skipped —
warming never blocks or breaks startup.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

logger = structlog.get_logger()


def _coerce_keep_alive(value: str) -> Any:
    """Pass numeric keep-alive as an int (e.g. -1 = forever), else as a string."""
    if value.lstrip("-").isdigit():
        return int(value)
    return value


async def warm_ollama_models(
    *,
    base_url: str,
    models: list[str],
    keep_alive: str = "-1",
    client: httpx.AsyncClient | None = None,
) -> None:
    """Send a tiny chat to each model so Ollama loads it into memory."""
    if not models:
        return
    keep = _coerce_keep_alive(keep_alive)
    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=httpx.Timeout(300.0))
    try:
        for model in models:
            try:
                await client.post(
                    f"{base_url}/api/chat",
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": "ok"}],
                        "stream": False,
                        "keep_alive": keep,
                    },
                )
                logger.info("ollama_model_warmed", model=model)
            except Exception:
                logger.warning("ollama_warm_failed", model=model, exc_info=True)
    finally:
        if owns_client:
            await client.aclose()
