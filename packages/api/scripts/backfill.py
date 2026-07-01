"""CLI: batch re-inference / backfill of stale embeddings + extractions (Epic 28).

Dry-run by default (prints counts + what *would* change). Pass ``--apply`` to
reprocess. Idempotent and resumable: re-running only touches rows still stale, so a
crashed run just continues on the next invocation.

Usage:
    poetry run python scripts/backfill.py --kind embeddings                 # dry-run
    poetry run python scripts/backfill.py --kind embeddings --apply
    poetry run python scripts/backfill.py --kind extraction  --apply --limit 500
"""

from __future__ import annotations

import argparse
import asyncio

from slate.config import settings
from slate.core.backfill.service import BackfillKind, BackfillService
from slate.infrastructure.db.session import async_session_factory
from slate.infrastructure.embedding.factory import get_embedding_client
from slate.infrastructure.llm.factory import get_llm_client


async def _global_budget_ok() -> bool:
    """True while the Epic 14 global daily cost cap has headroom (fails open on error)."""
    if not settings.cost_guard_enabled:
        return True
    try:
        from slate.infrastructure.cache.usage_counter import day_bucket, peek_window
        from slate.infrastructure.config.dynamic import dynamic_config

        cap = await dynamic_config.get_int("cost_global_per_day")
        used = await peek_window(f"cost:g:day:{day_bucket()}")
        return used < cap
    except Exception:
        return True  # never let a cost-check outage block ops work


def _build_service() -> BackfillService:
    return BackfillService(
        async_session_factory,
        get_llm_client(settings),
        get_embedding_client(settings),
        settings,
    )


async def _run(kind: BackfillKind, apply: bool, limit: int | None) -> int:
    service = _build_service()
    plan = await service.plan(kind)
    print(
        f"kind={plan.kind}  version={plan.current_version!r}  "
        f"total={plan.total}  stale={plan.stale}"
    )
    if plan.stale == 0:
        print("✓ Corpus already current — nothing to do.")
        return 0
    if not apply:
        would = min(plan.stale, limit) if limit else plan.stale
        print(f"(dry-run) would reprocess {would} rows. Re-run with --apply.")
        return 0

    report = await service.run(kind, limit=limit, budget_ok=_global_budget_ok)
    tail = f"  (stopped: {report.stopped})" if report.stopped else ""
    print(f"✓ processed={report.processed}  failed={report.failed}{tail}")
    return 0 if report.failed == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill stale embeddings / extractions (Epic 28)"
    )
    parser.add_argument("--kind", choices=["embeddings", "extraction"], required=True)
    parser.add_argument("--apply", action="store_true", help="reprocess (default: dry-run)")
    parser.add_argument("--limit", type=int, default=None, help="max rows to attempt this run")
    args = parser.parse_args()
    return asyncio.run(_run(args.kind, args.apply, args.limit))


if __name__ == "__main__":
    raise SystemExit(main())
