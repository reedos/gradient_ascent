"""Level 0: no model. Keyword search over the corpus, and nothing else.

`run` scores every section against the question with BM25 (`evals.corpus.bm25_search`) and
returns the best-scoring section verbatim as the answer. There is no drafting, no synthesis, and
no judgment about whether the section actually answers the question: that is the point of this
level. Every step is decided by code, because there is no model in the loop to decide anything.
"""
from __future__ import annotations

from pathlib import Path

from evals.corpus import DEFAULT_CORPUS_DIR, bm25_search, load_sections
from examples.common.model import Embedder, Model
from examples.common.trace import Tracer
from examples.common.types import Answer

LEVEL = 0
NO_MATCH_TEXT = "No section of the corpus scores above zero for this question."


def run(
    question: str,
    model: Model | None,
    embedder: Embedder | None,
    tracer: Tracer,
    *,
    corpus_dir: Path = DEFAULT_CORPUS_DIR,
) -> Answer:
    del model, embedder  # level 0 uses neither; kept for a uniform run() signature
    sections = load_sections(corpus_dir)
    tracer.record(
        kind="code",
        decided_by="code",
        title="Load corpus",
        detail=f"{len(sections)} sections from {corpus_dir}",
    )
    hits = bm25_search(sections, question, k=3)
    tracer.record(
        kind="code",
        decided_by="code",
        title="Keyword search",
        detail=", ".join(f"{s.cite}={score:.2f}" for s, score in hits) or "no sections scored",
    )
    if not hits or hits[0][1] <= 0:
        tracer.record(kind="code", decided_by="code", title="No match above zero", detail=question)
        return Answer(text=NO_MATCH_TEXT, citations=[])
    best, score = hits[0]
    tracer.record(
        kind="code",
        decided_by="code",
        title="Return best section",
        detail=f"{best.cite} score={score:.2f}",
    )
    return Answer(text=best.text, citations=[best.cite])
