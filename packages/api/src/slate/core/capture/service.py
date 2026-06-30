"""Capture service: submission, candidate management, and library integration."""

from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from fastapi import HTTPException, status

from slate.config import Settings
from slate.config import settings as default_settings
from slate.core.capture import candidates
from slate.core.capture.ingestion import (
    enforce_import_quota,
    meter_import,
    temp_image_file,
    validate_image,
    validate_import_image,
)
from slate.core.capture.ports import (
    CaptureProcessor,
    LibraryImportProcessor,
)
from slate.core.library.igdb_budget import igdb_budget_allows
from slate.core.safety.guard import sanitize_and_audit
from slate.infrastructure.catalog.base import AbstractCatalogMatcher
from slate.infrastructure.db.models import Capture, CaptureCandidate, LibraryEntry
from slate.infrastructure.db.repositories.capture import (
    CaptureCandidateRepository,
    CaptureRepository,
)
from slate.infrastructure.db.repositories.game import GameRepository
from slate.infrastructure.db.repositories.library import LibraryRepository
from slate.infrastructure.db.repositories.platform import PlatformRepository
from slate.infrastructure.db.repositories.usage import UsageCounterRepository
from slate.infrastructure.igdb.base import IGDBSearchClient
from slate.infrastructure.llm.base import AbstractLLMClient
from slate.infrastructure.ocr.base import AbstractOCRClient


