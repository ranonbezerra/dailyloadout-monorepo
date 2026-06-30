"""LLM evaluation harness — golden-dataset eval with deterministic checks + judge.

Public surface:

    from slate.core.eval import run_eval, golden_cases, LLMJudge, DummyJudge
"""

from slate.core.eval.golden import golden_cases
from slate.core.eval.judge import AbstractJudge, DummyJudge, LLMJudge
from slate.core.eval.runner import produce_output, run_case, run_eval
from slate.core.eval.schema import CaseResult, CheckResult, EvalCase, EvalReport

__all__ = [
    "AbstractJudge",
    "CaseResult",
    "CheckResult",
    "DummyJudge",
    "EvalCase",
    "EvalReport",
    "LLMJudge",
    "golden_cases",
    "produce_output",
    "run_case",
    "run_eval",
]
