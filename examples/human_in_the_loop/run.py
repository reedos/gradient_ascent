"""Level 3: human approval. A draft answer is checked against two fixed thresholds: no citation
at all (low confidence) or a dollar figure in the text (high cost, since a number that looks like
a price is the kind of claim worth a person's eyes before it goes anywhere). If either trips, the
run pauses and hands back a checkpoint instead of a final answer, rather than shipping a guess.

`resume` is a second, separate call: it takes that checkpoint, a person's decision, and — for an
edit — their corrected text, and produces the final answer. The pause itself is a fixed rule the
code checks against the draft's own content; the model is never asked whether it wants a person
to look, and it never sees what the reviewer decided until `resume` injects it as plain text. A
design that let the model itself decide to ask for approval (a tool it could choose to call)
would belong at level 4, not here.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from evals.corpus import DEFAULT_CORPUS_DIR, Section, bm25_search, load_sections
from examples.common.model import Embedder, Message, Model
from examples.common.trace import Tracer
from examples.common.types import Answer
from examples.rag.run import CITE_RE

LEVEL = 3
RETRIEVE_K = 4
COST_PATTERN = re.compile(r"\$\d")
DRAFT_SYSTEM = (
    "You answer questions about Halvorsen appliances using only the numbered sources below. If "
    "the sources do not answer the question, say so plainly instead of guessing. End your answer "
    "with a line starting 'Sources:' listing the citations, like 'dw300-manual#3', you used."
)

Reason = Literal["low_confidence", "high_cost"]
Decision = Literal["approve", "edit", "reject"]


@dataclass(frozen=True)
class PendingReview:
    """A paused run: everything a reviewer needs to see, and everything `resume` needs to finish
    once they decide. Every field is a plain value — this is exactly what a real system would
    persist between the pause and whenever a person actually gets to it."""

    question: str
    draft_text: str
    citations: list[str]
    reason: Reason


def _needs_review(draft_text: str, citations: list[str]) -> Reason | None:
    if not citations:
        return "low_confidence"
    if COST_PATTERN.search(draft_text):
        return "high_cost"
    return None


def run(
    question: str,
    model: Model,
    embedder: Embedder | None,
    tracer: Tracer,
    *,
    corpus_dir: Path = DEFAULT_CORPUS_DIR,
) -> Answer | PendingReview:
    del embedder  # retrieval here is keyword search, not a vector index
    sections: dict[str, Section] = load_sections(corpus_dir)
    sources = [s for s, score in bm25_search(sections, question, k=RETRIEVE_K) if score > 0]
    tracer.record(kind="code", decided_by="code", title="Retrieve sources", detail=", ".join(s.cite for s in sources) or "none")

    blocks = "\n\n".join(f"[{s.cite}] {s.title}\n{s.text}" for s in sources)
    completion = model.complete(
        [Message(role="system", content=DRAFT_SYSTEM), Message(role="user", content=f"Sources:\n\n{blocks}\n\nQuestion: {question}")],
        max_tokens=400,
    )
    tracer.record(
        kind="model", decided_by="code", title="Draft an answer", detail=completion.text[:200],
        tokens_in=completion.tokens_in, tokens_out=completion.tokens_out, ms=completion.ms,
    )

    citations = sorted(set(CITE_RE.findall(completion.text.lower())))
    reason = _needs_review(completion.text, citations)
    tracer.record(kind="code", decided_by="code", title="Check confidence and cost thresholds", detail=f"reason={reason or 'none'}")
    if reason is None:
        return Answer(text=completion.text, citations=citations)

    tracer.record(kind="code", decided_by="code", title="Pause for human approval", detail=reason)
    return PendingReview(question=question, draft_text=completion.text, citations=citations, reason=reason)


def resume(pending: PendingReview, decision: Decision, tracer: Tracer, *, note: str = "") -> Answer:
    tracer.record(
        kind="code", decided_by="code", title="Resume from checkpoint with the reviewer's decision",
        detail=f"decision={decision}" + (f" note={note!r}" if note else ""),
    )
    if decision == "approve":
        return Answer(text=pending.draft_text, citations=pending.citations)
    if decision == "edit":
        return Answer(text=note, citations=pending.citations)
    return Answer(text="The reviewer rejected this answer; no answer is given.", citations=[])
