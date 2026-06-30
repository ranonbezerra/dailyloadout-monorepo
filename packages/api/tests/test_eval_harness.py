"""Tests for the LLM evaluation harness (schema, checks, judge, runner, golden)."""

from __future__ import annotations

from pathlib import Path

import pytest

from evals import (
    DummyJudge,
    EvalCase,
    LLMJudge,
    golden_cases,
    produce_output,
    run_eval,
)
from evals.cache import cache_corpus, evaluate_cache
from evals.calibration import (
    bucket,
    calibration_cases,
    interpret_kappa,
    quadratic_weighted_kappa,
)
from evals.checks import run_checks
from evals.gate import baseline_from_report, diff_baseline
from evals.gate_cache import fingerprint, is_cached_pass, record_pass
from evals.retrieval import evaluate_retrieval, retrieval_cases
from evals.schema import CaseResult, CheckResult, EvalReport
from slate.infrastructure.agent.dummy import DummyRecapAgent
from slate.infrastructure.embedding import DummyEmbeddingClient
from slate.infrastructure.llm.dummy import DummyLLMClient


class _JudgeLLM(DummyLLMClient):
    """A DummyLLMClient whose ``complete`` returns a scripted judge payload."""

    def __init__(self, payload: str) -> None:
        self._payload = payload

    async def complete(self, prompt: str, *, role: str = "fast", json: bool = False) -> str:  # type: ignore[override]
        return self._payload


# =====================================================================
# Golden dataset — well-formed + the pipeline runs (quality is judged
# against a real model, not the dummy, so we don't assert pass-rate here)
# =====================================================================


class TestGoldenDataset:
    def test_dataset_is_well_formed(self) -> None:
        cases = golden_cases()
        assert len(cases) == 14  # 12 quick + 2 deep
        assert {c.task for c in cases} == {"recap", "deep_recap"}
        assert len({c.id for c in cases}) == 14  # unique ids
        for c in cases:
            assert "context" in c.reference
            if c.task == "recap":
                assert c.checks == ["non_empty", "grounding", "spoiler_free", "mentions"]
            else:  # deep_recap grounds on web research, so it omits grounding-vs-notes
                assert c.checks == ["non_empty", "spoiler_free", "mentions"]
            # previous_wrap_ups carry extracted_state alongside raw_text (prod fidelity).
            for wu in c.inputs["previous_wrap_ups"]:  # type: ignore[union-attr]
                assert "raw_text" in wu

    async def test_pipeline_runs_over_the_dataset(self) -> None:
        # The deep_recap cases need an agent; the dummy one runs the canned path.
        report = await run_eval(DummyLLMClient(), golden_cases(), DummyJudge(), DummyRecapAgent())
        assert len(report.results) == 14
        assert set(report.scores_by_task()) == {"recap", "deep_recap"}
        assert all(r.output for r in report.results)
        assert all(0.0 <= r.score <= 1.0 for r in report.results)

    async def test_deep_recap_task_uses_the_agent(self) -> None:
        case = next(c for c in golden_cases() if c.task == "deep_recap")
        output = await produce_output(DummyLLMClient(), case, DummyRecapAgent())
        assert output  # the agent produced a recap
        assert case.inputs["game_title"].split()[0] in output  # type: ignore[union-attr]

    async def test_deep_recap_without_agent_raises(self) -> None:
        case = next(c for c in golden_cases() if c.task == "deep_recap")
        with pytest.raises(ValueError, match="requires a recap agent"):
            await produce_output(DummyLLMClient(), case)


# =====================================================================
# Deterministic checks
# =====================================================================


