"""Tests for LLM response parsing helpers."""

from __future__ import annotations

import pytest

from dailyloadout.infrastructure.llm.parsers import _extract_json, _parse_game_list


class TestExtractJson:
    def test_already_array(self) -> None:
        assert _extract_json('[{"title": "Hades"}]') == '[{"title": "Hades"}]'

    def test_already_object(self) -> None:
        assert _extract_json('{"title": "Hades"}') == '{"title": "Hades"}'

    def test_markdown_fenced(self) -> None:
        text = 'Here are the games:\n```json\n[{"title": "Hades"}]\n```'
        assert _extract_json(text) == '[{"title": "Hades"}]'

    def test_preamble_before_bare_json(self) -> None:
        text = 'I found these games: [{"title": "Hades"}]'
        result = _extract_json(text)
        assert result is not None
        assert '"Hades"' in result

    def test_no_json_returns_none(self) -> None:
        assert _extract_json("no json here at all") is None

    def test_whitespace_stripped(self) -> None:
        assert _extract_json("  [1, 2]  ") == "[1, 2]"


class TestParseGameList:
    def test_plain_list(self) -> None:
        parsed = [{"title": "Hades", "confidence": 0.9}]
        result = _parse_game_list(parsed, "raw")
        assert result is not None
        assert len(result) == 1
        assert result[0].title == "Hades"
        assert result[0].confidence == pytest.approx(0.9)

    def test_dict_with_games_key(self) -> None:
        parsed = {"games": [{"title": "Celeste"}]}
        result = _parse_game_list(parsed, "raw")
        assert result is not None
        assert result[0].title == "Celeste"

    def test_dict_with_results_key(self) -> None:
        parsed = {"results": [{"title": "Celeste"}]}
        result = _parse_game_list(parsed, "raw")
        assert result is not None
        assert result[0].title == "Celeste"

    def test_dict_with_titles_key(self) -> None:
        parsed = {"titles": [{"title": "Celeste"}]}
        result = _parse_game_list(parsed, "raw")
        assert result is not None
        assert result[0].title == "Celeste"

    def test_single_game_dict(self) -> None:
        parsed = {"title": "Hades", "confidence": 0.8}
        result = _parse_game_list(parsed, "raw")
        assert result is not None
        assert len(result) == 1
        assert result[0].title == "Hades"

    def test_unrecognised_dict_returns_none(self) -> None:
        parsed = {"foo": "bar"}
        assert _parse_game_list(parsed, "raw") is None

    def test_non_list_after_unwrap_returns_none(self) -> None:
        assert _parse_game_list(42, "raw") is None

    def test_items_without_title_skipped(self) -> None:
        parsed = [{"title": "Hades"}, {"no_title": True}, {"title": "Celeste"}]
        result = _parse_game_list(parsed, "raw")
        assert result is not None
        assert len(result) == 2

    def test_max_items_truncation(self) -> None:
        parsed = [{"title": f"Game {i}"} for i in range(10)]
        result = _parse_game_list(parsed, "raw", max_items=3)
        assert result is not None
        assert len(result) == 3

    def test_confidence_none_stays_none(self) -> None:
        parsed = [{"title": "Hades"}]
        result = _parse_game_list(parsed, "raw")
        assert result is not None
        assert result[0].confidence is None

    def test_platform_hint_passthrough(self) -> None:
        parsed = [{"title": "Zelda", "platform_hint": "Switch"}]
        result = _parse_game_list(parsed, "raw")
        assert result is not None
        assert result[0].platform_hint == "Switch"

    def test_non_dict_items_skipped(self) -> None:
        parsed = [{"title": "Hades"}, "not a dict", 42]
        result = _parse_game_list(parsed, "raw")
        assert result is not None
        assert len(result) == 1
