"""Breached-password port: local blocklist, HIBP k-anonymity adapter, factory."""

from __future__ import annotations

import hashlib
from typing import Any

import pytest

from slate.core.auth import breach
from slate.core.auth.breach import (
    BreachedPasswordError,
    HIBPChecker,
    LocalBlocklistChecker,
    NullBreachChecker,
    assert_password_not_breached,
    get_breach_checker,
)


def _suffix(password: str) -> str:
    return hashlib.sha1(password.encode()).hexdigest().upper()[5:]  # noqa: S324 — HIBP uses SHA-1


class _FakeResp:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


class _FakeClient:
    def __init__(self, *, text: str = "", error: Exception | None = None) -> None:
        self._text = text
        self._error = error

    async def __aenter__(self) -> _FakeClient:
        return self

    async def __aexit__(self, *_a: object) -> bool:
        return False

    async def get(self, _url: str, headers: dict[str, str] | None = None) -> _FakeResp:
        if self._error is not None:
            raise self._error
        return _FakeResp(self._text)


def _patch_hibp(monkeypatch: pytest.MonkeyPatch, **kw: Any) -> None:
    monkeypatch.setattr(breach.httpx, "AsyncClient", lambda **_k: _FakeClient(**kw))


class TestLocalAndNull:
    async def test_local_flags_common_password(self) -> None:
        assert await LocalBlocklistChecker().is_breached("Password123") is True
        assert await LocalBlocklistChecker().is_breached("q7$Fbz-Wintermute92") is False

    async def test_null_never_flags(self) -> None:
        assert await NullBreachChecker().is_breached("Password123") is False


class TestHIBP:
    async def test_breached_when_suffix_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        pw = "hunter2guessme"
        _patch_hibp(monkeypatch, text=f"{_suffix(pw)}:42\nAAAAA:1")
        assert await HIBPChecker().is_breached(pw) is True

    async def test_not_breached_when_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_hibp(monkeypatch, text="0123456789ABCDEF0123456789ABCDEF01234567:9\nAAAAA:1")
        assert await HIBPChecker().is_breached("some-unlisted-pass") is False

    async def test_padded_zero_count_is_not_breached(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pw = "paddedrow"
        _patch_hibp(monkeypatch, text=f"{_suffix(pw)}:0")  # padding rows carry count 0
        assert await HIBPChecker().is_breached(pw) is False

    async def test_fails_open_on_network_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_hibp(monkeypatch, error=RuntimeError("HIBP down"))
        # A third-party outage must never block a signup.
        assert await HIBPChecker().is_breached("Password123") is False


class TestFactoryAndGuard:
    def test_factory_selects_by_provider(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(breach.settings, "password_breach_provider", "hibp")
        assert isinstance(get_breach_checker(), HIBPChecker)
        monkeypatch.setattr(breach.settings, "password_breach_provider", "null")
        assert isinstance(get_breach_checker(), NullBreachChecker)
        monkeypatch.setattr(breach.settings, "password_breach_provider", "local")
        assert isinstance(get_breach_checker(), LocalBlocklistChecker)

    async def test_assert_raises_on_breached(self) -> None:
        with pytest.raises(BreachedPasswordError):
            await assert_password_not_breached(LocalBlocklistChecker(), "Password123")
        # A strong password does not raise.
        await assert_password_not_breached(LocalBlocklistChecker(), "q7$Fbz-Wintermute92")
