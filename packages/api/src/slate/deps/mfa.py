"""MFA dependencies: the TOTP service wired to the request session."""

from typing import Annotated

from fastapi import Depends

from slate.core.auth.mfa import MfaService
from slate.infrastructure.db.repositories.mfa import MfaRepository

from .db import DbSession


def get_mfa_service(db: DbSession) -> MfaService:
    """Provide an ``MfaService`` bound to the current session."""
    return MfaService(MfaRepository(db))


MfaServiceDep = Annotated[MfaService, Depends(get_mfa_service)]
