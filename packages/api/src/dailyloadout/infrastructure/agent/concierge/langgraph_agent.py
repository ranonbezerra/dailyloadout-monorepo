"""LangGraph + ChatOllama implementation of the Concierge agent.

Uses ``ChatOllama.bind_tools`` (via ``create_react_agent``) for the tool-calling
loop. The tool-using model defaults to ``qwen3:8b`` — Gemma is weak at
function-calling. A shared in-memory checkpointer persists conversation threads
across turns (upgrade to a Postgres saver in Epic 16).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langchain_core.messages import HumanMessage
from langchain_core.messages.utils import count_tokens_approximately, trim_messages
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import StructuredTool
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from .base import AbstractConciergeAgent, ConciergeReply, ConciergeRequest

if TYPE_CHECKING:
    from dailyloadout.config import Settings

# Process-lifetime checkpointer: the agent is rebuilt per request (DI), so the
# saver must live at module scope or multi-turn history is lost between turns.
# Single-process only — a Postgres saver for multi-worker is ROADMAP Epic 16.
_CHECKPOINTER = MemorySaver()

# Cap the context fed to the model each turn. Persistent memory replays the whole
# thread (messages + verbose tool outputs) every turn, so without a bound the
# prompt grows unboundedly and prompt-eval time creeps up. Generous enough to
# hold a full single-turn tool loop while shedding old turns.
_MAX_CONTEXT_TOKENS = 4000


def _trim_history(state: dict[str, Any]) -> dict[str, Any]:
    """Keep only the most recent messages within a token budget.

    Trims to ``llm_input_messages`` (the model's view) without mutating the saved
    thread, starting on a human turn so tool-call/result pairs aren't orphaned.
    """
    trimmed = trim_messages(
        state["messages"],
        strategy="last",
        token_counter=count_tokens_approximately,
        max_tokens=_MAX_CONTEXT_TOKENS,
        start_on="human",
        end_on=("human", "tool"),
        include_system=False,
    )
    return {"llm_input_messages": trimmed}


class LangGraphConciergeAgent(AbstractConciergeAgent):
    def __init__(self, *, settings: Settings) -> None:
        self._settings = settings
        # Shared across turns/threads so multi-turn conversations accumulate.
        self._checkpointer = _CHECKPOINTER

    async def respond(self, req: ConciergeRequest) -> ConciergeReply:
        model = ChatOllama(
            base_url=self._settings.ollama_base_url,
            model=self._settings.ollama_agent_model,
            # Disable the model's hidden chain-of-thought — qwen3's <think>
            # blocks dominate latency across the multi-step ReAct loop.
            reasoning=self._settings.concierge_agent_reasoning,
        )
        tools = [
            StructuredTool.from_function(
                coroutine=t.coroutine,
                name=t.name,
                description=t.description,
                args_schema=t.args_schema,
            )
            for t in req.tools
        ]
        graph = create_react_agent(
            model,
            tools,
            prompt=req.system,
            checkpointer=self._checkpointer,
            pre_model_hook=_trim_history,
        )
        config: RunnableConfig = {
            "configurable": {"thread_id": req.thread_id},
            "recursion_limit": max(4, self._settings.concierge_max_tool_loops * 2),
        }
        inputs: dict[str, Any] = {"messages": [HumanMessage(content=req.message)]}
        result: Any = await graph.ainvoke(inputs, config=config)
        final = result["messages"][-1].content
        return ConciergeReply(text=final if isinstance(final, str) else str(final))
