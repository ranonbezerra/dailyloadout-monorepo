"""Tests for the process-wide Ollama concurrency semaphore.

The semaphore bounds how many outbound model calls hit the host Ollama server at
once (per worker process). We patch the HTTP round-trip with a barrier that
records peak concurrency and assert it never exceeds the configured limit.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

from dailyloadout.config import Settings
from dailyloadout.infrastructure.llm import ollama as ollama_mod
from dailyloadout.infrastructure.llm.ollama import OllamaClient


@pytest.fixture(autouse=True)
def _reset_semaphore() -> None:
    """Clear the lazily-built singleton so each test rebinds to its loop/limit."""
    ollama_mod._ollama_semaphore = None


class _ConcurrencyProbe:
    """Tracks current + peak concurrent in-flight calls behind a barrier."""

    def __init__(self, hold: float = 0.05) -> None:
        self.current = 0
        self.peak = 0
        self._hold = hold
        self._lock = asyncio.Lock()

    async def __call__(self, *args: object, **kwargs: object) -> httpx.Response:
        async with self._lock:
            self.current += 1
            self.peak = max(self.peak, self.current)
        try:
            await asyncio.sleep(self._hold)
        finally:
            async with self._lock:
                self.current -= 1
        request = httpx.Request("POST", "http://ollama/api/generate")
        return httpx.Response(200, json={"response": "ok"}, request=request)


def _make_client(max_concurrency: int) -> OllamaClient:
    ollama_mod._settings = Settings(ollama_max_concurrency=max_concurrency)
    return OllamaClient(ollama_mod._settings)


async def test_semaphore_bounds_concurrency(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(max_concurrency=2)
    probe = _ConcurrencyProbe()

    http = await client._get_client()
    monkeypatch.setattr(http, "post", probe)

    # Fire many concurrent completions; only 2 may be in-flight at once.
    await asyncio.gather(*(client.complete(f"prompt-{i}") for i in range(8)))

    assert probe.peak <= 2
    assert probe.peak == 2  # the limit is actually reached (not accidentally 1)


async def test_semaphore_limit_is_configurable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _make_client(max_concurrency=4)
    probe = _ConcurrencyProbe()

    http = await client._get_client()
    monkeypatch.setattr(http, "post", probe)

    await asyncio.gather(*(client.complete(f"prompt-{i}") for i in range(8)))

    assert probe.peak <= 4
    assert probe.peak == 4
