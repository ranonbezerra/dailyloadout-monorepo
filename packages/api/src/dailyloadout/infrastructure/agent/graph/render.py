"""Thin Jinja2 loader for agent prompts.

Reuses the same ``SandboxedEnvironment`` discipline as the LLM client and the
shared ``prompts/`` directory, so agent prompts live alongside the others.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

from jinja2.sandbox import SandboxedEnvironment

from dailyloadout.core.sanitization import wrap_user_data

_PROMPTS_DIR = Path(__file__).resolve().parents[3] / "prompts"

_jinja_env = SandboxedEnvironment(autoescape=False)
# ``udata`` fences untrusted user/shared/library text in a <user_data> block and
# neutralizes any forged closing sentinel, so the model treats it as DATA only.
_jinja_env.filters["udata"] = wrap_user_data


@cache
def _template_src(name: str) -> str:
    """Load and cache a prompt template's source by file name."""
    return (_PROMPTS_DIR / name).read_text(encoding="utf-8")


def render(name: str, **kwargs: object) -> str:
    """Render the prompt template *name* with the given context."""
    return _jinja_env.from_string(_template_src(name)).render(**kwargs)
