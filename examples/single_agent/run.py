"""Level 5: single agent. Plan-and-execute: one call asks the model for a short plan, then a
loop lets the model act on that plan with two tools, revise it as results come in, and decide
for itself when it has enough to answer. Distinct from `examples/agentic_rag/`, which is a
single continuous ReAct-style loop with no separate planning call; see the site's page for the
two papers this shape is drawn from.

The planning call is `kind: "model"` but `decided_by: "code"`, the same rule
`examples/rag/run.py`'s one call follows: the code always makes this call, and always moves on
to the execution loop afterward, regardless of what the plan says. The plan does not itself
select what happens next, so it is not a model decision. Only once the loop starts offering
tools does the model's own output choose the next action -- which tool, with what arguments, or
to stop -- and every one of those steps is `decided_by: "model"`, the same as
`examples/agentic_rag/run.py`'s loop.
"""
from __future__ import annotations

import json
from pathlib import Path

from evals.corpus import DEFAULT_CORPUS_DIR, Section, load_sections
from examples.common.agent_loop import force_final, record_completion
from examples.common import tools as toolkit
from examples.common.model import Embedder, Message, Model, ToolCall
from examples.common.trace import Tracer
from examples.common.types import Answer

LEVEL = 5
MAX_STEPS = 5
MAX_TOKENS = 3000
PLAN_SYSTEM = (
    "You answer questions about Halvorsen appliances. Before doing anything, write a short plan: "
    "2 or 3 numbered steps for how you will use search(query) and lookup_part(part_number) to "
    "answer. Do not call a tool yet; write the plan as plain text only."
)
ACT_SYSTEM = (
    "Here is your plan:\n{plan}\n\nCarry it out one action at a time, using search(query) and "
    "lookup_part(part_number). Revise the plan yourself if a result changes what you still need. "
    "Call no tools, in your final turn, once you are ready to give the final answer."
)
TOOLS = [toolkit.SEARCH_TOOL, toolkit.LOOKUP_PART_TOOL]


def _run_tool(call: ToolCall, sections: dict[str, Section]) -> tuple[str, list[str]]:
    if call.name == "search":
        return toolkit.search_full_text(sections, str(call.arguments.get("query", "")))
    if call.name == "lookup_part":
        return toolkit.part_line(sections, str(call.arguments.get("part_number", "")))
    return toolkit.unknown_tool(call.name)


def run(
    question: str,
    model: Model,
    embedder: Embedder | None,
    tracer: Tracer,
    *,
    corpus_dir: Path = DEFAULT_CORPUS_DIR,
    max_steps: int = MAX_STEPS,
    max_tokens: int = MAX_TOKENS,
) -> Answer:
    del embedder  # a single agent retrieves through its tools, not a vector index
    sections = load_sections(corpus_dir)

    plan_call = model.complete(
        [Message(role="system", content=PLAN_SYSTEM), Message(role="user", content=question)], max_tokens=200
    )
    record_completion(tracer, decided_by="code", title="Model writes a plan", completion=plan_call)
    tokens_used = plan_call.tokens_in + plan_call.tokens_out
    messages = [
        Message(role="system", content=ACT_SYSTEM.format(plan=plan_call.text)),
        Message(role="user", content=question),
    ]

    citations: list[str] = []
    for _ in range(max_steps):
        completion = model.complete(messages, tools=TOOLS, max_tokens=400)
        tokens_used += completion.tokens_in + completion.tokens_out

        if not completion.tool_calls:
            record_completion(tracer, decided_by="model", title="Model stops and answers", completion=completion)
            return Answer.from_text(completion.text, retrieved_sources=citations)

        calls_desc = ", ".join(f"{c.name}({json.dumps(c.arguments, sort_keys=True)})" for c in completion.tool_calls)
        record_completion(tracer, decided_by="model", title="Model acts on the plan", completion=completion, detail=calls_desc)
        messages.append(Message(role="assistant", content=f"[called {calls_desc}]"))
        for call in completion.tool_calls:
            result_text, cites = _run_tool(call, sections)
            citations.extend(cites)
            tracer.record(kind="code", decided_by="code", title=f"Run tool: {call.name}", detail=result_text[:200])
            messages.append(Message(role="user", content=f"Result of {call.name}: {result_text}"))

        if tokens_used >= max_tokens:
            reason = f"token budget reached: {tokens_used} >= {max_tokens}"
            final = force_final(messages, model, tracer, reason=reason, max_tokens=400)
            return Answer.from_text(final.text, retrieved_sources=citations)

    final = force_final(messages, model, tracer, reason=f"step cap reached: {max_steps} steps", max_tokens=400)
    return Answer.from_text(final.text, retrieved_sources=citations)
