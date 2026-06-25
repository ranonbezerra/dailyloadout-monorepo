"""Tests for the bulk library-import path (ROADMAP Epic 14).

Covers the processor (OCR -> confidence gate -> vision fallback -> catalog match)
and the endpoints (multi-image import, per-day cap, bulk confirm). The dummy OCR
treats uploaded bytes as UTF-8 lines, so "images" are newline-separated titles.
"""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import uuid4

from httpx import AsyncClient

from dailyloadout.config import settings
from dailyloadout.infrastructure.catalog.dummy import DummyCatalogMatcher
from dailyloadout.infrastructure.db.repositories.capture import (
    CaptureCandidateRepository,
    CaptureRepository,
)
from dailyloadout.infrastructure.db.repositories.usage import UsageCounterRepository
from dailyloadout.infrastructure.ocr.base import AbstractOCRClient, OcrLine, OcrResult
from dailyloadout.infrastructure.ocr.dummy import DummyOCRClient
from dailyloadout.workers.library_import_processor import (
    VISION_FALLBACK_KEY,
    process_library_import,
)
from tests.conftest import _TestSessionFactory


class _StubFallbackOCR(AbstractOCRClient):
    """A fallback that always returns clean, high-confidence titles."""

    def __init__(self, titles: list[str]) -> None:
        self._titles = titles

    async def extract_lines(self, image_bytes: bytes) -> OcrResult:
        lines = [OcrLine(text=t, confidence=0.95) for t in self._titles]
        return OcrResult(lines=lines, mean_confidence=0.95)


async def _seed_user_and_capture(session: Any) -> tuple[int, Any]:
    from dailyloadout.infrastructure.db.models import User

    user = User(email=f"{uuid4().hex}@test.com", password_hash="h", display_name="T")
    session.add(user)
    await session.flush()
    capture = await CaptureRepository(session).create(user_id=user.id, input_type="library_import")
    return user.id, capture


# -- Processor ------------------------------------------------------------------


async def test_processor_creates_candidates_from_local_ocr() -> None:
    async with _TestSessionFactory() as session:
        user_id, capture = await _seed_user_and_capture(session)
        await process_library_import(
            capture,
            [b"Hollow Knight\nCeleste\nMystery Game Foo"],
            user_id=user_id,
            today=date(2026, 6, 24),
            capture_repo=CaptureRepository(session),
            candidate_repo=CaptureCandidateRepository(session),
            usage_repo=UsageCounterRepository(session),
            ocr_client=DummyOCRClient(),
            ocr_fallback_client=None,
            catalog_matcher=DummyCatalogMatcher(),
            settings=settings,
        )
        candidates = await CaptureCandidateRepository(session).get_all_for_capture(capture.id)
        titles = {c.title for c in candidates}
        assert "Hollow Knight" in titles  # matched + enriched
        assert "Mystery Game Foo" in titles  # echoed, unmatched
        assert capture.status == "review"


async def test_processor_escalates_low_confidence_to_vision() -> None:
    async with _TestSessionFactory() as session:
        user_id, capture = await _seed_user_and_capture(session)
        usage_repo = UsageCounterRepository(session)

        await process_library_import(
            capture,
            [b"__lowconf__\ngarbled"],  # primary OCR is low-confidence
            user_id=user_id,
            today=date(2026, 6, 24),
            capture_repo=CaptureRepository(session),
            candidate_repo=CaptureCandidateRepository(session),
            usage_repo=usage_repo,
            ocr_client=DummyOCRClient(),
            ocr_fallback_client=_StubFallbackOCR(["Hades", "Celeste"]),
            catalog_matcher=DummyCatalogMatcher(),
            settings=settings,
        )

        candidates = await CaptureCandidateRepository(session).get_all_for_capture(capture.id)
        titles = {c.title for c in candidates}
        assert titles == {"Hades", "Celeste"}  # fallback output replaced the garble
        # The vision fallback was metered.
        assert await usage_repo.get_count(user_id, VISION_FALLBACK_KEY, date(2026, 6, 24)) == 1


