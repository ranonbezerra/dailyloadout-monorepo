"""IGDB-specific exceptions."""


class IGDBNotConfigured(Exception):
    """IGDB credentials not provided. Enrichment skipped."""
