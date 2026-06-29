"""Catalog matching port: OCR line -> canonical game (ROADMAP Epic 14)."""

from .base import AbstractCatalogMatcher, CatalogMatch
from .factory import get_catalog_matcher

__all__ = [
    "AbstractCatalogMatcher",
    "CatalogMatch",
    "get_catalog_matcher",
]