async def test_processor_respects_vision_fallback_cap() -> None:
    async with _TestSessionFactory() as session:
        user_id, capture = await _seed_user_and_capture(session)
        usage_repo = UsageCounterRepository(session)
        today = date(2026, 6, 24)
        # Pre-consume the entire vision budget for the day.
        await usage_repo.increment(
            user_id, VISION_FALLBACK_KEY, today, settings.library_import_vision_fallbacks_per_day
        )

        await process_library_import(
            capture,
            [b"__lowconf__\nKept Title"],
            user_id=user_id,
            today=today,
            capture_repo=CaptureRepository(session),
            candidate_repo=CaptureCandidateRepository(session),
            usage_repo=usage_repo,
            ocr_client=DummyOCRClient(),
            ocr_fallback_client=_StubFallbackOCR(["Should Not Appear"]),
            catalog_matcher=DummyCatalogMatcher(),
            settings=settings,
        )
        candidates = await CaptureCandidateRepository(session).get_all_for_capture(capture.id)
        # Fallback skipped (cap reached): the low-confidence primary line is kept.
        assert {c.title for c in candidates} == {"Kept Title"}


async def test_clean_title_strips_icon_noise() -> None:
    from dailyloadout.workers.library_import_processor import _clean_title

    assert _clean_title("▶ Hollow Knight") == "Hollow Knight"
    assert _clean_title("• Celeste") == "Celeste"
    assert _clean_title("  Hades  ") == "Hades"
    assert _clean_title("O Hollow Knight") == "Hollow Knight"  # icon misread as a letter
    # Inner punctuation is preserved.
    assert _clean_title("S.T.A.L.K.E.R.") == "S.T.A.L.K.E.R"


async def test_processor_cleans_icon_prefixed_titles() -> None:
    async with _TestSessionFactory() as session:
        user_id, capture = await _seed_user_and_capture(session)
        await process_library_import(
            capture,
            ["▶ Unknown Indie Game".encode()],
            user_id=user_id,
            today=date(2026, 6, 24),
            capture_repo=CaptureRepository(session),
            candidate_repo=CaptureCandidateRepository(session),
            usage_repo=UsageCounterRepository(session),
            ocr_client=DummyOCRClient(),
            ocr_fallback_client=None,
            catalog_matcher=DummyCatalogMatcher(),
            settings=settings,
        )
        candidates = await CaptureCandidateRepository(session).get_all_for_capture(capture.id)
        assert {c.title for c in candidates} == {"Unknown Indie Game"}


async def test_processor_no_titles_marks_review() -> None:
    async with _TestSessionFactory() as session:
        user_id, capture = await _seed_user_and_capture(session)
        await process_library_import(
            capture,
            [b"   \n123\n!!"],  # nothing meaningful
            user_id=user_id,
            today=date(2026, 6, 24),
            capture_repo=CaptureRepository(session),
            candidate_repo=CaptureCandidateRepository(session),
            usage_repo=UsageCounterRepository(session),
            ocr_client=DummyOCRClient(),
            ocr_fallback_client=None,
            catalog_matcher=DummyCatalogMatcher(),
            settings=settings,
        )
        assert capture.status == "review"
        candidates = await CaptureCandidateRepository(session).get_all_for_capture(capture.id)
        assert candidates == []


# -- Endpoints ------------------------------------------------------------------


def _image_files(*payloads: str) -> list[tuple[str, tuple[str, bytes, str]]]:
    return [
        ("files", (f"shot{i}.png", p.encode("utf-8"), "image/png")) for i, p in enumerate(payloads)
    ]


