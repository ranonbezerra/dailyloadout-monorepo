"""Tests for the photo capture flow: upload image -> vision LLM extraction -> candidates."""

from __future__ import annotations

import io
from typing import Any

from httpx import AsyncClient
from PIL import Image


def _real_png(size_px: int = 1) -> bytes:
    """Return the bytes of a real, decodable PNG (passes magic-byte validation)."""
    buf = io.BytesIO()
    Image.new("RGB", (size_px, size_px), (10, 20, 30)).save(buf, format="PNG")
    return buf.getvalue()


# =====================================================================
# Helpers
# =====================================================================

_MINIMAL_PNG = _real_png()


def _make_image_file(size: int | None = None) -> io.BytesIO:
    """Create a real in-memory PNG for upload tests.

    If *size* is given, the buffer is padded past the image with trailing bytes
    (ignored by the PNG decoder) so the size guard can be exercised.
    """
    data = _MINIMAL_PNG
    if size is not None and size > len(data):
        data = data + b"\x00" * (size - len(data))
    buf = io.BytesIO(data)
    buf.name = "test.png"
    return buf


async def _upload_photo(
    client: AsyncClient,
    headers: dict[str, str],
    image_file: io.BytesIO | None = None,
    content_type: str = "image/png",
    filename: str = "test.png",
) -> Any:
    """Upload a photo for capture and return the httpx response."""
    if image_file is None:
        image_file = _make_image_file()
    return await client.post(
        "/v1/captures/photo",
        files={"file": (filename, image_file, content_type)},
        headers=headers,
    )


# =====================================================================
# Test: Photo upload endpoint
# =====================================================================


class TestPhotoUpload:
    async def test_upload_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        resp = await _upload_photo(async_client, auth_headers)
        assert resp.status_code == 201, resp.text

        data = resp.json()
        assert data["input_type"] == "photo"
        assert data["status"] == "review"
        assert len(data["candidates"]) >= 1

    async def test_upload_invalid_mime(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        buf = io.BytesIO(b"not image data")
        resp = await _upload_photo(
            async_client,
            auth_headers,
            image_file=buf,
            content_type="text/plain",
            filename="test.txt",
        )
        assert resp.status_code == 400
        assert "image" in resp.json()["detail"].lower()

    async def test_upload_too_large(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        # 11 MB file (exceeds 10 MB limit).
        large_file = _make_image_file(size=11 * 1024 * 1024)
        resp = await _upload_photo(async_client, auth_headers, image_file=large_file)
        assert resp.status_code == 400
        assert "10MB" in resp.json()["detail"]

    async def test_upload_rejects_spoofed_image(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Bytes that aren't a real image are rejected even with an image/* MIME."""
        buf = io.BytesIO(b"this is not really a PNG, just text")
        buf.name = "fake.png"
        resp = await _upload_photo(
            async_client,
            auth_headers,
            image_file=buf,
            content_type="image/png",
            filename="fake.png",
        )
        assert resp.status_code == 400
        assert "valid image" in resp.json()["detail"].lower()

    async def test_upload_unauthorized(
        self,
        async_client: AsyncClient,
    ) -> None:
        image_file = _make_image_file()
        resp = await async_client.post(
            "/v1/captures/photo",
            files={"file": ("test.png", image_file, "image/png")},
        )
        assert resp.status_code == 401


# =====================================================================
# Test: Full photo capture flow
# =====================================================================


class TestPhotoCaptureFlow:
    async def test_photo_candidates_extracted(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Upload photo -> DummyLLM returns 3 shelf games."""
        resp = await _upload_photo(async_client, auth_headers)
        assert resp.status_code == 201

        data = resp.json()
        assert data["input_type"] == "photo"
        assert data["status"] == "review"

        # DummyLLMClient.parse_capture_image returns exactly 3 games.
        titles = {c["title"] for c in data["candidates"]}
        assert "The Legend of Zelda: Tears of the Kingdom" in titles
        assert "Elden Ring" in titles
        assert "Celeste" in titles
        assert len(data["candidates"]) == 3

        for candidate in data["candidates"]:
            assert candidate["status"] == "pending"
            assert candidate["confidence"] is not None

    async def test_photo_candidates_appear_in_detail(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Candidates from photo capture should appear when fetching capture detail."""
        resp = await _upload_photo(async_client, auth_headers)
        assert resp.status_code == 201
        capture_id = resp.json()["public_id"]

        resp = await async_client.get(
            f"/v1/captures/{capture_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200

        data = resp.json()
        assert len(data["candidates"]) == 3
        titles = {c["title"] for c in data["candidates"]}
        assert "Elden Ring" in titles

    async def test_photo_capture_appears_in_list(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        resp = await _upload_photo(async_client, auth_headers)
        assert resp.status_code == 201

        resp = await async_client.get("/v1/captures", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["input_type"] == "photo"

    async def test_confirm_photo_candidate(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Confirm a candidate from a photo capture into the library."""
        resp = await _upload_photo(async_client, auth_headers)
        assert resp.status_code == 201

        capture_data = resp.json()
        capture_id = capture_data["public_id"]
        candidate = capture_data["candidates"][0]
        candidate_id = candidate["public_id"]

        # Pick a platform to confirm with.
        platform_id = seed_platforms[0]["id"]

        resp = await async_client.post(
            f"/v1/captures/{capture_id}/candidates/{candidate_id}/confirm",
            json={"platform_id": platform_id, "status": "backlog"},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text

        data = resp.json()
        assert data["game"]["title"] is not None
        assert data["status"] == "backlog"
