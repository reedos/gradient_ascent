"""Level 6: agent graphs. A graph runner in the same shape as
`examples/workflow_graphs/run.py` -- nodes are plain functions over shared state, and the runner
writes a checkpoint after every node -- except one node here is a supervisor whose own model
call picks the next node from an explicit allowlist, `ALLOWED_HANDOFFS`. That is the one
difference from a workflow graph and the only place `decided_by="model"` appears in this file.

Code still runs every node, checkpoints every one, and never calls a node the supervisor names
that is not in the allowlist -- an out-of-list answer is recorded and the graph is forced to
`write` instead of being handed to `NODES[<whatever the model said>]`, which would raise on
anything the model invented. `MAX_RESEARCH_HOPS` caps how many times the supervisor may hand off
to `research` before code forces `write` on its own, without asking the model again.
"""
from __future__ import annotations

from pathlib import Path

from evals.corpus import DEFAULT_CORPUS_DIR, Section, bm25_search, load_sections
from examples.common.model import Embedder, Message, Model
from examples.common.trace import Tracer
from examples.common.types import Answer

LEVEL = 6
MAX_RESEARCH_HOPS = 4
ALLOWED_HANDOFFS = frozenset({"research", "write"})
SUPERVISOR_SYSTEM = (
    "You direct a two-agent team answering a question about Halvorsen appliances. Findings so "
    "far:\n{findings}\n\nReply with exactly one word: 'research' if more information is needed, "
    "or 'write' if there is enough to answer the question now."
)
WRITE_SYSTEM = (
    "Write the final answer to the question using only the findings below. Cite every source you "
    "rely on. End with a line starting 'Sources:'."
)


def _findings_block(findings: list[tuple[str, str]]) -> str:
    return "\n".join(f"[{cite}] {text}" for cite, text in findings) or "(none yet)"


def _supervisor_choose(question: str, findings: list[tuple[str, str]], model: Model, tracer: Tracer) -> str:
    prompt = f"Question: {question}\n\n{SUPERVISOR_SYSTEM.format(findings=_findings_block(findings))}"
    completion = model.complete([Message(role="user", content=prompt)], max_tokens=10)
    choice = completion.text.strip().lower()
    tracer.record(
        kind="model",
        decided_by="model",
        title="Supervisor picks the next agent",
        detail=f"-> {choice!r}",
        tokens_in=completion.tokens_in,
        tokens_out=completion.tokens_out,
        ms=completion.ms,
    )
    return choice


def _node_research(question: str, sections: dict[str, Section], findings: list[tuple[str, str]], tracer: Tracer) -> None:
    """Search the whole corpus for the original question, skipping any section already in
    `findings`, so a second hop naturally turns up the next-best match instead of repeating the
    first one."""
    already = {cite for cite, _ in findings}
    for section, score in bm25_search(sections, question, k=len(sections)):
        if score > 0 and section.cite not in already:
            findings.append((section.cite, section.text[:400]))
            tracer.record(
                kind="code", decided_by="code", title="Checkpoint after 'research'",
                detail=f"{section.cite}: {section.text[:80]}",
            )
            return
    tracer.record(kind="code", decided_by="code", title="Checkpoint after 'research'", detail="no new section found")


def _node_write(question: str, findings: list[tuple[str, str]], model: Model, tracer: Tracer) -> str:
    prompt = f"Question: {question}\n\nFindings:\n{_findings_block(findings)}\n\n{WRITE_SYSTEM}"
    completion = model.complete([Message(role="user", content=prompt)], max_tokens=400)
    tracer.record(
        kind="model", decided_by="code", title="Checkpoint after 'write'", detail=completion.text[:200],
        tokens_in=completion.tokens_in, tokens_out=completion.tokens_out, ms=completion.ms,
    )
    return completion.text


def run(
    question: str,
    model: Model,
    embedder: Embedder | None,
    tracer: Tracer,
    *,
    corpus_dir: Path = DEFAULT_CORPUS_DIR,
    max_research_hops: int = MAX_RESEARCH_HOPS,
) -> Answer:
    del embedder  # retrieval here is keyword search, like workflow_graphs
    sections = load_sections(corpus_dir)
    findings: list[tuple[str, str]] = []
    hops = 0

    while True:
        if hops >= max_research_hops:
            tracer.record(
                kind="code", decided_by="code", title="Hop cap reached",
                detail=f"{hops} research hops >= {max_research_hops}; forcing write",
            )
            choice = "write"
        else:
            choice = _supervisor_choose(question, findings, model, tracer)
            if choice not in ALLOWED_HANDOFFS:
                tracer.record(
                    kind="code", decided_by="code", title="Handoff blocked",
                    detail=f"{choice!r} is not in the allowlist {sorted(ALLOWED_HANDOFFS)}; forcing write",
                )
                choice = "write"

        if choice == "write":
            answer_text = _node_write(question, findings, model, tracer)
            break

        hops += 1
        _node_research(question, sections, findings, tracer)

    citations = sorted({cite for cite, _ in findings})
    return Answer(text=answer_text, citations=citations)
