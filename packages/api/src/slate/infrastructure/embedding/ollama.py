"""Ollama-backed embedding client (local-first, no cloud).

Calls Ollama's batch ``/api/embed`` with the configured embedding model
(``nomic-embed-text`` by default). Mirrors ``OllamaClient``'s pooled-HTTP shape.
"""

from __future__ import annotations

import httpx
import structlog

from slate.config import Settings

from .base import AbstractEmbeddingClient

logger = structlog.get_logger()


class OllamaEmbeddingClient(AbstractEmbeddingClient):
    """Embeddings via a local Ollama instance."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._model = settings.ollama_embedding_model
        self._dimensions = settings.embedding_dimensions
        self._timeout = settings.llm_timeout_seconds
        self._http_client: httpx.AsyncClient | None = None

    @property
    def model(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=self._timeout)
        return self._http_client

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        client = await self._get_client()
        try:
            resp = await client.post(
                f"{self._base_url}/api/embed",
                json={"model": self._model, "input": texts},
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("embedding_failed", error=str(exc), count=len(texts))
            raise
        embeddings = resp.json().get("embeddings", [])
        return [[float(x) for x in vector] for vector in embeddings]