class TestChecks:
    def test_grounding_flags_ungrounded_output(self) -> None:
        case = EvalCase(
            id="x",
            task="recap",
            inputs={},
            reference={"context": "Hollow Knight Greenpath"},
            checks=["grounding"],
        )
        [result] = run_checks("Completely Different Imaginary Zelda Castle Dragon", case)
        assert result.name == "grounding"
        assert not result.passed

    def test_grounding_ignores_boilerplate_capitalized_words(self) -> None:
        # "Welcome", "You", "Head", "Now" are sentence-initial common words, not
        # proper nouns — they must NOT drag the overlap down. Only "Watson" counts.
        case = EvalCase(
            id="x", task="recap", inputs={}, reference={"context": "Watson"}, checks=["grounding"]
        )
        [result] = run_checks("Welcome back! You head to Watson now.", case)
        assert result.passed and result.score == pytest.approx(1.0)

    def test_grounding_ignores_sentence_initial_adverb(self) -> None:
        # Regression: "Carefully" leading a sentence used to count as a proper noun
        # and sink grounding to 0.00. It must be treated as boilerplate now.
        case = EvalCase(
            id="x", task="recap", inputs={}, reference={"context": "Watson"}, checks=["grounding"]
        )
        [result] = run_checks("Carefully make your way back toward Watson.", case)
        assert result.passed and result.score == pytest.approx(1.0)

    def test_grounding_keeps_context_proper_noun_at_note_start(self) -> None:
        # The context is NOT sentence-initial-lowercased, so a note that *starts*
        # with the entity ('Watson is...') still grounds an output that names it.
        case = EvalCase(
            id="x",
            task="recap",
            inputs={},
            reference={"context": "Watson is where you left off"},
            checks=["grounding"],
        )
        [result] = run_checks("you head back to Watson", case)
        assert result.passed and result.score == pytest.approx(1.0)

    def test_spoiler_free_catches_forbidden_term(self) -> None:
        case = EvalCase(
            id="x",
            task="recap",
            inputs={},
            reference={"forbidden": ["final boss"]},
            checks=["spoiler_free"],
        )
        [result] = run_checks("then you reach the FINAL BOSS", case)
        assert not result.passed

    def test_spoiler_free_word_boundary_no_substring_false_positive(self) -> None:
        # "ending" must NOT fire on "depending"/"ended"; "story" not on "history".
        case = EvalCase(
            id="x",
            task="recap",
            inputs={},
            reference={"forbidden": ["ending", "story"]},
            checks=["spoiler_free"],
        )
        text = "Depending on your cred you ended up in Watson; the history is yours"
        [result] = run_checks(text, case)
        assert result.passed and result.score == 1.0

    def test_mentions_word_boundary_no_substring_false_positive(self) -> None:
        # "camp" must NOT be satisfied by "campaign".
        case = EvalCase(
            id="x", task="recap", inputs={}, reference={"mentions": ["camp"]}, checks=["mentions"]
        )
        [result] = run_checks("you joined the campaign", case)
        assert not result.passed and result.score == 0.0

    def test_mentions_tolerates_singular_plural(self) -> None:
        # 'Terminids' (the expected term) should match a recap that wrote 'Terminid'.
        case = EvalCase(
            id="x",
            task="recap",
            inputs={},
            reference={"mentions": ["Terminids"]},
            checks=["mentions"],
        )
        [result] = run_checks("you fought a Terminid in the swamp", case)
        assert result.passed and result.score == pytest.approx(1.0)

    def test_grounding_tolerates_singular_plural(self) -> None:
        case = EvalCase(
            id="x",
            task="recap",
            inputs={},
            reference={"context": "fighting Terminids on hard"},
            checks=["grounding"],
        )
        [result] = run_checks("You fought a Terminid.", case)
        assert result.passed and result.score == pytest.approx(1.0)

    def test_mentions_scores_recall(self) -> None:
        case = EvalCase(
            id="x",
            task="recap",
            inputs={},
            reference={"mentions": ["Watson", "Regina"]},
            checks=["mentions"],
        )
        [hit] = run_checks("you are in Watson doing Regina's gigs", case)
        assert hit.passed and hit.score == pytest.approx(1.0)
        [partial] = run_checks("you are in Watson", case)
        assert not partial.passed and partial.score == pytest.approx(0.5)

    def test_mentions_passes_when_none_required(self) -> None:
        case = EvalCase(id="x", task="recap", inputs={}, reference={}, checks=["mentions"])
        [result] = run_checks("anything", case)
        assert result.passed and result.score == 1.0

    def test_json_valid_rejects_non_json(self) -> None:
        case = EvalCase(id="x", task="capture", inputs={}, checks=["json_valid"])
        [result] = run_checks("not json", case)
        assert not result.passed

    def test_uuid_in_candidates_rejects_unknown(self) -> None:
        case = EvalCase(
            id="x",
            task="pick",
            inputs={},
            reference={"candidate_ids": ["abc"]},
            checks=["uuid_in_candidates"],
        )
        [result] = run_checks('{"library_entry_public_id": "zzz"}', case)
        assert not result.passed

    def test_unknown_check_name_is_skipped(self) -> None:
        case = EvalCase(id="x", task="recap", inputs={}, checks=["does_not_exist"])
        assert run_checks("anything", case) == []

    def test_uuid_in_candidates_rejects_non_object_json(self) -> None:
        case = EvalCase(
            id="x",
            task="pick",
            inputs={},
            reference={"candidate_ids": ["abc"]},
            checks=["uuid_in_candidates"],
        )
        [result] = run_checks('["abc"]', case)  # valid JSON, but a list, not an object
        assert not result.passed


