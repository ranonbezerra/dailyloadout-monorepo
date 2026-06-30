"""LLM evaluation harness — golden-dataset eval with deterministic checks + judge.

Public surface:

    from evals import run_eval, golden_cases, LLMJudge, DummyJudge
"""

from evals.golden import golden_cases
from evals.judge import AbstractJudge, DummyJudge, LLMJudge
from evals.runner import produce_output, run_case, run_eval
from evals.schema import CaseResult, CheckResult, EvalCase, EvalReport

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
