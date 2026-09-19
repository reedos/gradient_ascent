"""Level 5: agentic RAG. A loop with `search` and `read` tools that runs until the model stops
calling tools, capped by a hard step limit and a hard token budget.

`search(query)` returns section titles and citations only, not full text, so the model has to
call `read(cite)` before it can quote or cite a section with confidence: this is what makes the
loop actually iterative rather than a single retrieve-then-answer pass. Every tool call, and the
decision to stop calling tools, belongs to the model (`decided_by: "model"`); running a tool and
enforcing the caps belong to the code. When a cap is hit before the model stops on its own, the
code forces one last no-tools call for a final answer, which is a `decided_by: "code"` step.
"""
from __future__ import annotations

import json
from pathlib import Path

from evals.corpus import DEFAULT_CORPUS_DIR, Section, load_sections
from examples.common.agent_loop import force_final
from examples.common import tools as toolkit
from examples.common.model import Embedder, Message, Model, ToolCall
from examples.common.trace import Tracer
from examples.common.types import Answer

LEVEL = 5
MAX_STEPS = 6
MAX_TOKENS = 4000
SYSTEM_PROMPT = (
    "You answer questions about Halvorsen appliances. You may call two tools, search(query) and "
    "read(cite), as many times as you need. search returns section titles and citations only, "
    "not full text; call read on a citation to get its full text before relying on it. Call no "
    "tools, in your final turn, once you are ready to give the final answer."
)
TOOLS = [toolkit.SEARCH_TITLES_TOOL, toolkit.READ_TOOL]


def _run_tool(call: ToolCall, sections: dict[str, Section]) -> tuple[str, list[str]]:
    if call.name == "search":
        return toolkit.search_titles(sections, str(call.arguments.get("query", "")))
    if call.name == "read":
        return toolkit.read_section(sections, str(call.arguments.get("cite", "")))
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
    del embedder  # level 5 retrieves through its tools, not a vector index
    sections = load_sections(corpus_dir)
    messages = [Message(role="system", content=SYSTEM_PROMPT), Message(role="user", content=question)]
    tracer.record(kind="code", decided_by="code", title="Build prompt with tool definitions", detail="search, read")

    citations: list[str] = []
    tokens_used = 0
    for _ in range(max_steps):
        completion = model.complete(messages, tools=TOOLS, max_tokens=400)
        tokens_used += completion.tokens_in + completion.tokens_out

        if not completion.tool_calls:
            tracer.record(
                kind="model",
                decided_by="model",
                title="Model stops and answers",
                detail=completion.text[:200],
                tokens_in=completion.tokens_in,
                tokens_out=completion.tokens_out,
                ms=completion.ms,
            )
            return Answer(text=completion.text, citations=sorted(set(citations)))

        calls_desc = ", ".join(f"{c.name}({json.dumps(c.arguments, sort_keys=True)})" for c in completion.tool_calls)
        tracer.record(
            kind="model",
            decided_by="model",
            title="Model calls tool(s)",
            detail=calls_desc,
            tokens_in=completion.tokens_in,
            tokens_out=completion.tokens_out,
            ms=completion.ms,
        )
        messages.append(Message(role="assistant", content=f"[called {calls_desc}]"))
        for call in completion.tool_calls:
            result_text, cites = _run_tool(call, sections)
            citations.extend(cites)
            tracer.record(kind="code", decided_by="code", title=f"Run tool: {call.name}", detail=result_text[:200])
            messages.append(Message(role="user", content=f"Result of {call.name}: {result_text}"))

        if tokens_used >= max_tokens:
            final = force_final(messages, model, tracer, reason=f"token budget reached: {tokens_used} >= {max_tokens}", max_tokens=400)
            return Answer(text=final.text, citations=sorted(set(citations)))

    final = force_final(messages, model, tracer, reason=f"step cap reached: {max_steps} steps", max_tokens=400)
    return Answer(text=final.text, citations=sorted(set(citations)))
