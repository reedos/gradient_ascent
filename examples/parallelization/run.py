"""Level 3: parallel calls, sectioning. Retrieve a fixed set of candidate sections, ask the model
to answer from each one ALONE, at the same time, then combine deterministically: keep whichever
sections actually answered part of the question, in retrieval order, and cite each one directly.

Sectioning here means splitting the *answering* step across sections rather than splitting it
across sub-questions: each call sees exactly one passage and never learns what the other calls
saw, so nothing here can compare or reconcile what two sections said (see the failure mode on
the page). The number of parallel calls, which sections each one gets, and how their results are
combined are all fixed before the first call goes out — the model never sees the other branches
and never decides how many there are.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from evals.corpus import DEFAULT_CORPUS_DIR, Section, bm25_search, load_sections
from examples.common.model import Completion, Embedder, Message, Model
from examples.common.trace import Tracer
from examples.common.types import Answer

LEVEL = 3
CANDIDATES_K = 3
NO_ANSWER = "NOT IN THIS SECTION"
PER_SECTION_SYSTEM = (
    "You are given exactly one source passage about Halvorsen appliances, and a question that "
    "may have more than one part. If this passage answers all or part of the question, answer "
    "briefly using only this passage. If it answers none of the question, reply with exactly "
    f"'{NO_ANSWER}' and nothing else."
)


def _answer_from_one_section(question: str, section: Section, model: Model) -> Completion:
    prompt = f"Passage [{section.cite}] {section.title}:\n{section.text}\n\nQuestion: {question}"
    return model.complete([Message(role="system", content=PER_SECTION_SYSTEM), Message(role="user", content=prompt)], max_tokens=200)


def run(
    question: str,
    model: Model,
    embedder: Embedder | None,
    tracer: Tracer,
    *,
    corpus_dir: Path = DEFAULT_CORPUS_DIR,
    k: int = CANDIDATES_K,
) -> Answer:
    del embedder  # candidates come from keyword search, not a vector index
    sections = load_sections(corpus_dir)
    candidates = [s for s, score in bm25_search(sections, question, k=k) if score > 0]
    tracer.record(
        kind="code", decided_by="code", title="Pick sections to answer in parallel",
        detail=", ".join(s.cite for s in candidates) or "none",
    )

    # .map submits every call to the pool at once and yields results back in candidate order,
    # so the calls run concurrently but the code below never has to sort them: determinism comes
    # from retrieval order, not from whichever call happens to finish first.
    with ThreadPoolExecutor(max_workers=max(1, len(candidates))) as pool:
        completions = list(pool.map(lambda s: _answer_from_one_section(question, s, model), candidates))

    for section, completion in zip(candidates, completions):
        tracer.record(
            kind="model", decided_by="code", title=f"Answer from {section.cite} alone", detail=completion.text[:200],
            tokens_in=completion.tokens_in, tokens_out=completion.tokens_out, ms=completion.ms,
        )

    used = [(s, c) for s, c in zip(candidates, completions) if NO_ANSWER not in c.text.upper()]
    tracer.record(
        kind="code", decided_by="code", title="Combine the sections that answered",
        detail=f"{len(used)} of {len(candidates)} sections answered part of the question",
    )
    if not used:
        return Answer(text="None of the retrieved sections answered the question.", citations=[])
    combined = " ".join(c.text.strip() for _, c in used)
    return Answer(text=combined, citations=sorted({s.cite for s, _ in used}))
