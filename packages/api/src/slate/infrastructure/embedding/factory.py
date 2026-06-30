"""Factory for the embedding client, mirroring ``llm/factory.py``."""

from __future__ import annotations

from slate.config import Settings

from .base import AbstractEmbeddingClient
from .dummy import DummyEmbeddingClient
from .ollama import OllamaEmbeddingClient


def get_embedding_client(settings: Settings) -> AbstractEmbeddingClient:
    """Return the embedding client appropriate for the current environment."""
    if settings.app_env == "testing":
        return DummyEmbeddingClient(dimensions=settings.embedding_dimensions)
    if settings.embedding_provider == "ollama":
        return OllamaEmbeddingClient(settings)
    if settings.embedding_provider == "dummy":
        return DummyEmbeddingClient(dimensions=settings.embedding_dimensions)
    raise ValueError(f"Unknown embedding provider: {settings.embedding_provider}")
