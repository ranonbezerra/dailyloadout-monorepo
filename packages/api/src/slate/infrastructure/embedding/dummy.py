"""Deterministic embedding backend for tests and offline/CI runs.

Uses signed feature-hashing: each token is hashed to a dimension (and a sign), the
counts are L2-normalised. This is deterministic (same text → same vector) AND
similarity-bearing (texts that share tokens get higher cosine), so retrieval tests
can assert that the *relevant* session ranks above an unrelated one — without a model.
"""

from __future__ import annotations

import hashlib
import math
import re

from .base import AbstractEmbeddingClient

_TOKEN_RE = re.compile(r"[a-z0-9]+")


class DummyEmbeddingClient(AbstractEmbeddingClient):
    """Model-free embeddings: deterministic, normalised, and similarity-bearing."""

    def __init__(self, dimensions: int = 768, model: str = "dummy-embed") -> None:
        self._dimensions = dimensions
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def _vector(self, text: str) -> list[float]:
        vec = [0.0] * self._dimensions
        for token in _TOKEN_RE.findall(text.lower()):
            digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
            h = int.from_bytes(digest, "big")
            vec[h % self._dimensions] += 1.0 if (h >> 1) & 1 else -1.0
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0.0:
            # Empty / symbol-only text → a fixed unit vector so cosine stays defined.
            vec[0] = 1.0
            return vec
        return [v / norm for v in vec]
