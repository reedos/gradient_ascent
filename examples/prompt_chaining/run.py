"""Level 3: prompt chaining. Four fixed steps, in this order, every time: rewrite the question
into search queries, retrieve for each one, draft an answer from what came back, then check the
draft's citations against what was actually retrieved.

The model is called twice (rewrite, draft), but the code decides the sequence and always runs
all four steps regardless of what either model call returns; the model never picks the next
step. That is what separates this from level 4: here the model only fills in the content of
steps the code already committed to running.
"""
from __future__ import annotations

from pathlib import Path

from evals.corpus import DEFAULT_CORPUS_DIR, Section, bm25_search, load_sections
from examples.common.model import Embedder, Message, Model
from examples.common.trace import Tracer
from examples.common.types import Answer
from examples.common.types import cited_sources

LEVEL = 3
MAX_QUERIES = 3
PER_QUERY_K = 2
REWRITE_SYSTEM = (
    "Break the user's question into 1 to 3 short search queries over Halvorsen appliance "
    "documents, one per line, plain text, no numbering."
)
DRAFT_SYSTEM = (
    "You answer questions about Halvorsen appliances using only the numbered sources below. "
    "If the sources do not contain the answer, say so instead of guessing. End your answer with "
    "a line starting 'Sources:' listing the citations, like 'dw300-manual#3', that you used."
)


def _rewrite_queries(question: str, model: Model, tracer: Tracer) -> list[str]:
    completion = model.complete([Message(role="system", content=REWRITE_SYSTEM), Message(role="user", content=question)], max_tokens=150)
    queries = [line.strip() for line in completion.text.splitlines() if line.strip()][:MAX_QUERIES] or [question]
    tracer.record(
        kind="model",
        decided_by="code",
        title="Rewrite into search queries",
        detail="; ".join(queries),
        tokens_in=completion.tokens_in,
        tokens_out=completion.tokens_out,
        ms=completion.ms,
    )
    return queries


def _retrieve(queries: list[str], sections: dict[str, Section], tracer: Tracer) -> list[Section]:
    seen: dict[str, Section] = {}
    for query in queries:
        for section, score in bm25_search(sections, query, k=PER_QUERY_K):
            if score > 0:
                seen[section.cite] = section
    sources = list(seen.values())
    tracer.record(kind="code", decided_by="code", title="Retrieve for each query", detail=", ".join(seen.keys()) or "none")
    return sources


def _draft(question: str, sources: list[Section], model: Model, tracer: Tracer):
    blocks = "\n\n".join(f"[{s.cite}] {s.title}\n{s.text}" for s in sources)
    prompt = f"Sources:\n\n{blocks}\n\nQuestion: {question}"
    completion = model.complete([Message(role="system", content=DRAFT_SYSTEM), Message(role="user", content=prompt)], max_tokens=500)
    tracer.record(
        kind="model",
        decided_by="code",
        title="Draft answer from sources",
        detail=completion.text[:200],
        tokens_in=completion.tokens_in,
        tokens_out=completion.tokens_out,
        ms=completion.ms,
    )
    return completion


def _check_citations(draft_text: str, sources: list[Section], tracer: Tracer) -> list[str]:
    retrieved = {s.cite for s in sources}
    claimed = set(cited_sources(draft_text))
    grounded = sorted(claimed & retrieved)
    dropped = sorted(claimed - retrieved)
    tracer.record(
        kind="code",
        decided_by="code",
        title="Check citations against retrieval",
        detail=f"kept {grounded}" + (f", dropped ungrounded {dropped}" if dropped else ""),
    )
    return grounded


def run(question: str, model: Model, embedder: Embedder | None, tracer: Tracer, *, corpus_dir: Path = DEFAULT_CORPUS_DIR) -> Answer:
    del embedder  # level 3 retrieves by keyword, not by vector
    sections = load_sections(corpus_dir)
    queries = _rewrite_queries(question, model, tracer)
    sources = _retrieve(queries, sections, tracer)
    completion = _draft(question, sources, model, tracer)
    citations = _check_citations(completion.text, sources, tracer)
    return Answer(text=completion.text, citations=citations, retrieved_sources=[s.cite for s in sources])
