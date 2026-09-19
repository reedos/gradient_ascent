"""Level 2: embeddings and search. Index the corpus once, then rank it against a query two ways
-- by embedding similarity and by keyword (BM25) -- and report where they agree and disagree.

There is no model call and nothing is retrieved for an answer: this level is the search step RAG
is built on, not an answer. Every step is `decided_by: "code"`; there is no model in this loop
to decide anything.

Honesty check, since it matters for what this example can and cannot show: `StubEmbedder`
(`examples/common/model.py`) hashes words into a fixed number of buckets and counts them -- a bag
of words, not a trained model. It has no notion that "quiet" and "dBA" are related unless the
words themselves overlap, so it cannot do what a real embedding model is for: finding the
passage that answers a question when the wording does not match. A real embedding model
(`Embedder.embed` has an `OllamaEmbedder` implementation behind the same interface) is what
closes that gap. What this example does show honestly: chunking, building an index once,
ranking a query against it by vector similarity, and comparing that against keyword search on
the same query.
"""
from __future__ import annotations

from pathlib import Path

from evals.corpus import DEFAULT_CORPUS_DIR, Section, bm25_search, load_sections
from examples.common.model import Embedder, Model
from examples.common.trace import Tracer
from examples.common.types import Answer

LEVEL = 2
TOP_K = 3


def _cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity, divided by both lengths rather than assuming unit vectors. `StubEmbedder`
    normalizes, so for it this equals a bare dot product; `OllamaEmbedder` returns whatever the
    server sends, and against unnormalized vectors a dot product is not a cosine."""
    dot = sum(x * y for x, y in zip(a, b))
    norms = (sum(x * x for x in a) ** 0.5) * (sum(y * y for y in b) ** 0.5)
    return dot / norms if norms else 0.0


def _semantic_search(query: str, sections: dict[str, Section], embedder: Embedder, k: int) -> list[tuple[Section, float]]:
    """Build the index (embed every chunk) and rank it against one embedded query."""
    ordered = list(sections.values())
    vectors = embedder.embed([query] + [f"{s.title}\n{s.text}" for s in ordered])
    query_vec, chunk_vecs = vectors[0], vectors[1:]
    scores = [_cosine(query_vec, v) for v in chunk_vecs]
    scored = sorted(zip(ordered, scores), key=lambda pair: pair[1], reverse=True)
    return scored[:k]


def _compare(semantic: list[tuple[Section, float]], keyword: list[tuple[Section, float]]) -> str:
    sem_cites = [s.cite for s, _ in semantic]
    key_cites = [s.cite for s, _ in keyword]
    overlap = sorted(set(sem_cites) & set(key_cites))
    return (
        f"Semantic top-{len(sem_cites)}: {', '.join(sem_cites)}. "
        f"Keyword top-{len(key_cites)}: {', '.join(key_cites)}. "
        f"{len(overlap)} of {len(sem_cites)} sections agree: {', '.join(overlap) or 'none'}."
    )


def run(
    query: str,
    model: Model | None,
    embedder: Embedder,
    tracer: Tracer,
    *,
    corpus_dir: Path = DEFAULT_CORPUS_DIR,
    k: int = TOP_K,
) -> Answer:
    del model  # this level searches; it does not answer
    sections = load_sections(corpus_dir)
    tracer.record(kind="code", decided_by="code", title="Chunk the corpus", detail=f"{len(sections)} sections")
    semantic = _semantic_search(query, sections, embedder, k)
    tracer.record(
        kind="code",
        decided_by="code",
        title="Embed the index and rank it by similarity",
        detail=", ".join(f"{s.cite}={score:.2f}" for s, score in semantic),
    )
    keyword = bm25_search(sections, query, k=k)
    tracer.record(
        kind="code",
        decided_by="code",
        title="Rank the same query by keyword (BM25)",
        detail=", ".join(f"{s.cite}={score:.2f}" for s, score in keyword),
    )
    summary = _compare(semantic, keyword)
    tracer.record(kind="code", decided_by="code", title="Compare the two result sets", detail=summary)
    return Answer(text=summary, citations=[s.cite for s, _ in semantic])