class CaptureService:
    """Orchestrates capture submission, candidate review, and library commits.

    Ingestion collaborators (LLM/IGDB/OCR clients, the worker pipelines, the
    usage repo and catalog matcher) are injected so the routers only parse input
    and delegate. They are optional because the candidate-review methods do not
    need them; the submission methods that do will raise if they are missing.
    """

    def __init__(
        self,
        capture_repo: CaptureRepository,
        candidate_repo: CaptureCandidateRepository,
        game_repo: GameRepository,
        library_repo: LibraryRepository,
        platform_repo: PlatformRepository,
        *,
        usage_repo: UsageCounterRepository | None = None,
        llm_client: AbstractLLMClient | None = None,
        igdb_client: IGDBSearchClient | None = None,
        ocr_client: AbstractOCRClient | None = None,
        ocr_fallback_client: AbstractOCRClient | None = None,
        catalog_matcher: AbstractCatalogMatcher | None = None,
        process_capture: CaptureProcessor | None = None,
        process_library_import: LibraryImportProcessor | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._capture_repo = capture_repo
        self._candidate_repo = candidate_repo
        self._game_repo = game_repo
        self._library_repo = library_repo
        self._platform_repo = platform_repo
        self._usage_repo = usage_repo
        self._llm_client = llm_client
        self._igdb_client = igdb_client
        self._ocr_client = ocr_client
        self._ocr_fallback_client = ocr_fallback_client
        self._catalog_matcher = catalog_matcher
        self._process_capture = process_capture
        self._process_library_import = process_library_import
        self._settings = settings or default_settings

    async def submit_text(self, user_id: int, raw_text: str, input_type: str = "text") -> Capture:
        """Create a new capture with status ``queued`` (untrusted text sanitized + audited)."""
        return await self._capture_repo.create(
            user_id=user_id,
            input_type=input_type,
            raw_text=sanitize_and_audit(raw_text, surface="capture", user_id=user_id),
        )

    async def submit_photo(self, user_id: int, image_path: str) -> Capture:
        """Create a capture from a photo."""
        return await self._capture_repo.create(
            user_id=user_id,
            input_type="photo",
            image_path=image_path,
        )

    async def _igdb_for(self, user_id: int) -> IGDBSearchClient | None:
        """The IGDB client, or None when the user's per-day budget is spent (fail-open)."""
        if self._igdb_client is None or not await igdb_budget_allows(user_id):
            return None
        return self._igdb_client

    async def submit_and_process_text(
        self,
        user_id: int,
        raw_text: str,
        input_type: str = "text",
    ) -> Capture:
        """Persist a text capture, run the inline pipeline, and return it loaded."""
        assert self._process_capture is not None and self._llm_client is not None
        capture = await self.submit_text(user_id, raw_text, input_type)
        await self._process_capture(
            capture=capture,
            capture_repo=self._capture_repo,
            candidate_repo=self._candidate_repo,
            llm_client=self._llm_client,
            igdb_client=await self._igdb_for(user_id),
        )
        return await self.get_capture(user_id, capture.public_id)

    async def submit_and_process_photo(
        self,
        user_id: int,
        contents: bytes,
        content_type: str | None,
    ) -> Capture:
        """Validate, persist (with a temp file), process, and return a photo capture."""
        assert self._process_capture is not None and self._llm_client is not None
        validate_image(content_type, len(contents), self._settings, data=contents)
        with temp_image_file(contents, content_type, self._settings) as image_path:
            capture = await self.submit_photo(user_id=user_id, image_path=image_path)
            await self._process_capture(
                capture=capture,
                capture_repo=self._capture_repo,
                candidate_repo=self._candidate_repo,
                llm_client=self._llm_client,
                igdb_client=await self._igdb_for(user_id),
            )
            return await self.get_capture(user_id, capture.public_id)

    async def check_import_quota(self, user_id: int, file_count: int) -> None:
        """Reject a bulk import (count cap + per-day quota) before buffering files."""
        assert self._usage_repo is not None
        await enforce_import_quota(
            user_id, file_count, usage_repo=self._usage_repo, settings=self._settings
        )

    async def submit_library_import(
        self,
        user_id: int,
        files: list[tuple[str | None, bytes]],
    ) -> Capture:
        """Validate and meter a bulk import (a list of ``(content_type, contents)``),
        run the pipeline, and return it loaded. Raises ``InvalidUploadError`` /
        ``ImportQuotaExceededError`` on bad uploads / the per-day cap.
        """
        assert self._process_library_import is not None
        assert self._usage_repo is not None
        assert self._ocr_client is not None
        assert self._catalog_matcher is not None

        blobs: list[bytes] = []
        for content_type, contents in files:
            validate_import_image(content_type, len(contents), self._settings, data=contents)
            blobs.append(contents)

        # Authoritative atomic meter against the per-day cap (closes the TOCTOU
        # race the router's pre-buffer ``check_import_quota`` read cannot).
        today = await meter_import(
            user_id, len(blobs), usage_repo=self._usage_repo, settings=self._settings
        )

        capture = await self._capture_repo.create(user_id=user_id, input_type="library_import")
        await self._process_library_import(
            capture,
            blobs,
            user_id=user_id,
            today=today,
            capture_repo=self._capture_repo,
            candidate_repo=self._candidate_repo,
            usage_repo=self._usage_repo,
            ocr_client=self._ocr_client,
            ocr_fallback_client=self._ocr_fallback_client,
            catalog_matcher=self._catalog_matcher,
            settings=self._settings,
        )
        return await self.get_capture(user_id, capture.public_id)

    async def get_capture(self, user_id: int, capture_public_id: UUID) -> Capture:
        """Return a capture scoped to *user_id*, or raise 404."""
        capture = await self._capture_repo.get_by_public_id(capture_public_id, user_id=user_id)
        if capture is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Capture not found",
            )
        return capture

    async def rematch_candidate(
        self,
        user_id: int,
        capture_public_id: UUID,
        candidate_public_id: UUID,
        title: str,
    ) -> CaptureCandidate:
        """Re-search IGDB for one candidate with a user-corrected title."""
        assert self._catalog_matcher is not None
        capture = await self.get_capture(user_id, capture_public_id)
        return await candidates.rematch_candidate(
            user_id=user_id,
            capture=capture,
            candidate_public_id=candidate_public_id,
            title=title,
            candidate_repo=self._candidate_repo,
            catalog_matcher=self._catalog_matcher,
        )

    async def list_captures(
        self,
        user_id: int,
        status_filter: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Capture], int]:
        """Return the user's captures along with the total count."""
        captures = await self._capture_repo.list_for_user(
            user_id,
            status=status_filter,
            limit=limit,
            offset=offset,
        )
        total = await self._capture_repo.count_for_user(user_id, status=status_filter)
        return captures, total

    async def confirm_candidate(
        self,
        user_id: int,
        capture_public_id: UUID,
        candidate_public_id: UUID,
        platform_id: int,
        library_status: str = "backlog",
    ) -> LibraryEntry:
        """Confirm a candidate: create a library entry and mark it confirmed."""
        capture = await self.get_capture(user_id, capture_public_id)
        return await candidates.confirm_candidate(
            user_id=user_id,
            capture=capture,
            candidate_public_id=candidate_public_id,
            platform_id=platform_id,
            library_status=library_status,
            candidate_repo=self._candidate_repo,
            capture_repo=self._capture_repo,
            game_repo=self._game_repo,
            library_repo=self._library_repo,
            platform_repo=self._platform_repo,
        )

    async def bulk_confirm_candidates(
        self,
        user_id: int,
        capture_public_id: UUID,
        confirm_public_ids: list[UUID],
        platform_id: int,
        library_status: str = "backlog",
        title_overrides: dict[UUID, str] | None = None,
        status_overrides: Mapping[UUID, str] | None = None,
    ) -> tuple[int, int]:
        """Confirm the listed candidates and reject the rest, in one call."""
        capture = await self.get_capture(user_id, capture_public_id)
        return await candidates.bulk_confirm_candidates(
            user_id=user_id,
            capture=capture,
            confirm_public_ids=confirm_public_ids,
            platform_id=platform_id,
            library_status=library_status,
            title_overrides=title_overrides,
            status_overrides=status_overrides,
            candidate_repo=self._candidate_repo,
            capture_repo=self._capture_repo,
            game_repo=self._game_repo,
            library_repo=self._library_repo,
            platform_repo=self._platform_repo,
        )

    async def reject_candidate(
        self,
        user_id: int,
        capture_public_id: UUID,
        candidate_public_id: UUID,
    ) -> None:
        """Reject a candidate."""
        capture = await self.get_capture(user_id, capture_public_id)
        await candidates.reject_candidate(
            capture=capture,
            candidate_public_id=candidate_public_id,
            candidate_repo=self._candidate_repo,
            capture_repo=self._capture_repo,
        )
