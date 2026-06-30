"""Contract tests for structured logs that must not leak sensitive data."""

from __future__ import annotations

from uuid import UUID

import pytest

from slate.core.admin import logging as admin_log
from slate.core.auth import logging as auth_log
from slate.infrastructure.db.models import User

_EMAIL = "Sensitive.User+demo@example.com"
_TOKEN = "raw-refresh-token-secret"
_PROMPT = "Previously on this very private game session..."


class _LogSpy:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, object]]] = []

    def info(self, event: str, **fields: object) -> None:
        self.events.append((event, fields))

    def warning(self, event: str, **fields: object) -> None:
        self.events.append((event, fields))


def _user(user_id: int, public_id: str, email: str) -> User:
    user = User(email=email, password_hash="hash", display_name="Demo")
    user.id = user_id
    user.public_id = UUID(public_id)
    return user


def _assert_no_sensitive_values(fields: dict[str, object]) -> None:
    rendered = str(fields)
    assert _EMAIL not in rendered
    assert _TOKEN not in rendered
    assert _PROMPT not in rendered


def test_auth_failure_logs_hash_email_without_raw_identifier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spy = _LogSpy()
    monkeypatch.setattr(auth_log, "logger", spy)

    auth_log.register_rejected(_EMAIL, reason="email_exists")
    auth_log.login_failed(_EMAIL)

    assert [event for event, _fields in spy.events] == [
        "auth_register_rejected",
        "auth_login_failed",
    ]
    for _event, fields in spy.events:
        assert fields["email_hash"]
        assert "email" not in fields
        _assert_no_sensitive_values(fields)


def test_auth_success_logs_ids_without_email_or_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spy = _LogSpy()
    monkeypatch.setattr(auth_log, "logger", spy)
    user = _user(10, "11111111-1111-4111-8111-111111111111", _EMAIL)

    auth_log.register_succeeded(user, auto_verified=True)
    auth_log.login_succeeded(user, device_label_present=True)
    auth_log.refresh_rotated(user)

    assert [event for event, _fields in spy.events] == [
        "auth_register_succeeded",
        "auth_login_succeeded",
        "auth_refresh_rotated",
    ]
    for _event, fields in spy.events:
        assert fields["user_id"] == 10
        assert fields["user_public_id"] == str(user.public_id)
        _assert_no_sensitive_values(fields)


def test_admin_logs_use_public_ids_and_boolean_reason_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spy = _LogSpy()
    monkeypatch.setattr(admin_log, "logger", spy)
    actor = _user(1, "22222222-2222-4222-8222-222222222222", "admin@example.com")
    target = _user(2, "33333333-3333-4333-8333-333333333333", _EMAIL)

    admin_log.log_admin_event(
        "admin_user_banned",
        actor=actor,
        action="user.ban",
        target_user=target,
        reason_present=True,
    )

    event, fields = spy.events[0]
    assert event == "admin_user_banned"
    assert fields["admin_public_id"] == str(actor.public_id)
    assert fields["target_public_id"] == str(target.public_id)
    assert fields["reason_present"] is True
    assert "reason" not in fields
    _assert_no_sensitive_values(fields)
