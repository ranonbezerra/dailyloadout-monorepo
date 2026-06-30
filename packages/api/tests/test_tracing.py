"""Tests for the observability layer: spans, the LLM tracer, and node spans."""

from __future__ import annotations

from slate.config import settings
from slate.infrastructure.agent.graph.builder import _traced_node
from slate.infrastructure.llm.dummy import DummyLLMClient
from slate.infrastructure.llm.traced import TracedLLMClient
from slate.infrastructure.observability.tracing import (
    add_span_attrs,
    current_trace,
    redact,
    span,
    start_trace,
)

# =====================================================================
# Tracing primitive
# =====================================================================


class TestTracingPrimitive:
    async def test_span_collected_with_duration_and_attrs(self) -> None:
        with start_trace() as spans:
            async with span("unit", role="fast"):
                pass
        assert len(spans) == 1
        assert spans[0].name == "unit"
        assert spans[0].attrs["role"] == "fast"
        assert spans[0].duration_ms >= 0.0

    async def test_add_span_attrs_merges_into_open_span(self) -> None:
        with start_trace() as spans:
            async with span("unit"):
                add_span_attrs(prompt_tokens=12, completion_tokens=34)
        assert spans[0].attrs["prompt_tokens"] == 12
        assert spans[0].attrs["completion_tokens"] == 34

    async def test_add_span_attrs_is_noop_without_open_span(self) -> None:
        add_span_attrs(x=1)  # must not raise

    async def test_no_trace_active_does_not_collect(self) -> None:
        assert current_trace() is None
        async with span("orphan"):
            pass  # emits a log line, collected nowhere
        assert current_trace() is None

    async def test_nested_spans_restore_parent(self) -> None:
        with start_trace() as spans:
            async with span("outer"):
                async with span("inner"):
                    add_span_attrs(where="inner")
                add_span_attrs(where="outer")
        names = {s.name: s.attrs.get("where") for s in spans}
        assert names == {"inner": "inner", "outer": "outer"}

    def test_redact_truncates(self) -> None:
        assert redact("  hi  ") == "hi"
        long = "x" * 600
        out = redact(long, 500)
        assert len(out) == 501 and out.endswith("…")


# =====================================================================
# TracedLLMClient
# =====================================================================


class TestTracedLLMClient:
    async def test_each_call_emits_a_span_with_role(self) -> None:
        traced = TracedLLMClient(DummyLLMClient())
        with start_trace() as spans:
            await traced.complete("hello", role="smart")
            await traced.generate_recap("Hades", [])
            await traced.parse_capture_text("got Hades")
        by_name = {s.name: s for s in spans}
        assert by_name["llm.complete"].attrs["role"] == "smart"
        assert by_name["llm.generate_recap"].attrs["role"] == "smart"
        assert by_name["llm.parse_capture_text"].attrs["role"] == "fast"
        assert by_name["llm.parse_capture_text"].attrs["output_count"] == 1

    async def test_returns_inner_result_unchanged(self) -> None:
        inner = DummyLLMClient()
        traced = TracedLLMClient(inner)
        assert await traced.complete("x") == await inner.complete("x")

    async def test_capture_disabled_by_default(self) -> None:
        traced = TracedLLMClient(DummyLLMClient())
        with start_trace() as spans:
            await traced.complete("secret prompt")
        assert "prompt" not in spans[0].attrs

    async def test_capture_enabled_records_redacted_preview(self) -> None:
        original = settings.trace_capture_enabled
        settings.trace_capture_enabled = True
        try:
            traced = TracedLLMClient(DummyLLMClient())
            with start_trace() as spans:
                await traced.complete("a visible prompt")
        finally:
            settings.trace_capture_enabled = original
        assert spans[0].attrs["prompt"] == "a visible prompt"

    async def test_all_methods_are_wrapped(self) -> None:
        traced = TracedLLMClient(DummyLLMClient())
        with start_trace() as spans:
            await traced.parse_capture_image("base64==")
            await traced.extract_wrap_up_state("Hades", "beat the boss")
            await traced.select_game(
                [{"public_id": "p1", "game_title": "Hades"}], "chill", 30, "low"
            )
        names = {s.name for s in spans}
        assert names == {
            "llm.parse_capture_image",
            "llm.extract_wrap_up_state",
            "llm.select_game",
        }


# =====================================================================
# Graph node spans
# =====================================================================


class TestGraphNodeSpans:
    async def test_traced_node_emits_graph_span(self) -> None:
        async def fake_node(state: dict[str, object]) -> dict[str, object]:
            return {"queries": ["q"]}

        wrapped = _traced_node("build_query", fake_node)
        with start_trace() as spans:
            result = await wrapped({"foo": "bar"})
        assert result == {"queries": ["q"]}
        assert [s.name for s in spans] == ["graph.build_query"]
