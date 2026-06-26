"""Bulk library-import endpoints: multi-image OCR ingestion + bulk confirm.

Kept separate from the single-capture router (``capture.py``) — it owns a new
OCR/catalog/usage surface and the batch confirm flow (ROADMAP Epic 14).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, UploadFile, status

from dailyloadout.core.capture.duplicates import find_duplicate_candidate_ids
from dailyloadout.core.capture.exceptions import ImportQuotaExceededError, InvalidUploadError
from dailyloadout.core.capture.schemas import (
    BulkConfirmRequest,
    BulkConfirmResponse,
    CaptureResponse,
    DuplicatesResponse,
)
from dailyloadout.deps import CaptureServiceDep, CurrentUserDep
from dailyloadout.deps.library import GameRepoDep, LibraryRepoDep

router = APIRouter(prefix="/v1/captures", tags=["captures"])


@router.post(
    "/library-import",
    response_model=CaptureResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_library_import(
    current_user: CurrentUserDep,
    capture_service: CaptureServiceDep,
    files: list[UploadFile],
) -> CaptureResponse:
    """Bulk-import a library from one or more list-view screenshots.

    Local OCR reads each image (escalating only noisy ones to the vision
    fallback), titles are repaired against the catalog, and a batch of
    candidates is returned for confirmation. 422 if no images, 429 if the
    per-day import cap is exceeded.
    """
    if not files:
        raise HTTPException(status_code=422, detail="At least one image is required.")

    uploads = [(file.content_type, await file.read()) for file in files]
    try:
        capture = await capture_service.submit_library_import(
            user_id=current_user.id,
            files=uploads,
        )
    except InvalidUploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ImportQuotaExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from exc
    return CaptureResponse.model_validate(capture)


@router.get(
    "/{public_id}/candidates/duplicates",
    response_model=DuplicatesResponse,
)
async def check_candidate_duplicates(
    public_id: UUID,
    current_user: CurrentUserDep,
    capture_service: CaptureServiceDep,
    game_repo: GameRepoDep,
    library_repo: LibraryRepoDep,
    platform_id: int = Query(...),
) -> DuplicatesResponse:
    """List candidates already in the user's library for *platform_id*.

    Advisory only — lets the import UI warn before adding. The same game on a
    different platform is not flagged.
    """
    capture = await capture_service.get_capture(current_user.id, public_id)
    duplicate_ids = await find_duplicate_candidate_ids(
        candidates=capture.candidates,
        game_repo=game_repo,
        library_repo=library_repo,
        user_id=current_user.id,
        platform_id=platform_id,
    )
    return DuplicatesResponse(duplicate_public_ids=duplicate_ids)


@router.post(
    "/{public_id}/candidates/bulk-confirm",
    response_model=BulkConfirmResponse,
)
async def bulk_confirm_candidates(
    public_id: UUID,
    body: BulkConfirmRequest,
    current_user: CurrentUserDep,
    capture_service: CaptureServiceDep,
) -> BulkConfirmResponse:
    """Confirm the selected candidates and reject the rest, in one call.

    Commits a whole library import (50-100 titles) at once: the listed
    candidates become library entries on *platform_id*; every other pending
    candidate is rejected.
    """
    confirmed, rejected = await capture_service.bulk_confirm_candidates(
        user_id=current_user.id,
        capture_public_id=public_id,
        confirm_public_ids=body.confirm_public_ids,
        platform_id=body.platform_id,
        library_status=body.status,
        title_overrides=body.title_overrides,
    )
    return BulkConfirmResponse(confirmed=confirmed, rejected=rejected)
