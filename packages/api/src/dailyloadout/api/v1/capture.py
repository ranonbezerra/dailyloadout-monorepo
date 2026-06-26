"""Capture API endpoints: text capture, voice transcription, candidate review."""

from __future__ import annotations

import os
import tempfile
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status

from dailyloadout.api.v1._cost_guard import cost_guard
from dailyloadout.api.v1._mime_helpers import guess_audio_extension
from dailyloadout.api.v1._rate_limit import rate_limit
from dailyloadout.config import settings
from dailyloadout.core.capture.exceptions import InvalidUploadError
from dailyloadout.core.capture.ingestion import read_upload_capped
from dailyloadout.core.capture.schemas import (
    CandidateConfirmRequest,
    CaptureListItem,
    CaptureListResponse,
    CaptureResponse,
    CaptureTextRequest,
    TranscribeResponse,
)
from dailyloadout.core.library.schemas import LibraryEntryResponse
from dailyloadout.deps import CaptureServiceDep, CurrentUserDep, RequireVerifiedUserDep
from dailyloadout.deps.capture import STTClientDep
from dailyloadout.infrastructure.stt.concurrency import get_stt_semaphore

router = APIRouter(prefix="/v1/captures", tags=["captures"])

# Per-user limiter on the LLM/IGDB capture-submit routes (text + photo). Each
# submission runs an LLM extraction plus IGDB lookups, so it's the expensive
# capture surface to bound per account.
_capture_submit_rate_limit = Depends(
    rate_limit(
        "capture_submit",
        settings.rate_limit_capture_submit_per_minute,
        60,
        by="user",
        fail_closed=True,
    )
)

# Aggregate $ cost kill-switch for the LLM/vision/STT capture routes.
_capture_cost_guard = Depends(cost_guard("capture"))


# ---------------------------------------------------------------------------
# Text capture
# ---------------------------------------------------------------------------


@router.post(
    "/text",
    response_model=CaptureResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_capture_submit_rate_limit, _capture_cost_guard],
)
async def submit_text_capture(
    body: CaptureTextRequest,
    current_user: RequireVerifiedUserDep,
    capture_service: CaptureServiceDep,
) -> CaptureResponse:
    """Submit a text capture, process it inline (LLM + IGDB), and return candidates.

    NOTE: Processing is done inline for now. This will move to background
    processing via arq once the task queue is fully wired.
    """
    capture = await capture_service.submit_and_process_text(
        user_id=current_user.id,
        raw_text=body.raw_text,
        input_type=body.input_type,
    )
    return CaptureResponse.model_validate(capture)


# ---------------------------------------------------------------------------
# Photo capture
# ---------------------------------------------------------------------------


@router.post(
    "/photo",
    response_model=CaptureResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_capture_submit_rate_limit, _capture_cost_guard],
)
async def submit_photo_capture(
    file: UploadFile,
    current_user: RequireVerifiedUserDep,
    capture_service: CaptureServiceDep,
) -> CaptureResponse:
    """Submit a photo capture, process it inline (vision LLM + IGDB), and return candidates."""
    max_bytes = settings.capture_max_image_mb * 1024 * 1024
    try:
        # Reject oversized uploads before fully buffering them into memory.
        contents = await read_upload_capped(
            file,
            max_bytes,
            too_large_message=f"Image file must be under {settings.capture_max_image_mb}MB.",
        )
        capture = await capture_service.submit_and_process_photo(
            user_id=current_user.id,
            contents=contents,
            content_type=file.content_type,
        )
    except InvalidUploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CaptureResponse.model_validate(capture)


@router.post(
    "/transcribe",
    response_model=TranscribeResponse,
    dependencies=[_capture_submit_rate_limit, _capture_cost_guard],
)
async def transcribe_audio(
    file: UploadFile,
    current_user: RequireVerifiedUserDep,
    stt_client: STTClientDep,
) -> TranscribeResponse:
    """Transcribe an audio file and return the text for user review.

    The user can then edit the transcribed text and submit it via the
    ``POST /v1/captures/text`` endpoint with ``input_type="voice"``.
    """
    # Validate MIME type.
    if not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="File must be an audio file.")

    # Validate file size BEFORE buffering the whole file into memory.
    max_size = settings.capture_max_audio_mb * 1024 * 1024
    too_large = f"Audio file must be under {settings.capture_max_audio_mb}MB."
    try:
        contents = await read_upload_capped(file, max_size, too_large_message=too_large)
    except InvalidUploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if stt_client is None:
        raise HTTPException(status_code=503, detail="Speech-to-text service is not available.")

    # Save file temporarily for transcription.
    upload_dir = settings.capture_upload_dir
    os.makedirs(upload_dir, exist_ok=True)

    suffix = guess_audio_extension(file.content_type)
    with tempfile.NamedTemporaryFile(dir=upload_dir, suffix=suffix, delete=False) as tmp:
        tmp.write(contents)
        audio_path = tmp.name

    try:
        # Bound concurrent transcriptions (process-wide) so a burst can't thrash
        # the host, mirroring the Ollama concurrency semaphore.
        async with get_stt_semaphore():
            result = await stt_client.transcribe(audio_path)
        # Enforce the configured audio-length ceiling on the decoded duration.
        max_seconds = settings.capture_max_audio_seconds
        if result.duration_seconds is not None and result.duration_seconds > max_seconds:
            raise HTTPException(
                status_code=422,
                detail=f"Audio must be under {max_seconds} seconds.",
            )
        return TranscribeResponse(
            text=result.text,
            language=result.language,
            duration_seconds=result.duration_seconds,
        )
    finally:
        # Always clean up the temp file.
        if os.path.exists(audio_path):
            os.unlink(audio_path)


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
    """List the current user's captures."""
    captures, total = await capture_service.list_captures(
        user_id=current_user.id,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )
    items = []
    for c in captures:
        item = CaptureListItem.model_validate(c)
        item.candidate_titles = [cand.igdb_title or cand.title for cand in c.candidates]
        items.append(item)
    return CaptureListResponse(items=items, total=total)


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
