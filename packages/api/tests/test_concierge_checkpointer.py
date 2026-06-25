"""Tests for the Concierge thread checkpointer selection (ROADMAP Epic 16).

The live Postgres saver needs a real database (integration-only); here we cover
the pure conninfo conversion and the memory-fallback selection.
"""

from __future__ import annotations

from typing import Any

import pytest
from langgraph.checkpoint.memory import MemorySaver

from dailyloadout.config import Settings
from dailyloadout.infrastructure.agent.concierge import checkpointer as cp
from dailyloadout.infrastructure.agent.concierge.checkpointer import (
    get_checkpointer,
    to_psycopg_conninfo,
)


@pytest.fixture
def _reset_postgres_singleton() -> Any:
    cp._postgres = None
    cp._postgres_tried = False
    yield
    cp._postgres = None
    cp._postgres_tried = False


def test_to_psycopg_conninfo_strips_asyncpg_driver() -> None:
    assert (
        to_psycopg_conninfo("postgresql+asyncpg://u:p@host:5432/db")
        == "postgresql://u:p@host:5432/db"
    )


async def test_memory_checkpointer_is_selected_for_non_postgres() -> None:
    saver = await get_checkpointer(Settings(concierge_checkpointer="memory"))
    assert isinstance(saver, MemorySaver)


async def test_postgres_branch_inits_once_then_caches(
    monkeypatch: pytest.MonkeyPatch, _reset_postgres_singleton: Any
) -> None:
    sentinel = object()
    calls = {"n": 0}

    async def _fake_init(_settings: Settings) -> object:
        calls["n"] += 1
        return sentinel

    monkeypatch.setattr(cp, "_init_postgres", _fake_init)
    settings = Settings(concierge_checkpointer="postgres")

    first = await get_checkpointer(settings)
    second = await get_checkpointer(settings)

    assert first is sentinel
    assert second is sentinel
    assert calls["n"] == 1  # initialised once, then cached


async def test_postgres_init_failure_falls_back_to_memory(
    monkeypatch: pytest.MonkeyPatch, _reset_postgres_singleton: Any
) -> None:
    async def _failed_init(_settings: Settings) -> None:
        return None  # mimics a Postgres init failure

    monkeypatch.setattr(cp, "_init_postgres", _failed_init)
    saver = await get_checkpointer(Settings(concierge_checkpointer="postgres"))
    assert isinstance(saver, MemorySaver)
