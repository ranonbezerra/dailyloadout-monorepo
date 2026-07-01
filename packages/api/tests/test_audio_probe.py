"""Unit tests for the pre-transcription audio-duration probe (DoS guard)."""

from __future__ import annotations

from fractions import Fraction
from typing import Any

import av
import pytest

from slate.infrastructure.stt.audio_probe import probe_audio_duration_seconds


class _FakeStream:
    type = "audio"

    def __init__(self, duration: int | None, time_base: Fraction | None) -> None:
        self.duration = duration
        self.time_base = time_base


class _FakeContainer:
    def __init__(self, duration: int | None, streams: list[_FakeStream]) -> None:
        self.duration = duration
        self.streams = streams

    def __enter__(self) -> _FakeContainer:
        return self

    def __exit__(self, *_: Any) -> bool:
        return False


def test_reads_container_duration(monkeypatch: pytest.MonkeyPatch) -> None:
    # container.duration is in AV_TIME_BASE units (microseconds).
    monkeypatch.setattr(av, "open", lambda _p: _FakeContainer(5_000_000, []))
    assert probe_audio_duration_seconds("x") == pytest.approx(5.0)


def test_falls_back_to_stream_duration(monkeypatch: pytest.MonkeyPatch) -> None:
    stream = _FakeStream(duration=480_000, time_base=Fraction(1, 48_000))  # 10s
    monkeypatch.setattr(av, "open", lambda _p: _FakeContainer(None, [stream]))
    assert probe_audio_duration_seconds("x") == pytest.approx(10.0)


def test_returns_none_when_undeterminable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(av, "open", lambda _p: _FakeContainer(None, []))
    assert probe_audio_duration_seconds("x") is None


def test_returns_none_on_unparsable_file(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(_p: str) -> _FakeContainer:
        raise av.error.InvalidDataError(1, "bad")

    monkeypatch.setattr(av, "open", _boom)
    assert probe_audio_duration_seconds("x") is None