class TestLibraryImportEndpoint:
    async def test_import_returns_candidates(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await async_client.post(
            "/v1/captures/library-import",
            files=_image_files("Hollow Knight\nCeleste\nHades\nMystery Foo"),
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["input_type"] == "library_import"
        assert body["status"] == "review"
        titles = {c["title"] for c in body["candidates"]}
        assert {"Hollow Knight", "Celeste", "Hades", "Mystery Foo"} <= titles

    async def test_import_requires_an_image(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await async_client.post("/v1/captures/library-import", headers=auth_headers)
        assert resp.status_code == 422

    async def test_import_rejects_non_image(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await async_client.post(
            "/v1/captures/library-import",
            files=[("files", ("notes.txt", b"Hollow Knight", "text/plain"))],
            headers=auth_headers,
        )
        assert resp.status_code == 400

    async def test_import_daily_cap_returns_429(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        monkeypatch: Any,
    ) -> None:
        monkeypatch.setattr(settings, "library_import_images_per_day", 1)
        resp = await async_client.post(
            "/v1/captures/library-import",
            files=_image_files("Hollow Knight", "Celeste"),  # 2 images > cap of 1
            headers=auth_headers,
        )
        assert resp.status_code == 429

    async def test_bulk_confirm_commits_and_rejects(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        imported = (
            await async_client.post(
                "/v1/captures/library-import",
                files=_image_files("Hollow Knight\nCeleste\nHades"),
                headers=auth_headers,
            )
        ).json()
        candidates = imported["candidates"]
        assert len(candidates) == 3
        confirm_ids = [candidates[0]["public_id"], candidates[1]["public_id"]]

        resp = await async_client.post(
            f"/v1/captures/{imported['public_id']}/candidates/bulk-confirm",
            json={"confirm_public_ids": confirm_ids, "platform_id": seed_platforms[0]["id"]},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"confirmed": 2, "rejected": 1}

        # The two confirmed games are now in the library.
        library = (await async_client.get("/v1/library", headers=auth_headers)).json()
        assert library["total"] == 2

    async def test_bulk_confirm_applies_title_override(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        imported = (
            await async_client.post(
                "/v1/captures/library-import",
                files=_image_files("Celeste"),
                headers=auth_headers,
            )
        ).json()
        candidate = imported["candidates"][0]

        resp = await async_client.post(
            f"/v1/captures/{imported['public_id']}/candidates/bulk-confirm",
            json={
                "confirm_public_ids": [candidate["public_id"]],
                "platform_id": seed_platforms[0]["id"],
                "title_overrides": {candidate["public_id"]: "Celeste Classic"},
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["confirmed"] == 1

        library = (await async_client.get("/v1/library", headers=auth_headers)).json()
        titles = {item["game"]["title"] for item in library["items"]}
        assert "Celeste Classic" in titles

    async def test_duplicates_flags_already_owned_games(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        platform_a = seed_platforms[0]["id"]
        platform_b = seed_platforms[1]["id"]

        # Import + commit "Hades" on platform A.
        first = (
            await async_client.post(
                "/v1/captures/library-import",
                files=_image_files("Hades"),
                headers=auth_headers,
            )
        ).json()
        await async_client.post(
            f"/v1/captures/{first['public_id']}/candidates/bulk-confirm",
            json={
                "confirm_public_ids": [first["candidates"][0]["public_id"]],
                "platform_id": platform_a,
            },
            headers=auth_headers,
        )

        # A second import containing "Hades" again.
        second = (
            await async_client.post(
                "/v1/captures/library-import",
                files=_image_files("Hades\nCeleste"),
                headers=auth_headers,
            )
        ).json()
        hades = next(c for c in second["candidates"] if c["title"] == "Hades")

        # On platform A it's a duplicate; on platform B it isn't.
        dup_a = (
            await async_client.get(
                f"/v1/captures/{second['public_id']}/candidates/duplicates",
                params={"platform_id": platform_a},
                headers=auth_headers,
            )
        ).json()
        assert dup_a["duplicate_public_ids"] == [hades["public_id"]]

        dup_b = (
            await async_client.get(
                f"/v1/captures/{second['public_id']}/candidates/duplicates",
                params={"platform_id": platform_b},
                headers=auth_headers,
            )
        ).json()
        assert dup_b["duplicate_public_ids"] == []

    async def test_bulk_confirm_unknown_platform_404(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        imported = (
            await async_client.post(
                "/v1/captures/library-import",
                files=_image_files("Hades"),
                headers=auth_headers,
            )
        ).json()
        resp = await async_client.post(
            f"/v1/captures/{imported['public_id']}/candidates/bulk-confirm",
            json={"confirm_public_ids": [], "platform_id": 99999},
            headers=auth_headers,
        )
        assert resp.status_code == 404
