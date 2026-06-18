"""Capture API endpoints: text capture, candidate review, and library commit."""

from uuid import UUID

from fastapi import APIRouter, Query, status

from dailyloadout.core.capture.schemas import (
    CandidateConfirmRequest,
    CaptureListItem,
    CaptureListResponse,
    CaptureResponse,
    CaptureTextRequest,
)
from dailyloadout.core.library.schemas import LibraryEntryResponse
from dailyloadout.deps import CurrentUserDep
from dailyloadout.deps.capture import (
    CaptureCandidateRepoDep,
    CaptureRepoDep,
    CaptureServiceDep,
    IGDBClientDep,
    LLMClientDep,
)
from dailyloadout.workers.capture_processor import process_capture

router = APIRouter(prefix="/v1/captures", tags=["captures"])


# ---------------------------------------------------------------------------
# Text capture
# ---------------------------------------------------------------------------


@router.post(
    "/text",
    response_model=CaptureResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_text_capture(
    body: CaptureTextRequest,
    current_user: CurrentUserDep,
    capture_service: CaptureServiceDep,
    capture_repo: CaptureRepoDep,
    candidate_repo: CaptureCandidateRepoDep,
    llm_client: LLMClientDep,
    igdb_client: IGDBClientDep,
) -> CaptureResponse:
    """Submit a text capture, process it inline (LLM + IGDB), and return candidates.

    NOTE: Processing is done inline for now. This will move to background
    processing via arq once the task queue is fully wired.
    """
    capture = await capture_service.submit_text(
        user_id=current_user.id,
        raw_text=body.raw_text,
    )

    # Process inline (will become arq job later).
    await process_capture(
        capture=capture,
        capture_repo=capture_repo,
        candidate_repo=candidate_repo,
        llm_client=llm_client,
        igdb_client=igdb_client,
    )

    # Re-fetch with candidates eagerly loaded.
    capture = await capture_service.get_capture(current_user.id, capture.public_id)
    return CaptureResponse.model_validate(capture)


# ---------------------------------------------------------------------------
# Capture listing and detail
# ---------------------------------------------------------------------------


@router.get("", response_model=CaptureListResponse)
async def list_captures(
    current_user: CurrentUserDep,
    capture_service: CaptureServiceDep,
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> CaptureListResponse:
    """List the current user's captures (without candidates)."""
    captures, total = await capture_service.list_captures(
        user_id=current_user.id,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )
    return CaptureListResponse(
        items=[CaptureListItem.model_validate(c) for c in captures],
        total=total,
    )


@router.get("/{public_id}", response_model=CaptureResponse)
async def get_capture(
    public_id: UUID,
    current_user: CurrentUserDep,
    capture_service: CaptureServiceDep,
) -> CaptureResponse:
    """Get a single capture with its candidates."""
    capture = await capture_service.get_capture(current_user.id, public_id)
    return CaptureResponse.model_validate(capture)


# ---------------------------------------------------------------------------
# Candidate actions
# ---------------------------------------------------------------------------


@router.post(
    "/{public_id}/candidates/{candidate_id}/confirm",
    response_model=LibraryEntryResponse,
)
async def confirm_candidate(
    public_id: UUID,
    candidate_id: UUID,
    body: CandidateConfirmRequest,
    current_user: CurrentUserDep,
    capture_service: CaptureServiceDep,
) -> LibraryEntryResponse:
    """Confirm a candidate and add it to the user's library."""
    entry = await capture_service.confirm_candidate(
        user_id=current_user.id,
        capture_public_id=public_id,
        candidate_public_id=candidate_id,
        platform_id=body.platform_id,
        library_status=body.status,
    )
    return LibraryEntryResponse.model_validate(entry)


@router.post(
    "/{public_id}/candidates/{candidate_id}/reject",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def reject_candidate(
    public_id: UUID,
    candidate_id: UUID,
    current_user: CurrentUserDep,
    capture_service: CaptureServiceDep,
) -> None:
    """Reject a candidate."""
    await capture_service.reject_candidate(
        user_id=current_user.id,
        capture_public_id=public_id,
        candidate_public_id=candidate_id,
    )
