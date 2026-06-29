"""IGDB-specific exceptions."""


class IGDBNotConfiguredError(Exception):
    """IGDB credentials not provided. Enrichment skipped."""