# =====================================================================
# Judge
# =====================================================================


class TestJudge:
    async def test_llm_judge_parses_score(self) -> None:
        judge = LLMJudge(_JudgeLLM('{"score": 0.8, "reason": "good"}'))
        score, reason = await judge.score(golden_cases()[0], "out")
        assert score == pytest.approx(0.8)
        assert reason == "good"

    async def test_llm_judge_clamps_out_of_range(self) -> None:
        judge = LLMJudge(_JudgeLLM('{"score": 5, "reason": "x"}'))
        score, _ = await judge.score(golden_cases()[0], "out")
        assert score == 1.0

    async def test_llm_judge_survives_unparsable_output(self) -> None:
        judge = LLMJudge(_JudgeLLM("not json at all"))
        score, reason = await judge.score(golden_cases()[0], "out")
        assert score == 0.0
        assert "unparsable" in reason

    async def test_llm_judge_extracts_verdict_from_reasoning(self) -> None:
        # Thinking models emit reasoning (and maybe a fenced block) around the JSON;
        # the judge runs free-text now, so the verdict must still be recovered.
        payload = (
            "<think>The recap stays grounded in the notes and suggests a "
            "concrete next step.</think>\nVerdict:\n```json\n"
            '{"score": 0.9, "reason": "faithful and grounded"}\n```'
        )
        judge = LLMJudge(_JudgeLLM(payload))
        score, reason = await judge.score(golden_cases()[0], "out")
        assert score == pytest.approx(0.9)
        assert reason == "faithful and grounded"

    async def test_llm_judge_takes_final_verdict(self) -> None:
        # If the reasoning floats a draft score, the LAST {score} block wins.
        payload = (
            'A first impression might be {"score": 0.2, "reason": "draft"}, but '
            'my final answer is {"score": 0.85, "reason": "final"}.'
        )
        judge = LLMJudge(_JudgeLLM(payload))
        score, reason = await judge.score(golden_cases()[0], "out")
        assert score == pytest.approx(0.85)
        assert reason == "final"

    async def test_dummy_judge_is_fixed(self) -> None:
        score, reason = await DummyJudge(0.7).score(golden_cases()[0], "out")
        assert score == pytest.approx(0.7)
        assert reason == "dummy"

    async def test_llm_judge_clamps_non_numeric_score(self) -> None:
        judge = LLMJudge(_JudgeLLM('{"score": "abc", "reason": "r"}'))
        score, _ = await judge.score(golden_cases()[0], "out")
        assert score == 0.0


