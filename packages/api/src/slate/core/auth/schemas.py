"""Pydantic request / response schemas for the auth layer."""

from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from slate.core.sanitization import sanitize_display_name


def _validate_password_complexity(v: str) -> str:
    """Require at least one upper, one lower, and one digit (shared by flows)."""
    if not re.search(r"[A-Z]", v):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", v):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", v):
        raise ValueError("Password must contain at least one digit")
    return v


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=100)

    @field_validator("display_name")
    @classmethod
    def _clean_display_name(cls, v: str) -> str:
        """NFKC-normalise and reject control/bidi/zero-width chars (homoglyphs)."""
        return sanitize_display_name(v)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        return _validate_password_complexity(v)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    # Optional so cookie-mode web callers can POST refresh/logout with no body;
    # in that case the token is read from the httpOnly cookie instead.
    refresh_token: str = ""


class VerifyEmailRequest(BaseModel):
    # Optional in the body so the token may instead arrive as a query param.
    token: str = ""


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        return _validate_password_complexity(v)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        return _validate_password_complexity(v)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    public_id: UUID
    email: str
    display_name: str
    avatar_url: str | None
    email_verified: bool
    locale: str
    timezone: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    message: str


__all__ = [
    "ChangePasswordRequest",
    "ForgotPasswordRequest",
    "LoginRequest",
    "MessageResponse",
    "RefreshRequest",
    "RegisterRequest",
    "ResendVerificationRequest",
    "ResetPasswordRequest",
    "TokenResponse",
    "UserResponse",
    "VerifyEmailRequest",
]
