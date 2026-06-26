"""Domain errors for the library layer.

Raised by the service so the router can map them to HTTP status codes without
the service depending on FastAPI/HTTP concerns.
"""

from __future__ import annotations


class CatalogImmutableError(Exception):
    """Attempted to edit a shared IGDB-canonical game (router maps to 403).

    ``Game`` rows are a shared global catalog deduped by ``igdb_id``/``slug``.
    IGDB-sourced rows are visible to every user, so they must not be rewritten by
    any single user. Non-IGDB rows (manual / pre-IGDB capture) stay editable.
    """