# =====================================================================
# Schema aggregation + runner dispatch
# =====================================================================


class TestSchemaAndRunner:
    def test_case_score_without_judge_is_deterministic_mean(self) -> None:
        result = CaseResult(
            case_id="x",
            task="recap",
            output="o",
            checks=[
                CheckResult(name="a", passed=True, score=1.0),
                CheckResult(name="b", passed=True, score=0.5),
            ],
        )
        assert result.deterministic_score == pytest.approx(0.75)
        assert result.score == pytest.approx(0.75)

    def test_case_score_blends_judge(self) -> None:
        result = CaseResult(
            case_id="x",
            task="recap",
            output="o",
            checks=[CheckResult(name="a", passed=True, score=1.0)],
            judge_score=0.0,
        )
        assert result.score == pytest.approx(0.5)

    def test_case_with_no_checks_scores_one(self) -> None:
        result = CaseResult(case_id="x", task="recap", output="o", checks=[])
        assert result.deterministic_score == 1.0
        assert result.passed

    def test_empty_report_defaults(self) -> None:
        report = EvalReport(results=[])
        assert report.overall_score == 1.0
        assert report.pass_rate == 1.0
        assert report.scores_by_task() == {}

    async def test_produce_output_unknown_task_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown eval task"):
            await produce_output(DummyLLMClient(), EvalCase(id="x", task="nope", inputs={}))

    async def test_produce_output_pick_invalid_uuid_fails_check(self) -> None:
        # mood='test_invalid_uuid' makes the dummy return a uuid outside the candidates.
        case = EvalCase(
            id="pick-bad",
            task="pick",
            inputs={
                "candidates": [{"public_id": "abc", "game_title": "Hades"}],
                "mood": "test_invalid_uuid",
                "available_minutes": 30,
                "mental_energy": "low",
            },
            reference={"candidate_ids": ["abc"]},
            checks=["uuid_in_candidates"],
            judge=False,
        )
        report = await run_eval(DummyLLMClient(), [case])
        assert not report.results[0].passed


# =====================================================================
# Baseline regression gate
# =====================================================================


def _report(*pairs: tuple[str, float]) -> EvalReport:
    """A report of recap cases whose single check 'grounding' has the given score."""
    return EvalReport(
        results=[
            CaseResult(
                case_id=cid,
                task="recap",
                output="x",
                checks=[CheckResult(name="grounding", passed=True, score=score)],
                judge_score=None,
            )
            for cid, score in pairs
        ]
    )


class TestGate:
    def test_baseline_is_flat_metrics(self) -> None:
        baseline = baseline_from_report(_report(("a", 1.0), ("b", 0.5)))
        assert baseline["overall"] == pytest.approx(0.75)
        assert baseline["task:recap"] == pytest.approx(0.75)
        assert baseline["check:grounding"] == pytest.approx(0.75)

    def test_no_regression_within_tolerance(self) -> None:
        baseline = baseline_from_report(_report(("a", 1.0), ("b", 0.8)))
        # Drop of 0.04 on grounding, under the 0.05 tolerance → no regression.
        current = _report(("a", 1.0), ("b", 0.72))
        assert diff_baseline(current, baseline, 0.05) == []

    def test_regression_beyond_tolerance_is_flagged(self) -> None:
        baseline = baseline_from_report(_report(("a", 1.0), ("b", 0.8)))
        current = _report(("a", 1.0), ("b", 0.40))  # grounding tanks
        regressions = diff_baseline(current, baseline, 0.05)
        assert any("check:grounding" in r for r in regressions)
        assert any("overall" in r for r in regressions)

    def test_new_metric_absent_from_baseline_is_not_a_regression(self) -> None:
        baseline = {"overall": 0.9}  # baseline predates per-check metrics
        current = _report(("a", 0.2))
        # overall regresses, but the new check:grounding key is ignored.
        regressions = diff_baseline(current, baseline, 0.05)
        assert all("check:" not in r for r in regressions)


