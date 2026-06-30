"""Content fingerprint so the slow, real-model eval gate is skipped when nothing
that could change recap quality has changed since it last passed.

The gate (`run_eval.py --real --gate`) costs ~minutes of Ollama and needs the model
SSD connected. A push that only touches web/auth/docs **cannot** move a recap score,
so paying that cost — and blocking the push if the SSD is unplugged — is pure waste.

This hashes the files whose content directly shapes an eval verdict (prompts, the
LLM client, the deep-recap graph, the recap service, model selection, and the
harness itself incl. the baseline). When the gate passes we record the hash; if the
next run's hash matches, the gate is a no-op. Any edit to a relevant file changes
the hash and re-arms the gate; edits anywhere else are invisible to it.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parent.parent  # packages/api
_DEFAULT_CACHE = _API_ROOT / "evals" / "results" / ".gate-cache"

# Paths (relative to packages/api) whose content can change a recap score. A change
# anywhere here re-runs the gate; a change anywhere ELSE is correctly ignored.
_RELEVANT = (
    "src/slate/prompts",  # the Jinja2 templates behind every LLM output
    "src/slate/infrastructure/llm",  # client params (temperature, format, model wiring)
    "src/slate/infrastructure/embedding",  # embeddings drive semantic recap retrieval
    "src/slate/infrastructure/agent",  # the deep-recap LangGraph graph + nodes
    "src/slate/core/play_session",  # the quick-recap service + retrieval + prompt context
    "src/slate/config.py",  # model selection (ollama_*_model) + recap_retrieval
    "evals",  # golden set, checks, judge, calibration, retrieval A/B, and baseline.json
)
_EXCLUDE_DIR_PARTS = {"__pycache__"}
# Transient / self-referential files inside `evals` that must NOT enter the hash,
# or the cache could never hit (latest.json changes every run; the cache is itself).
_EXCLUDE_RELPATHS = {"evals/results/latest.json", "evals/results/.gate-cache"}


def _relevant_files(root: Path) -> list[Path]:
    found: list[Path] = []
    for rel in _RELEVANT:
        p = root / rel
        if p.is_file():
            found.append(p)
        elif p.is_dir():
            found.extend(f for f in p.rglob("*") if f.is_file())
    out: list[Path] = []
    for f in found:
        if _EXCLUDE_DIR_PARTS & set(f.parts):
            continue
        if f.relative_to(root).as_posix() in _EXCLUDE_RELPATHS:
            continue
        out.append(f)
    return out


def fingerprint(root: Path = _API_ROOT) -> str:
    """SHA-256 over the relevant files' relative paths + bytes (order-independent)."""
    h = hashlib.sha256()
    for f in sorted(_relevant_files(root)):
        h.update(f.relative_to(root).as_posix().encode())
        h.update(b"\0")
        h.update(f.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def is_cached_pass(root: Path = _API_ROOT, cache: Path = _DEFAULT_CACHE) -> bool:
    """True if the gate already passed for this exact content (skip the re-run)."""
    return cache.exists() and cache.read_text().strip() == fingerprint(root)


def record_pass(root: Path = _API_ROOT, cache: Path = _DEFAULT_CACHE) -> None:
    """Remember that the gate passed for the current content."""
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(fingerprint(root) + "\n")
