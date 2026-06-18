"""Capture API endpoints: text capture, voice transcription, candidate review."""

from __future__ import annotations

import os
import tempfile
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, UploadFile, status

from dailyloadout.config import settings
from dailyloadout.core.capture.schemas import (
    CandidateConfirmRequest,
    CaptureListItem,
    CaptureListResponse,
    CaptureResponse,
    CaptureTextRequest,
    TranscribeResponse,
)
from dailyloadout.core.library.schemas import LibraryEntryResponse
from dailyloadout.deps import CurrentUserDep
from dailyloadout.deps.capture import (
    CaptureCandidateRepoDep,
    CaptureRepoDep,
    CaptureServiceDep,
    IGDBClientDep,
    LLMClientDep,
    STTClientDep,
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
        input_type=body.input_type,
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
# Photo capture
# ---------------------------------------------------------------------------


@router.post(
    "/photo",
    response_model=CaptureResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_photo_capture(
    file: UploadFile,
    current_user: CurrentUserDep,
    capture_service: CaptureServiceDep,
    capture_repo: CaptureRepoDep,
    candidate_repo: CaptureCandidateRepoDep,
    llm_client: LLMClientDep,
    igdb_client: IGDBClientDep,
) -> CaptureResponse:
    """Submit a photo capture, process it inline (vision LLM + IGDB), and return candidates."""
    # Validate MIME type.
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")

    # Validate file size.
    max_size = settings.capture_max_image_mb * 1024 * 1024
    contents = await file.read()
    if len(contents) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"Image file must be under {settings.capture_max_image_mb}MB.",
        )

    # Save file to temp location.
    upload_dir = settings.capture_upload_dir
    os.makedirs(upload_dir, exist_ok=True)

    ext = _guess_image_extension(file.content_type)
    with tempfile.NamedTemporaryFile(dir=upload_dir, suffix=ext, delete=False) as tmp:
        tmp.write(contents)
        image_path = tmp.name

    capture = await capture_service.submit_photo(
        user_id=current_user.id,
        image_path=image_path,
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


def _guess_image_extension(content_type: str | None) -> str:
    """Map an image MIME type to a file extension."""
    mapping = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/bmp": ".bmp",
        "image/tiff": ".tiff",
        "image/heic": ".heic",
        "image/heif": ".heif",
    }
    return mapping.get(content_type or "", ".jpg")


# ---------------------------------------------------------------------------
# Voice transcription (STT only — returns text for user review)
# ---------------------------------------------------------------------------


def _guess_extension(content_type: str | None) -> str:
    """Map an audio MIME type to a file extension."""
    mapping = {
        "audio/webm": ".webm",
        "audio/mp4": ".m4a",
        "audio/mpeg": ".mp3",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/ogg": ".ogg",
        "audio/flac": ".flac",
    }
    return mapping.get(content_type or "", ".wav")


@router.post(
    "/transcribe",
    response_model=TranscribeResponse,
)
async def transcribe_audio(
    file: UploadFile,
    current_user: CurrentUserDep,  # noqa: ARG001
    stt_client: STTClientDep,
) -> TranscribeResponse:
    """Transcribe an audio file and return the text for user review.

    The user can then edit the transcribed text and submit it via the
    ``POST /v1/captures/text`` endpoint with ``input_type="voice"``.
    """
    # Validate MIME type.
    if file.content_type and not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="File must be an audio file.")

    # Validate file size (5 MB max).
    max_size = 5 * 1024 * 1024
    contents = await file.read()
    if len(contents) > max_size:
        raise HTTPException(status_code=400, detail="Audio file must be under 5MB.")

    if stt_client is None:
        raise HTTPException(status_code=503, detail="Speech-to-text service is not available.")

    # Save file temporarily for transcription.
    upload_dir = settings.capture_upload_dir
    os.makedirs(upload_dir, exist_ok=True)

    suffix = _guess_extension(file.content_type)
    with tempfile.NamedTemporaryFile(dir=upload_dir, suffix=suffix, delete=False) as tmp:
        tmp.write(contents)
        audio_path = tmp.name

    try:
        result = await stt_client.transcribe(audio_path)
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