# =====================================================================
# Judge calibration (kappa vs human labels)
# =====================================================================


class TestCalibration:
    def test_bucket_edges(self) -> None:
        assert bucket(0.0) == 0
        assert bucket(0.39) == 0
        assert bucket(0.40) == 1  # ok floor is inclusive
        assert bucket(0.74) == 1
        assert bucket(0.75) == 2  # good floor is inclusive
        assert bucket(1.0) == 2

    def test_calibration_set_is_well_formed(self) -> None:
        cases = calibration_cases()
        assert len(cases) == 14
        assert len({c.id for c in cases}) == 14  # unique ids
        assert all(0.0 <= c.human_score <= 1.0 for c in cases)
        # The set must span all three buckets, or the kappa has nothing to separate.
        assert {bucket(c.human_score) for c in cases} == {0, 1, 2}

    def test_to_eval_case_carries_context_and_behavior(self) -> None:
        case = calibration_cases()[0]
        ec = case.to_eval_case()
        assert ec.reference["context"] == case.context
        assert ec.reference["behavior"] == case.behavior

    def test_kappa_perfect_agreement_is_one(self) -> None:
        labels = [0, 1, 2, 0, 1, 2]
        assert quadratic_weighted_kappa(labels, labels, 3) == pytest.approx(1.0)

    def test_kappa_systematic_disagreement_is_zero(self) -> None:
        # Human all 'poor', judge all 'good' → no better than chance once the
        # marginals are accounted for.
        assert quadratic_weighted_kappa([0, 0, 0], [2, 2, 2], 3) == pytest.approx(0.0)

    def test_kappa_constant_equal_raters_is_one(self) -> None:
        # No expected disagreement (both raters constant + equal) → 1.0 by convention.
        assert quadratic_weighted_kappa([1, 1, 1], [1, 1, 1], 3) == pytest.approx(1.0)

    def test_kappa_adjacent_miss_beats_two_bucket_miss(self) -> None:
        # Quadratic weighting: an off-by-one disagreement scores higher than off-by-two.
        adjacent = quadratic_weighted_kappa([0, 1, 2, 0], [0, 1, 2, 1], 3)
        far = quadratic_weighted_kappa([0, 1, 2, 0], [0, 1, 2, 2], 3)
        assert adjacent > far

    def test_kappa_rejects_empty_or_mismatched(self) -> None:
        with pytest.raises(ValueError):
            quadratic_weighted_kappa([], [], 3)
        with pytest.raises(ValueError):
            quadratic_weighted_kappa([0, 1], [0], 3)

    def test_interpret_kappa_bands(self) -> None:
        assert "almost perfect" in interpret_kappa(0.9)
        assert "substantial" in interpret_kappa(0.7)
        assert interpret_kappa(-0.1).startswith("poor")


# =====================================================================
# Gate cache (skip the real gate when nothing eval-relevant changed)
# =====================================================================


def _seed_tree(root: Path) -> None:
    """A minimal repo-shaped tree with one file in each relevant area."""
    (root / "src/slate/prompts").mkdir(parents=True)
    (root / "src/slate/prompts/recap.j2").write_text("recap {{ notes }}")
    (root / "src/slate/config.py").write_text("ollama_smart_model = 'gemma3:12b'")
    (root / "evals/results").mkdir(parents=True)
    (root / "evals/golden.py").write_text("CASES = 1")


