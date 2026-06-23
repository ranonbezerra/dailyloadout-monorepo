"""Factory for creating the appropriate LLM client based on settings."""

from __future__ import annotations

from dailyloadout.config import Settings

from .base import AbstractLLMClient
from .dummy import DummyLLMClient
from .ollama import OllamaClient


def get_llm_client(settings: Settings) -> AbstractLLMClient:
    """Return the LLM client appropriate for the current environment."""
    if settings.app_env == "testing":
        return DummyLLMClient()
    if settings.llm_provider == "ollama":
        return OllamaClient(settings)
    raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
