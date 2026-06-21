"""IGDB infrastructure: API client and exception types."""

from .client import IGDBClient
from .exceptions import IGDBNotConfiguredError

__all__ = [
    "IGDBClient",
    "IGDBNotConfiguredError",
]