class TestGateCache:
    def test_fingerprint_changes_when_relevant_file_changes(self, tmp_path: Path) -> None:
        _seed_tree(tmp_path)
        before = fingerprint(tmp_path)
        (tmp_path / "src/slate/prompts/recap.j2").write_text("recap CHANGED {{ notes }}")
        assert fingerprint(tmp_path) != before

    def test_fingerprint_ignores_irrelevant_file(self, tmp_path: Path) -> None:
        _seed_tree(tmp_path)
        before = fingerprint(tmp_path)
        # An auth router is not part of the recap pipeline → must not re-arm the gate.
        (tmp_path / "src/slate/api/v1").mkdir(parents=True)
        (tmp_path / "src/slate/api/v1/auth.py").write_text("ROUTES = []")
        assert fingerprint(tmp_path) == before

    def test_fingerprint_ignores_transient_artifacts(self, tmp_path: Path) -> None:
        _seed_tree(tmp_path)
        before = fingerprint(tmp_path)
        # latest.json + the cache itself live under evals/ but must be excluded,
        # or the cache could never hit.
        (tmp_path / "evals/results/latest.json").write_text('{"overall": 0.9}')
        (tmp_path / "evals/results/.gate-cache").write_text("deadbeef")
        assert fingerprint(tmp_path) == before

    def test_record_then_cached_pass_roundtrips(self, tmp_path: Path) -> None:
        _seed_tree(tmp_path)
        cache = tmp_path / "evals/results/.gate-cache"
        assert not is_cached_pass(tmp_path, cache)  # nothing recorded yet
        record_pass(tmp_path, cache)
        assert is_cached_pass(tmp_path, cache)
        # A change to a relevant file invalidates the cached pass.
        (tmp_path / "src/slate/config.py").write_text("ollama_smart_model = 'gemma3:27b'")
        assert not is_cached_pass(tmp_path, cache)


# =====================================================================
# Retrieval A/B (semantic vs recent recall@k — Epic 24)
# =====================================================================


class TestRetrievalEval:
    async def test_semantic_beats_recent_on_buried_context(self) -> None:
        report = await evaluate_retrieval(DummyEmbeddingClient(dimensions=256))
        assert report.semantic_recall > report.recent_recall
        assert report.delta > 0.0
        assert 0.0 <= report.recent_recall <= 1.0
        assert 0.0 <= report.semantic_recall <= 1.0

    async def test_control_case_semantic_does_not_regress(self) -> None:
        # When the relevant context is already recent, semantic must not lose recall.
        report = await evaluate_retrieval(DummyEmbeddingClient(dimensions=256))
        control = next(r for r in report.rows if r["id"] == "recency_sufficient")
        assert float(control["semantic"]) >= float(control["recent"])

    def test_cases_have_buried_relevant_sessions(self) -> None:
        # Each non-control case's gold must sit OUTSIDE the chronological top_k,
        # or the A/B would prove nothing.
        for case in retrieval_cases():
            if case.id == "recency_sufficient":
                continue
            recent_by_age = sorted(range(len(case.pool)), key=lambda i: case.pool[i][1])
            recent_top_k = set(recent_by_age[: case.top_k])
            assert case.gold - recent_top_k, f"{case.id}: gold is not buried"


# =====================================================================
# Semantic capture-cache experiment (Epic 27)
# =====================================================================


class TestCacheExperiment:
    async def test_lower_threshold_lifts_hit_rate(self) -> None:
        results = {r.threshold: r for r in await evaluate_cache(DummyEmbeddingClient())}
        assert results[0.60].hit_rate >= results[0.95].hit_rate
        assert all(0.0 <= r.hit_rate <= 1.0 for r in results.values())

    async def test_false_hits_only_at_low_threshold(self) -> None:
        # The confusable ("Final Fantasy XVI" ~ "VII") is served wrong only when the
        # threshold is loose; a strict threshold never serves a wrong parse.
        results = {r.threshold: r for r in await evaluate_cache(DummyEmbeddingClient())}
        assert results[0.60].false_hits > 0
        assert results[0.95].false_hits == 0

    def test_corpus_has_near_dups_and_a_confusable(self) -> None:
        corpus = cache_corpus()
        titles = [c.true_title for c in corpus]
        assert "Final Fantasy VII" in titles and "Final Fantasy XVI" in titles
        assert titles.count("Elden Ring") >= 2  # near-duplicate spellings
