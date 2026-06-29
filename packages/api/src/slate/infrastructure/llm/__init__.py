"""LLM infrastructure: abstract client, Ollama backend, and factory."""

from .base import AbstractLLMClient, ExtractedGame
from .factory import get_llm_client

__all__ = [
    "AbstractLLMClient",
    "ExtractedGame",
    "get_llm_client",
]
