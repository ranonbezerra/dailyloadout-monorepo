"""Tests for the voice capture flow: transcribe + submit text with input_type=voice."""

from __future__ import annotations

import io
from typing import Any

from httpx import AsyncClient

# =====================================================================
# Helpers
# =====================================================================


def _make_audio_file(size: int = 1024) -> io.BytesIO:
    """Create a minimal in-memory audio file for upload tests."""
    buf = io.BytesIO(b"\x00" * size)
    buf.name = "test.wav"
    return buf


async def _transcribe(
    client: AsyncClient,
    headers: dict[str, str],
    audio_file: io.BytesIO | None = None,
    content_type: str = "audio/wav",
    filename: str = "test.wav",
) -> Any:
    """Upload audio for transcription and return the httpx response."""
    if audio_file is None:
        audio_file = _make_audio_file()
    return await client.post(
        "/v1/captures/transcribe",
        files={"file": (filename, audio_file, content_type)},
        headers=headers,
    )


# =====================================================================
# Test: Transcribe endpoint
# =====================================================================


class TestTranscribeAudio:
    async def test_transcribe_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        resp = await _transcribe(async_client, auth_headers)
        assert resp.status_code == 200, resp.text

        data = resp.json()
        assert "text" in data
        assert len(data["text"]) > 0
        assert data["language"] is not None
        assert data["duration_seconds"] is not None

    async def test_transcribe_invalid_mime(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        buf = io.BytesIO(b"not audio data")
        resp = await _transcribe(
            async_client,
            auth_headers,
            audio_file=buf,
            content_type="text/plain",
            filename="test.txt",
        )
        assert resp.status_code == 400
        assert "audio" in resp.json()["detail"].lower()

    async def test_transcribe_too_large(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        # 6 MB file (exceeds 5 MB limit).
        large_file = _make_audio_file(size=6 * 1024 * 1024)
        resp = await _transcribe(async_client, auth_headers, audio_file=large_file)
        assert resp.status_code == 400
        assert "5MB" in resp.json()["detail"]

    async def test_transcribe_unauthorized(
        self,
        async_client: AsyncClient,
    ) -> None:
        audio_file = _make_audio_file()
        resp = await async_client.post(
            "/v1/captures/transcribe",
            files={"file": ("test.wav", audio_file, "audio/wav")},
        )
        assert resp.status_code == 401

    async def test_transcribe_rejects_over_max_audio_seconds(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """A transcription longer than capture_max_audio_seconds is rejected 422."""
        from dailyloadout.config import settings
        from dailyloadout.deps.capture import get_stt_client_dep
        from dailyloadout.infrastructure.stt.base import TranscriptionResult
        from dailyloadout.main import app

        class _LongSTT:
            async def transcribe(
                self, audio_path: str, language: str = "pt"
            ) -> TranscriptionResult:
                return TranscriptionResult(
                    text="x",
                    language="en",
                    duration_seconds=settings.capture_max_audio_seconds + 1,
                )

        app.dependency_overrides[get_stt_client_dep] = lambda: _LongSTT()
        try:
            resp = await _transcribe(async_client, auth_headers)
        finally:
            del app.dependency_overrides[get_stt_client_dep]
        assert resp.status_code == 422
        assert "seconds" in resp.json()["detail"].lower()


# =====================================================================
# Test: Full voice flow (transcribe → submit text with input_type=voice)
# =====================================================================


class TestVoiceCaptureFlow:
    async def test_transcribe_then_submit_as_voice(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """The full voice flow: transcribe audio, then submit the text."""
        # Step 1: Transcribe.
        resp = await _transcribe(async_client, auth_headers)
        assert resp.status_code == 200
        transcribed_text = resp.json()["text"]

        # Step 2: Submit as voice-originated text capture.
        resp = await async_client.post(
            "/v1/captures/text",
            json={"raw_text": transcribed_text, "input_type": "voice"},
            headers=auth_headers,
        )
        assert resp.status_code == 201

        data = resp.json()
        assert data["input_type"] == "voice"
        assert data["raw_text"] == transcribed_text
        assert data["status"] == "review"
        assert len(data["candidates"]) >= 1

    async def test_voice_capture_has_candidates(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """DummySTT returns 'got Hollow Knight and Hades for the Switch',
        which DummyLLM should parse into Hollow Knight and Hades candidates.
        """
        resp = await _transcribe(async_client, auth_headers)
        transcribed_text = resp.json()["text"]

        resp = await async_client.post(
            "/v1/captures/text",
            json={"raw_text": transcribed_text, "input_type": "voice"},
            headers=auth_headers,
        )
        assert resp.status_code == 201

        data = resp.json()
        titles = {c["title"] for c in data["candidates"]}
        assert "Hollow Knight" in titles
        assert "Hades" in titles

        for candidate in data["candidates"]:
            assert candidate["status"] == "pending"
            assert candidate["confidence"] is not None

    async def test_voice_capture_appears_in_list(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        resp = await _transcribe(async_client, auth_headers)
        transcribed_text = resp.json()["text"]

        resp = await async_client.post(
            "/v1/captures/text",
            json={"raw_text": transcribed_text, "input_type": "voice"},
            headers=auth_headers,
        )
        assert resp.status_code == 201

        resp = await async_client.get("/v1/captures", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["input_type"] == "voice"

    async def test_edited_transcription_works(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """User edits the transcribed text before submitting."""
        # Transcribe returns canned text, but user overrides it.
        resp = await _transcribe(async_client, auth_headers)
        assert resp.status_code == 200

        edited_text = "Elden Ring on PS5"
        resp = await async_client.post(
            "/v1/captures/text",
            json={"raw_text": edited_text, "input_type": "voice"},
            headers=auth_headers,
        )
        assert resp.status_code == 201

        data = resp.json()
        assert data["raw_text"] == edited_text
        assert data["input_type"] == "voice"
        titles = {c["title"] for c in data["candidates"]}
        assert "Elden Ring" in titles
