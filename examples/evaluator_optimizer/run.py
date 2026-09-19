"""Level 3: write and check (evaluator-optimizer). One model call drafts an answer; a second,
separate call checks the draft against one explicit criterion (does every citation it claims
actually appear among the sources it was given) and returns feedback, not a vibe; if the check
fails, a third call revises using that feedback, and the loop repeats.

The loop's cap is in code (`max_revisions`), not in the model: the model can make the loop run
its full length by continuing to fail its own check, but it cannot make the loop run one
iteration longer than the code allows. The checker is asked for one written-down thing (which
citations are unsupported), not "is this good" — a vaguer prompt would let its own judgment drift
between calls the way the drafter's did, checking nothing.
"""
from __future__ import annotations

from pathlib import Path

from evals.corpus import DEFAULT_CORPUS_DIR, Section, bm25_search, load_sections
from examples.common.model import Embedder, Message, Model
from examples.common.trace import Tracer
from examples.common.types import Answer
from examples.rag.run import CITE_RE

LEVEL = 3
RETRIEVE_K = 4
MAX_REVISIONS = 2
PASS_TOKEN = "ALL CITATIONS SUPPORTED"
DRAFT_SYSTEM = (
    "You answer questions about Halvorsen appliances using only the numbered sources below. End "
    "your answer with a line starting 'Sources:' listing the citations, like 'dw300-manual#3', "
    "that you used."
)
CHECK_SYSTEM = (
    "You check a draft answer against the source passages it was given. List every citation the "
    "draft claims that does NOT actually appear among the sources below, one per line, as "
    f"'MISSING: <citation>'. If every citation the draft claims is one of the sources, reply with "
    f"exactly '{PASS_TOKEN}' and nothing else."
)
REVISE_SYSTEM = (
    "Revise your previous answer to fix the citation problems named below. Use only the sources "
    "given. Keep the same 'Sources:' line format."
)


def _sources_block(sources: list[Section]) -> str:
    return "\n\n".join(f"[{s.cite}] {s.title}\n{s.text}" for s in sources)


def _draft(question: str, sources: list[Section], model: Model, tracer: Tracer) -> str:
    prompt = f"Sources:\n\n{_sources_block(sources)}\n\nQuestion: {question}"
    completion = model.complete([Message(role="system", content=DRAFT_SYSTEM), Message(role="user", content=prompt)], max_tokens=400)
    tracer.record(
        kind="model", decided_by="code", title="Draft an answer", detail=completion.text[:200],
        tokens_in=completion.tokens_in, tokens_out=completion.tokens_out, ms=completion.ms,
    )
    return completion.text


def _check(draft_text: str, sources: list[Section], model: Model, tracer: Tracer) -> str | None:
    """None means the draft passed. Otherwise, the checker's own feedback text."""
    prompt = f"Sources:\n\n{_sources_block(sources)}\n\nDraft answer:\n{draft_text}"
    completion = model.complete([Message(role="system", content=CHECK_SYSTEM), Message(role="user", content=prompt)], max_tokens=200)
    verdict = completion.text.strip()
    tracer.record(
        kind="model", decided_by="code", title="Check citations against the sources", detail=verdict[:200],
        tokens_in=completion.tokens_in, tokens_out=completion.tokens_out, ms=completion.ms,
    )
    return None if PASS_TOKEN in verdict.upper() else verdict


def _revise(question: str, draft_text: str, feedback: str, sources: list[Section], model: Model, tracer: Tracer) -> str:
    prompt = f"Sources:\n\n{_sources_block(sources)}\n\nQuestion: {question}\n\nPrevious answer:\n{draft_text}\n\nProblems to fix:\n{feedback}"
    completion = model.complete([Message(role="system", content=REVISE_SYSTEM), Message(role="user", content=prompt)], max_tokens=400)
    tracer.record(
        kind="model", decided_by="code", title="Revise using the checker's feedback", detail=completion.text[:200],
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
    max_revisions: int = MAX_REVISIONS,
) -> Answer:
    del embedder  # retrieval here is keyword search, not a vector index
    sections = load_sections(corpus_dir)
    sources = [s for s, score in bm25_search(sections, question, k=RETRIEVE_K) if score > 0]
    tracer.record(kind="code", decided_by="code", title="Retrieve sources", detail=", ".join(s.cite for s in sources) or "none")

    draft_text = _draft(question, sources, model, tracer)
    feedback = _check(draft_text, sources, model, tracer)
    revisions = 0
    while feedback is not None and revisions < max_revisions:
        draft_text = _revise(question, draft_text, feedback, sources, model, tracer)
        revisions += 1
        feedback = _check(draft_text, sources, model, tracer)
    if feedback is not None:
        tracer.record(
            kind="code", decided_by="code", title="Stop: revision cap reached",
            detail=f"shipping a draft that still fails its own check after {revisions} revision(s)",
        )

    citations = sorted(set(CITE_RE.findall(draft_text.lower())))
    return Answer(text=draft_text, citations=citations)
