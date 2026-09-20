"""Level 4: function calling. The model may call `search(query)` or `lookup_part(part_number)`,
at most once; the code runs whichever tool was called and asks for a final answer.

This is the first level with a real decision in it: the model chooses whether to call a tool at
all, and if so, which one and with what argument. That choice is `decided_by: "model"`. Running
the tool is still the code's job (`decided_by: "code"`), and so is the second call that asks for
a final answer once the tool result is in hand: the code always makes that call when a tool ran,
regardless of what the tool returned.
"""
from __future__ import annotations

import json
from pathlib import Path

from evals.corpus import DEFAULT_CORPUS_DIR, Section, load_sections
from examples.common import tools as toolkit
from examples.common.model import Embedder, Message, Model, ToolCall
from examples.common.trace import Tracer
from examples.common.types import Answer

LEVEL = 4
SYSTEM_PROMPT = (
    "You answer questions about Halvorsen appliances. You may call one tool, at most once: "
    "search(query) for a keyword search over the documents, or lookup_part(part_number) for a "
    "specific HLV part number. If you already know the answer, or no tool would help, answer "
    "directly without calling one."
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
) -> Answer:
    del embedder  # level 4 retrieves through its tools, not a vector index
    sections = load_sections(corpus_dir)
    messages = [Message(role="system", content=SYSTEM_PROMPT), Message(role="user", content=question)]
    tracer.record(kind="code", decided_by="code", title="Build prompt with tool definitions", detail="search, lookup_part")

    first = model.complete(messages, tools=TOOLS, max_tokens=300)
    if not first.tool_calls:
        tracer.record(
            kind="model",
            decided_by="model",
            title="Model answers directly, no tool call",
            detail=first.text[:200],
            tokens_in=first.tokens_in,
            tokens_out=first.tokens_out,
            ms=first.ms,
        )
        return Answer.from_text(first.text)

    call = first.tool_calls[0]
    # the prompt allows one call; if the model asked for more, the code drops the rest, and the
    # trace has to say so rather than quietly showing a tidier run than the one that happened
    dropped = "" if len(first.tool_calls) == 1 else f" (dropped {len(first.tool_calls) - 1} further call(s))"
    tracer.record(
        kind="model",
        decided_by="model",
        title=f"Model calls {call.name}",
        detail=json.dumps(call.arguments, sort_keys=True) + dropped,
        tokens_in=first.tokens_in,
        tokens_out=first.tokens_out,
        ms=first.ms,
    )
    result_text, citations = _run_tool(call, sections)
    tracer.record(kind="code", decided_by="code", title=f"Run tool: {call.name}", detail=result_text[:200])

    follow_up = messages + [
        Message(role="assistant", content=f"[called {call.name}({json.dumps(call.arguments)})]"),
        Message(role="user", content=f"Tool result:\n{result_text}\n\nNow answer the question: {question}"),
    ]
    final = model.complete(follow_up, max_tokens=400)
    tracer.record(
        kind="model",
        decided_by="code",
        title="Ask for a final answer",
        detail=final.text[:200],
        tokens_in=final.tokens_in,
        tokens_out=final.tokens_out,
        ms=final.ms,
    )
    return Answer.from_text(final.text, retrieved_sources=citations)
