"""Embedding port — the hexagonal boundary for turning text into vectors.

Same shape as ``llm/``: an abstract client with a real (Ollama) and a deterministic
(dummy) backend, selected by a factory. Embeddings ground the recap on the player's
*semantically* most relevant prior sessions instead of just the chronological last-N.

``model`` + ``dimensions`` are exposed so a stored vector can be versioned by the
model that produced it (a model swap means a re-embed, never a silent mismatch).
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class AbstractEmbeddingClient(ABC):
    """Contract for turning text into fixed-width vectors."""

    @property
    @abstractmethod
    def model(self) -> str:
        """Identifier of the embedding model (stored alongside the vector)."""
        ...

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Width of every vector this client returns."""
        ...

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed *texts*, returning one ``dimensions``-long vector per input."""
        ...

    async def embed_one(self, text: str) -> list[float]:
        """Convenience: embed a single string."""
        vectors = await self.embed([text])
        return vectors[0]
