"""Level 5: the agent harness. The same StubModel script, replayed through two different harness
configurations, to show that the harness -- not the model -- decides what a run can see and do.

Four pluggable parts, each an ordinary argument to `run` rather than something baked into the
loop: `ToolRegistry` (the tool definitions the model is shown, and an allowlist checked before
any of them runs), a `ContextPolicy` (what of the growing tool-call history actually goes into
the next request), a `Hook` (a chance to veto a call the model already chose), and `max_steps` /
`max_tokens` (the caps). Swap any one of them and the loop, the tools and the model's own script
do not change.

`decided_by` follows the same rule as every other level-5 example (see
`examples/common/trace.py`): which tool to call, its arguments, and the decision to stop are
`decided_by: "model"`. Running a tool, trimming context, and a hook's veto are all
`decided_by: "code"` -- the harness's decisions, never the model's, even though a veto changes
what the model gets to do next just as surely as a missing tool would.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from evals.corpus import DEFAULT_CORPUS_DIR, Section, load_sections
from examples.common import tools as toolkit
from examples.common.agent_loop import force_final, record_completion
from examples.common.model import Embedder, Message, Model, ToolCall, content_text, count_tokens
from examples.common.trace import Tracer
from examples.common.types import Answer

LEVEL = 5
MAX_STEPS = 4
MAX_TOKENS = 3000
SYSTEM = (
    "You answer questions about Halvorsen appliances using search(query) and "
    "lookup_part(part_number). Call no tools once you are ready to answer."
)


@dataclass(frozen=True)
class ToolRegistry:
    """What the model is shown, and what actually runs. `allowed` is the harness's own
    allowlist: a tool the model can see in `definitions` but that is missing from `allowed` is
    refused the same way an unregistered name is -- the registry, not the tool function, decides
    what may run at all."""

    definitions: list[dict]
    allowed: frozenset[str]
    call: Callable[[ToolCall, dict[str, Section]], tuple[str, list[str]]]


def _call_tool(call: ToolCall, sections: dict[str, Section]) -> tuple[str, list[str]]:
    if call.name == "search":
        return toolkit.search_full_text(sections, str(call.arguments.get("query", "")))
    if call.name == "lookup_part":
        return toolkit.part_line(sections, str(call.arguments.get("part_number", "")))
    return toolkit.unknown_tool(call.name)


DEFAULT_REGISTRY = ToolRegistry(
    definitions=[toolkit.SEARCH_TOOL, toolkit.LOOKUP_PART_TOOL],
    allowed=frozenset({"search", "lookup_part"}),
    call=_call_tool,
)

# A context policy takes the full message history the loop has built so far and returns what the
# next request actually sends. Nothing about the loop changes when this changes -- only what the
# model is shown.
ContextPolicy = Callable[[list[Message]], list[Message]]


def keep_everything(messages: list[Message]) -> list[Message]:
    """The generous policy: every tool result stays in context for the rest of the run."""
    return messages


def trim_to_budget(budget_tokens: int) -> ContextPolicy:
    """The tight policy: keeps every non-tool-result message, and as many of the most recent
    tool results as fit under `budget_tokens`, dropping older ones first. Real context policies
    trim the same way -- see this page's Use it lane for how Anthropic describes tool result
    clearing and compaction -- this one trims by a plain token count to keep the point readable
    in a few lines.

    The question is a user message too, and a tool result is recognized here by how its text
    opens. So the search starts after the first assistant turn: a question that happens to begin
    "Result of ..." is never trimmed, because a policy that drops the question leaves the model
    answering something it can no longer see."""

    def policy(messages: list[Message]) -> list[Message]:
        first_turn = next((i for i, m in enumerate(messages) if m.role == "assistant"), len(messages))
        result_idx = [i for i, m in enumerate(messages) if i > first_turn and m.role == "user" and _is_tool_result(m)]
        kept: set[int] = set()
        used = 0
        for i in reversed(result_idx):
            cost = count_tokens(content_text(messages[i].content))
            if used + cost > budget_tokens:
                break
            used += cost
            kept.add(i)
        out = []
        for i, m in enumerate(messages):
            if i in result_idx and i not in kept:
                out.append(Message(role="user", content="[earlier tool result trimmed by the context policy]"))
            else:
                out.append(m)
        return out

    return policy


def _is_tool_result(message: Message) -> bool:
    return isinstance(message.content, str) and message.content.startswith("Result of ")


# A hook sees a tool call the model already chose and decides whether it may run. Returning
# `(False, reason)` vetoes it -- the harness's decision, recorded `decided_by: "code"` -- before
# the registry's allowlist or the tool function ever sees it.
Hook = Callable[[ToolCall], "tuple[bool, str]"]


def allow_everything(call: ToolCall) -> tuple[bool, str]:
    return True, ""


def deny_after(allowed_calls: int) -> Hook:
    """A hook for demonstration and testing: allows the first `allowed_calls` tool calls the
    model attempts, vetoes every one after. A real hook would read the call's own name and
    arguments; this one only counts, to keep the point -- a hook can block an action the model
    already decided to take -- in three lines."""
    seen = {"n": 0}

    def hook(call: ToolCall) -> tuple[bool, str]:
        seen["n"] += 1
        if seen["n"] > allowed_calls:
            return False, f"tool budget of {allowed_calls} call(s) already spent"
        return True, ""

    return hook


def run(
    question: str,
    model: Model,
    embedder: Embedder | None,
    tracer: Tracer,
    *,
    corpus_dir=DEFAULT_CORPUS_DIR,
    registry: ToolRegistry = DEFAULT_REGISTRY,
    context_policy: ContextPolicy = keep_everything,
    hook: Hook = allow_everything,
    max_steps: int = MAX_STEPS,
    max_tokens: int = MAX_TOKENS,
) -> Answer:
    del embedder  # this harness retrieves through its tools, not a vector index
    sections = load_sections(corpus_dir)
    messages = [Message(role="system", content=SYSTEM), Message(role="user", content=question)]
    citations: list[str] = []
    tokens_used = 0

    for _ in range(max_steps):
        completion = model.complete(context_policy(messages), tools=registry.definitions, max_tokens=400)
        tokens_used += completion.tokens_in + completion.tokens_out

        if not completion.tool_calls:
            record_completion(tracer, decided_by="model", title="Model stops and answers", completion=completion)
            return Answer(text=completion.text, citations=sorted(set(citations)))

        calls_desc = ", ".join(f"{c.name}({c.arguments})" for c in completion.tool_calls)
        record_completion(tracer, decided_by="model", title="Model picks an action", completion=completion, detail=calls_desc)
        messages.append(Message(role="assistant", content=f"[called {calls_desc}]"))

        for call in completion.tool_calls:
            allowed, reason = hook(call)
            if not allowed:
                tracer.record(kind="code", decided_by="code", title="Hook vetoes the call", detail=reason)
                messages.append(Message(role="user", content=f"Denied: {call.name} -- {reason}"))
                continue
            if call.name not in registry.allowed:
                result_text, cites = toolkit.unknown_tool(call.name)
            else:
                result_text, cites = registry.call(call, sections)
            citations.extend(cites)
            tracer.record(kind="code", decided_by="code", title=f"Run tool: {call.name}", detail=result_text[:200])
            messages.append(Message(role="user", content=f"Result of {call.name}: {result_text}"))

        if tokens_used >= max_tokens:
            reason = f"token budget reached: {tokens_used} >= {max_tokens}"
            final = force_final(context_policy(messages), model, tracer, reason=reason, max_tokens=400)
            return Answer(text=final.text, citations=sorted(set(citations)))

    final = force_final(context_policy(messages), model, tracer, reason=f"step cap reached: {max_steps} steps", max_tokens=400)
    return Answer(text=final.text, citations=sorted(set(citations)))
