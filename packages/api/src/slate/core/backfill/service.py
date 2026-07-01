"""Idempotent, resumable batch re-inference over the corpus (Epic 28).

When the embedding model or the extraction prompt/model changes, the stored vectors
and extracted state are stale. This service reprocesses them in bounded pages:

- **Idempotent** — a row is reprocessed only while its version marker differs from the
  current one; each success stamps the current version, so a re-run skips finished work.
- **Resumable** — paging by ``id > after_id`` advances past every row (even failures),
  so a crash mid-run just means the next run picks up the still-stale remainder.
- **Concurrency-capped** — inference calls within a page run under a semaphore, and each
  item commits in its own DB session, so a backfill never serializes on one connection
  nor floods the provider.
- **Budget-aware** — an optional ``budget_ok`` hook is polled before each page; the CLI
  wires it to the Epic 14 global cost cap so a backfill stops instead of breaching it.

The heavy lifting reuses the live paths: ``embed_session`` (Epic 24) for vectors and
``extract_wrap_up_state`` for state — no duplicated inference logic.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from slate.config import Settings
from slate.core.play_session.embedding import embed_session
from slate.infrastructure.db.repositories.backfill import BackfillRepository
from slate.infrastructure.db.repositories.play_session_embedding import (
    PlaySessionEmbeddingRepository,
)
from slate.infrastructure.embedding.base import AbstractEmbeddingClient
from slate.infrastructure.llm.base import AbstractLLMClient

logger = structlog.get_logger()

BackfillKind = Literal["embeddings", "extraction"]
BudgetHook = Callable[[], Awaitable[bool]]


@dataclass(frozen=True)
class BackfillPlan:
    """What a run *would* do — the dry-run result."""

    kind: BackfillKind
    current_version: str
    total: int
    stale: int


@dataclass(frozen=True)
class BackfillReport:
    """The outcome of a run."""

    kind: BackfillKind
    current_version: str
    processed: int
    failed: int
    stopped: str | None  # None = drained; "limit" | "budget" = stopped early


class BackfillService:
    """Reprocess stale embeddings or extractions across the corpus."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        llm_client: AbstractLLMClient,
        embedding_client: AbstractEmbeddingClient,
        settings: Settings,
    ) -> None:
        self._session_factory = session_factory
        self._llm = llm_client
        self._embedding = embedding_client
        self._settings = settings

    def _version(self, kind: BackfillKind) -> str:
        """The current version marker a processed row is stamped with."""
        if kind == "embeddings":
            return self._embedding.model
        return self._settings.extraction_version

    async def plan(self, kind: BackfillKind) -> BackfillPlan:
        """Count total and stale rows without touching anything (dry run)."""
        version = self._version(kind)
        async with self._session_factory() as session:
            repo = BackfillRepository(session)
            total = await repo.count_embeddable()
            stale = (
                await repo.count_stale_embeddings(version)
                if kind == "embeddings"
                else await repo.count_stale_extractions(version)
            )
        return BackfillPlan(kind=kind, current_version=version, total=total, stale=stale)

    async def run(
        self,
        kind: BackfillKind,
        *,
        limit: int | None = None,
        budget_ok: BudgetHook | None = None,
    ) -> BackfillReport:
        """Reprocess stale rows page by page until drained, limited, or out of budget."""
        version = self._version(kind)
        batch = self._settings.backfill_batch_size
        sem = asyncio.Semaphore(max(1, self._settings.backfill_concurrency))
        after_id = 0
        processed = failed = 0
        stopped: str | None = None

        while True:
            if budget_ok is not None and not await budget_ok():
                stopped = "budget"
                break
            page_limit = batch if limit is None else min(batch, limit - processed - failed)
            if page_limit <= 0:
                stopped = "limit"
                break

            async with self._session_factory() as session:
                rows = await self._page(kind, session, version, after_id, page_limit)
            if not rows:
                break

            async def _guarded(row: object) -> bool:
                async with sem:
                    return await self._process_one(kind, row, version)

            results = await asyncio.gather(*(_guarded(r) for r in rows))
            processed += sum(1 for ok in results if ok)
            failed += sum(1 for ok in results if not ok)
            after_id = rows[-1].id  # type: ignore[attr-defined]

        logger.info(
            "backfill_run_complete",
            kind=kind,
            version=version,
            processed=processed,
            failed=failed,
            stopped=stopped,
        )
        return BackfillReport(
            kind=kind,
            current_version=version,
            processed=processed,
            failed=failed,
            stopped=stopped,
        )

    async def _page(
        self,
        kind: BackfillKind,
        session: AsyncSession,
        version: str,
        after_id: int,
        limit: int,
    ) -> list[object]:
        repo = BackfillRepository(session)
        if kind == "embeddings":
            return list(await repo.page_stale_embeddings(version, after_id, limit))
        return list(await repo.page_stale_extractions(version, after_id, limit))

    async def _process_one(self, kind: BackfillKind, row: object, version: str) -> bool:
        """Reprocess one row in its own session. Returns whether it advanced to current."""
        try:
            async with self._session_factory() as session:
                ok = (
                    await self._reembed(session, row)
                    if kind == "embeddings"
                    else await self._reextract(session, row, version)
                )
                if ok:
                    await session.commit()
                return ok
        except Exception:
            logger.warning("backfill_item_failed", kind=kind, exc_info=True)
            return False

    async def _reembed(self, session: AsyncSession, row: object) -> bool:
        return await embed_session(
            self._embedding,
            PlaySessionEmbeddingRepository(session),
            row.id,  # type: ignore[attr-defined]
            row.wrap_up_text,  # type: ignore[attr-defined]
            row.extracted_state,  # type: ignore[attr-defined]
        )

    async def _reextract(self, session: AsyncSession, row: object, version: str) -> bool:
        extracted = await self._llm.extract_wrap_up_state(
            game_title=row.game_title,  # type: ignore[attr-defined]
            wrap_up_text=row.wrap_up_text,  # type: ignore[attr-defined]
        )
        state: dict[str, object] = {
            "location": extracted.location,
            "next_action": extracted.next_action,
            "level": extracted.level,
            "current_quest": extracted.current_quest,
        }
        await BackfillRepository(session).stamp_extraction(row.id, state, version)  # type: ignore[attr-defined]
        # Re-embed so the vector reflects the new state (mirrors the live extraction path).
        await embed_session(
            self._embedding,
            PlaySessionEmbeddingRepository(session),
            row.id,  # type: ignore[attr-defined]
            row.wrap_up_text,  # type: ignore[attr-defined]
            state,
        )
        return True
