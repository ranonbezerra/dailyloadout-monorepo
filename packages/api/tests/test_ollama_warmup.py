"""Tests for the Ollama startup warm-up (best-effort model preload)."""

from __future__ import annotations

from typing import Any

import httpx

from dailyloadout.infrastructure.llm.warmup import _coerce_keep_alive, warm_ollama_models


class _SpyClient:
    """Records the chat-load calls; optionally raises for one model."""

    def __init__(self, fail_on: str | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self._fail_on = fail_on

    async def post(self, url: str, json: dict[str, Any]) -> Any:
        if json["model"] == self._fail_on:
            raise httpx.ConnectError("ollama down")
        self.calls.append({"url": url, "json": json})


def test_coerce_keep_alive() -> None:
    assert _coerce_keep_alive("-1") == -1  # forever, as an int
    assert _coerce_keep_alive("300") == 300
    assert _coerce_keep_alive("60m") == "60m"  # duration string passes through


async def test_no_models_is_a_noop() -> None:
    client = _SpyClient()
    await warm_ollama_models(base_url="http://x", models=[], client=client)  # type: ignore[arg-type]
    assert client.calls == []


async def test_warms_each_model_with_keep_alive() -> None:
    client = _SpyClient()
    await warm_ollama_models(
        base_url="http://ollama:11434",
        models=["gemma3:4b", "qwen2.5:7b-instruct"],
        keep_alive="-1",
        client=client,  # type: ignore[arg-type]
    )
    assert [c["json"]["model"] for c in client.calls] == ["gemma3:4b", "qwen2.5:7b-instruct"]
    assert client.calls[0]["url"] == "http://ollama:11434/api/chat"
    assert client.calls[0]["json"]["keep_alive"] == -1
    assert client.calls[0]["json"]["stream"] is False


async def test_one_model_failing_does_not_stop_the_rest() -> None:
    client = _SpyClient(fail_on="gemma3:4b")
    await warm_ollama_models(
        base_url="http://x",
        models=["gemma3:4b", "qwen2.5:7b-instruct"],
        client=client,  # type: ignore[arg-type]
    )
    # The failing model is skipped; the next one still warms.
    assert [c["json"]["model"] for c in client.calls] == ["qwen2.5:7b-instruct"]
