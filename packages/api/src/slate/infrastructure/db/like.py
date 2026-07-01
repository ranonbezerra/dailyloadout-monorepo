"""Shared LIKE/ILIKE escaping.

Postgres ``LIKE``/``ILIKE`` has NO escape character unless one is declared, so
escaping ``%``/``_`` in the pattern is a no-op on its own. Always pair
:func:`escape_like` with ``.ilike(pattern, escape=LIKE_ESCAPE)`` — otherwise a
search term of ``%%%_%_...`` injects wildcards (pathological backtracking /
query-DoS, and over-broad matches).
"""

from __future__ import annotations

LIKE_ESCAPE = "\\"


def escape_like(term: str) -> str:
    """Escape LIKE/ILIKE wildcards in *term* so it matches literally.

    Escapes the backslash FIRST (so it doesn't double-escape the ``%``/``_``
    escapes), then ``%`` and ``_``. Use with ``escape=LIKE_ESCAPE``.
    """
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
