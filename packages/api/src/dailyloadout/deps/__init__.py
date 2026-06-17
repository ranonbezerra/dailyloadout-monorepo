"""FastAPI dependencies for DailyLoadout.

Re-exports all dependency aliases so existing imports keep working:

    from dailyloadout.deps import AuthServiceDep, CurrentUserDep
"""

from .auth import AuthServiceDep, CurrentUserDep
from .db import DbSession, get_db

__all__ = [
    "AuthServiceDep",
    "CurrentUserDep",
    "DbSession",
    "get_db",
]
