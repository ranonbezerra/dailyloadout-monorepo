"""Tests for LLM and STT client factories."""

from __future__ import annotations

import pytest

from dailyloadout.config import Settings
from dailyloadout.infrastructure.llm.dummy import DummyLLMClient
from dailyloadout.infrastructure.llm.factory import get_llm_client
from dailyloadout.infrastructure.llm.ollama import OllamaClient
from dailyloadout.infrastructure.stt.dummy import DummySTTClient
from dailyloadout.infrastructure.stt.factory import get_stt_client


def _make_settings(**overrides: object) -> Settings:
    defaults = {
        "app_env": "development",
        "database_url": "sqlite+aiosqlite://",
        "redis_url": "redis://localhost:6380/0",
    }
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


class TestLLMFactory:
    def test_test_env_returns_dummy(self) -> None:
        s = _make_settings(app_env="testing")
        client = get_llm_client(s)
        assert isinstance(client, DummyLLMClient)

    def test_ollama_provider_returns_ollama(self) -> None:
        s = _make_settings(llm_provider="ollama")
        client = get_llm_client(s)
        assert isinstance(client, OllamaClient)

    def test_unknown_provider_raises(self) -> None:
        s = _make_settings(llm_provider="unknown")
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            get_llm_client(s)


class TestSTTFactory:
    def test_dummy_provider(self) -> None:
        s = _make_settings(stt_provider="dummy")
        client = get_stt_client(s)
        assert isinstance(client, DummySTTClient)

    def test_whisper_provider(self) -> None:
        s = _make_settings(stt_provider="whisper")
        from dailyloadout.infrastructure.stt.whisper import WhisperSTTClient

        client = get_stt_client(s)
        assert isinstance(client, WhisperSTTClient)

    def test_unknown_provider_raises(self) -> None:
        s = _make_settings(stt_provider="unknown")
        with pytest.raises(ValueError, match="Unknown STT provider"):
            get_stt_client(s)
