"""Tests for capture_processor edge cases and _load_image_as_jpeg."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from PIL import Image

from slate.infrastructure.llm.dummy import DummyLLMClient
from slate.workers.capture_processor import _load_image_as_jpeg, process_capture


def _make_capture(**overrides: object) -> MagicMock:
    defaults: dict[str, object] = {
        "id": 1,
        "user_id": 1,
        "input_type": "text",
        "raw_text": "I bought Hollow Knight",
        "status": "queued",
        "image_path": None,
    }
    defaults.update(overrides)
    return MagicMock(**defaults)


class TestProcessCaptureEdgeCases:
    async def test_photo_no_image_path(self) -> None:
        capture = _make_capture(input_type="photo", image_path=None)
        capture_repo = AsyncMock()
        candidate_repo = AsyncMock()
        llm = DummyLLMClient()

        result = await process_capture(capture, capture_repo, candidate_repo, llm, None)

        capture_repo.update_status.assert_any_call(
            1, "failed", error_message="No image to process"
        )
        assert result is capture

    async def test_text_no_raw_text(self) -> None:
        capture = _make_capture(input_type="text", raw_text=None)
        capture_repo = AsyncMock()
        candidate_repo = AsyncMock()
        llm = DummyLLMClient()

        result = await process_capture(capture, capture_repo, candidate_repo, llm, None)

        capture_repo.update_status.assert_any_call(1, "failed", error_message="No text to process")
        assert result is capture

    async def test_empty_extraction_sets_review(self) -> None:
        capture = _make_capture(input_type="text", raw_text="asdf")
        capture_repo = AsyncMock()
        candidate_repo = AsyncMock()

        llm = AsyncMock()
        llm.parse_capture_text = AsyncMock(return_value=[])

        result = await process_capture(capture, capture_repo, candidate_repo, llm, None)

        capture_repo.update_status.assert_any_call(
            1, "review", error_message="No games found in text"
        )
        assert result is capture

    async def test_exception_sets_failed(self) -> None:
        capture = _make_capture(input_type="text", raw_text="Hollow Knight")
        capture_repo = AsyncMock()
        candidate_repo = AsyncMock()

        llm = AsyncMock()
        llm.parse_capture_text = AsyncMock(side_effect=RuntimeError("secret internal detail"))

        await process_capture(capture, capture_repo, candidate_repo, llm, None)

        last_call = capture_repo.update_status.call_args_list[-1]
        assert last_call.args[1] == "failed"
        # The persisted error_message is generic — raw exception text (which can
        # leak internals to the client) must never be stored.
        error_message = last_call.kwargs["error_message"]
        assert error_message == "Processing failed. Please try again."
        assert "secret internal detail" not in error_message

    async def test_igdb_enrichment_adds_metadata(self) -> None:
        from slate.infrastructure.igdb.schemas import IGDBGame
        from slate.infrastructure.llm.base import ExtractedGame

        capture = _make_capture(input_type="text", raw_text="Hollow Knight")
        capture_repo = AsyncMock()
        candidate_repo = AsyncMock()

        llm = AsyncMock()
        llm.parse_capture_text = AsyncMock(
            return_value=[ExtractedGame(title="Hollow Knight", confidence=0.9)]
        )

        igdb = AsyncMock()
        igdb.search_games = AsyncMock(
            return_value=[IGDBGame(igdb_id=99, title="Hollow Knight", cover_url="http://img.url")]
        )

        await process_capture(capture, capture_repo, candidate_repo, llm, igdb)

        candidate_repo.create.assert_called_once()
        call_kwargs = candidate_repo.create.call_args.kwargs
        assert call_kwargs.get("igdb_id") == 99

    async def test_igdb_not_configured_graceful(self) -> None:
        from slate.infrastructure.igdb.exceptions import IGDBNotConfiguredError
        from slate.infrastructure.llm.base import ExtractedGame

        capture = _make_capture(input_type="text", raw_text="Hollow Knight")
        capture_repo = AsyncMock()
        candidate_repo = AsyncMock()

        llm = AsyncMock()
        llm.parse_capture_text = AsyncMock(
            return_value=[ExtractedGame(title="Hollow Knight", confidence=0.9)]
        )

        igdb = AsyncMock()
        igdb.search_games = AsyncMock(side_effect=IGDBNotConfiguredError())

        await process_capture(capture, capture_repo, candidate_repo, llm, igdb)

        # Should still create the candidate, just without IGDB data.
        candidate_repo.create.assert_called_once()

    async def test_igdb_generic_error_graceful(self) -> None:
        from slate.infrastructure.llm.base import ExtractedGame

        capture = _make_capture(input_type="text", raw_text="Hollow Knight")
        capture_repo = AsyncMock()
        candidate_repo = AsyncMock()

        llm = AsyncMock()
        llm.parse_capture_text = AsyncMock(
            return_value=[ExtractedGame(title="Hollow Knight", confidence=0.9)]
        )

        igdb = AsyncMock()
        igdb.search_games = AsyncMock(side_effect=RuntimeError("network error"))

        await process_capture(capture, capture_repo, candidate_repo, llm, igdb)

        candidate_repo.create.assert_called_once()


class TestLoadImageAsJpeg:
    def test_native_png_returns_raw_bytes(self, tmp_path: Path) -> None:
        img = Image.new("RGB", (10, 10), color="red")
        path = tmp_path / "test.png"
        img.save(path, format="PNG")

        result = _load_image_as_jpeg(path)
        assert result == path.read_bytes()

    def test_native_jpeg_returns_raw_bytes(self, tmp_path: Path) -> None:
        img = Image.new("RGB", (10, 10), color="blue")
        path = tmp_path / "test.jpg"
        img.save(path, format="JPEG")

        result = _load_image_as_jpeg(path)
        assert result == path.read_bytes()

    def test_bmp_converts_to_jpeg(self, tmp_path: Path) -> None:
        img = Image.new("RGB", (10, 10), color="green")
        path = tmp_path / "test.bmp"
        img.save(path, format="BMP")

        result = _load_image_as_jpeg(path)
        # Should be valid JPEG bytes, not the original BMP.
        converted = Image.open(io.BytesIO(result))
        assert converted.format == "JPEG"

    def test_rgba_converted_to_rgb_jpeg(self, tmp_path: Path) -> None:
        img = Image.new("RGBA", (10, 10), color=(255, 0, 0, 128))
        path = tmp_path / "test.bmp"
        img.save(path, format="BMP")

        result = _load_image_as_jpeg(path)
        converted = Image.open(io.BytesIO(result))
        assert converted.format == "JPEG"
        assert converted.mode == "RGB"
