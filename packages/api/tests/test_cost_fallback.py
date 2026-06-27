"""Tests for the in-process fixed-window counters (cost guard degraded mode)."""

from __future__ import annotations

import pytest

from dailyloadout.infrastructure.cache import cost_fallback


@pytest.fixture(autouse=True)
def _clean_store() -> object:
    cost_fallback.reset_local_windows()
    yield
    cost_fallback.reset_local_windows()


def test_incr_local_window_counts_up() -> None:
    assert cost_fallback.incr_local_window("k", 60, now=100.0) == 1
    assert cost_fallback.incr_local_window("k", 60, now=100.0) == 2
    assert cost_fallback.incr_local_window("k", 60, now=100.0) == 3


def test_incr_local_window_isolated_per_key() -> None:
    assert cost_fallback.incr_local_window("a", 60, now=0.0) == 1
    assert cost_fallback.incr_local_window("b", 60, now=0.0) == 1


def test_window_resets_after_ttl_expires() -> None:
    assert cost_fallback.incr_local_window("k", 60, now=0.0) == 1
    assert cost_fallback.incr_local_window("k", 60, now=30.0) == 2
    # Past the TTL boundary the window resets to 1 (slides, never extends).
    assert cost_fallback.incr_local_window("k", 60, now=61.0) == 1


def test_reset_local_windows_clears_all() -> None:
    cost_fallback.incr_local_window("k", 60, now=0.0)
    cost_fallback.reset_local_windows()
    assert cost_fallback.incr_local_window("k", 60, now=0.0) == 1


def test_expired_entries_are_pruned() -> None:
    # Fill past the prune threshold with already-expired keys, then trigger a
    # prune via one more incr at a later time — the store must not keep growing.
    for i in range(cost_fallback._PRUNE_THRESHOLD + 5):
        cost_fallback.incr_local_window(f"k{i}", 1, now=0.0)
    cost_fallback.incr_local_window("fresh", 60, now=100.0)
    # All the now=0.0 / ttl=1 windows are long expired and should be gone.
    assert len(cost_fallback._counts) == 1
    assert "fresh" in cost_fallback._counts
