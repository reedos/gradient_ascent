"""Level 2: knowledge graphs. Extract (subject, relation, object) triples from two documents,
store them in a small dict-based graph, and answer a two-hop question by walking two edges --
a part number to the model it fits, that model to its warranty class -- showing the path as
provenance instead of a single retrieved passage.

Extraction is one model call per document, same shape as GraphRAG's own indexing step: an LLM
reads the text and states the entities and relationships in it, as documented by Microsoft
(the page's "What it is" prose cites this). The code always makes exactly these two extraction
calls, in this order, and always walks the graph the same way afterward; nothing here is decided
by the model, only filled in by it. `decided_by` is "code" on every step, same as levels 0-3 in
`examples/common/trace.py`.
"""
from __future__ import annotations

import re
from pathlib import Path

from evals.corpus import DEFAULT_CORPUS_DIR, load_sections
from examples.common.model import Embedder, Message, Model
from examples.common.trace import Tracer
from examples.common.types import Answer

LEVEL = 2
PART_RE = re.compile(r"HLV-\d{4}")
DEFAULT_PART = "HLV-5520"
# The two sections a real GraphRAG-style indexer would extract from for this question: fitment
# facts (which part fits which model) and warranty facts (which model gets which coverage).
SOURCE_CITES = ("parts-list#3", "warranty-policy#2")
EXTRACT_SYSTEM = (
    "Extract facts from the document below as triples, one per line, exactly in the form "
    "'subject | relation | object'. State only facts the document actually says. No prose."
)

Triple = tuple[str, str, str]


def _extract_triples(cite: str, text: str, model: Model, tracer: Tracer) -> list[tuple[Triple, str]]:
    completion = model.complete(
        [Message(role="system", content=EXTRACT_SYSTEM), Message(role="user", content=text)], max_tokens=300
    )
    triples: list[tuple[Triple, str]] = []
    for line in completion.text.splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) == 3 and all(parts):
            triples.append(((parts[0], parts[1], parts[2]), cite))
    tracer.record(
        kind="model",
        decided_by="code",
        title=f"Extract triples from {cite}",
        detail="; ".join(f"{s} {r} {o}" for (s, r, o), _ in triples) or "none",
        tokens_in=completion.tokens_in,
        tokens_out=completion.tokens_out,
        ms=completion.ms,
    )
    return triples


def _two_hop(graph: dict[str, list[tuple[str, str, str]]], start: str, hop1: str, hop2: str):
    """Walk start --hop1--> mid --hop2--> value. Returns (mid, value, cite1, cite2) or None."""
    for rel1, mid, cite1 in graph.get(start, []):
        if rel1 != hop1:
            continue
        for rel2, value, cite2 in graph.get(mid, []):
            if rel2 == hop2:
                return mid, value, cite1, cite2
    return None


def run(
    question: str,
    model: Model,
    embedder: Embedder | None,
    tracer: Tracer,
    *,
    corpus_dir: Path = DEFAULT_CORPUS_DIR,
) -> Answer:
    del embedder  # nothing is embedded here; the graph is walked by exact key, not by similarity
    part_number = next(iter(PART_RE.findall(question)), DEFAULT_PART)
    sections = load_sections(corpus_dir)
    graph: dict[str, list[tuple[str, str, str]]] = {}
    for cite in SOURCE_CITES:
        for (subject, relation, obj), source in _extract_triples(cite, sections[cite].text, model, tracer):
            graph.setdefault(subject, []).append((relation, obj, source))
    tracer.record(
        kind="code",
        decided_by="code",
        title="Build the graph from the extracted triples",
        detail=f"{sum(len(edges) for edges in graph.values())} edges over {len(graph)} subjects",
    )
    hop = _two_hop(graph, part_number, "fits", "warranty_class")
    if hop is None:
        tracer.record(kind="code", decided_by="code", title="No two-hop path found", detail=part_number)
        return Answer(text=f"No warranty class found for {part_number} in the graph.", citations=[])
    model_name, warranty_class, cite1, cite2 = hop
    tracer.record(
        kind="code",
        decided_by="code",
        title="Walk the two-hop path",
        detail=f"{part_number} --fits--> {model_name} --warranty_class--> {warranty_class}",
    )
    text = f"{part_number} fits {model_name} [{cite1}], which carries warranty class: {warranty_class} [{cite2}]."
    return Answer(text=text, citations=[cite1, cite2])
