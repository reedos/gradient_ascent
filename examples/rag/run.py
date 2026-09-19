"""Level 2: RAG. Chunk by section, embed, retrieve the top-k, answer with citations.

Every corpus section is already a natural chunk (`evals.corpus.load_sections`), so chunking is
free here; a real document set would need its own splitter. The embedder turns the question and
every chunk into a vector, cosine similarity ranks the chunks, and the top-k go into one prompt
that asks the model to answer using only those sources and to name which ones it used. Retrieval
is fixed: the code always embeds, always takes the top-k, and always asks once. Nothing here is
a model-made choice, so every step is `decided_by: "code"`, same as levels 0 and 1.
"""
from __future__ import annotations

import re
from pathlib import Path

from evals.corpus import DEFAULT_CORPUS_DIR, Section, load_sections
from examples.common.model import Embedder, Message, Model
from examples.common.trace import Tracer
from examples.common.types import Answer

LEVEL = 2
TOP_K = 4
CITE_RE = re.compile(r"[a-z0-9][a-z0-9_-]*#\d+")
SYSTEM_PROMPT = (
    "You answer questions about Halvorsen appliances using only the numbered sources below. "
    "If the sources do not contain the answer, say so instead of guessing. End your answer with "
    "a line starting 'Sources:' listing the citations, like 'dw300-manual#3', that you used."
)


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    return dot  # StubEmbedder and OllamaEmbedder both return unit vectors, so dot == cosine


def _retrieve(question: str, sections: dict[str, Section], embedder: Embedder, k: int) -> list[Section]:
    ordered = list(sections.values())
    vectors = embedder.embed([question] + [f"{s.title}\n{s.text}" for s in ordered])
    query_vec, chunk_vecs = vectors[0], vectors[1:]
    scored = sorted(zip(ordered, chunk_vecs), key=lambda pair: _cosine(query_vec, pair[1]), reverse=True)
    return [section for section, _ in scored[:k]]


def _build_prompt(question: str, sources: list[Section]) -> str:
    blocks = "\n\n".join(f"[{s.cite}] {s.title}\n{s.text}" for s in sources)
    return f"Sources:\n\n{blocks}\n\nQuestion: {question}"


def run(
    question: str,
    model: Model,
    embedder: Embedder,
    tracer: Tracer,
    *,
    corpus_dir: Path = DEFAULT_CORPUS_DIR,
    top_k: int = TOP_K,
) -> Answer:
    sections = load_sections(corpus_dir)
    tracer.record(kind="code", decided_by="code", title="Chunk corpus", detail=f"{len(sections)} sections")
    sources = _retrieve(question, sections, embedder, top_k)
    tracer.record(
        kind="code",
        decided_by="code",
        title="Embed and retrieve top-k",
        detail=", ".join(s.cite for s in sources),
    )
    prompt = _build_prompt(question, sources)
    messages = [Message(role="system", content=SYSTEM_PROMPT), Message(role="user", content=prompt)]
    tracer.record(kind="code", decided_by="code", title="Build prompt with sources", detail=f"{len(sources)} sources")
    completion = model.complete(messages, max_tokens=500)
    tracer.record(
        kind="model",
        decided_by="code",
        title="Ask the model for a cited answer",
        detail=completion.text[:200],
        tokens_in=completion.tokens_in,
        tokens_out=completion.tokens_out,
        ms=completion.ms,
    )
    citations = sorted(set(CITE_RE.findall(completion.text.lower())))
    tracer.record(kind="code", decided_by="code", title="Parse citations", detail=", ".join(citations) or "none")
    return Answer(text=completion.text, citations=citations)
