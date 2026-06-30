"""Embedding port: text → vectors for semantic retrieval over PlaySession history."""

from .base import AbstractEmbeddingClient
from .dummy import DummyEmbeddingClient
from .factory import get_embedding_client
from .ollama import OllamaEmbeddingClient
from .similarity import cosine_similarity, rank_by_similarity, select_grounding_ids

__all__ = [
    "AbstractEmbeddingClient",
    "DummyEmbeddingClient",
    "OllamaEmbeddingClient",
    "cosine_similarity",
    "get_embedding_client",
    "rank_by_similarity",
    "select_grounding_ids",
]
