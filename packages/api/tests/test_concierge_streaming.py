"""Tests for the Concierge streaming gate (ROADMAP Epic 16)."""

from __future__ import annotations

from dailyloadout.infrastructure.agent.concierge.streaming import (
    RecommendationGate,
    split_recommendation,
)


def _run(deltas: list[str]) -> tuple[str, str | None]:
    """Feed deltas through a gate; return (all emitted prose, recommendation id)."""
    gate = RecommendationGate()
    out = ""
    for d in deltas:
        out += gate.feed(d)
    tail, rec_id = gate.finish()
    return out + tail, rec_id


def test_split_recommendation() -> None:
    prose, rec = split_recommendation("Try this one.\nRECOMMEND: abc-123")
    assert prose == "Try this one."
    assert rec == "abc-123"
    assert split_recommendation("Nothing fits.") == ("Nothing fits.", None)


def test_prose_without_marker_streams_fully() -> None:
    text, rec = _run(["Hello ", "there, ", "play ", "something."])
    assert text == "Hello there, play something."
    assert rec is None


def test_marker_is_withheld_and_parsed() -> None:
    text, rec = _run(["Play this.\n", "RECOMMEND: abc"])
    assert "RECOMMEND" not in text
    assert "abc" not in text
    assert text.strip() == "Play this."
    assert rec == "abc"


def test_marker_split_across_deltas_never_leaks() -> None:
    text, rec = _run(["Go north.\n", "REC", "OMMEND:", " xyz-9"])
    assert "RECOMMEND" not in text
    assert "xyz-9" not in text
    assert text.strip() == "Go north."
    assert rec == "xyz-9"


def test_single_line_prose_streams_live() -> None:
    # No marker, no newline — should emit progressively, not buffer to the end.
    gate = RecommendationGate()
    first = gate.feed("I'd play ")
    second = gate.feed("Hades tonight.")
    tail, rec = gate.finish()
    assert first == "I'd play "  # streamed before the turn finished
    assert (first + second + tail) == "I'd play Hades tonight."
    assert rec is None


def test_recommend_word_in_prose_is_not_the_marker() -> None:
    # "Recommended:" diverges from the "RECOMMEND:" marker → treated as prose.
    text, rec = _run(["My top pick — ", "highly recommended for tonight."])
    assert text == "My top pick — highly recommended for tonight."
    assert rec is None
