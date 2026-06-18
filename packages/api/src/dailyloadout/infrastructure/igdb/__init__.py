"""IGDB infrastructure: API client and exception types."""

from .client import IGDBClient
from .exceptions import IGDBNotConfigured

__all__ = [
    "IGDBClient",
    "IGDBNotConfigured",
]
