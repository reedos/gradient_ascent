"""Level 2: ask the datasheet. RAG over the documents an engineer already has for one board (a
datasheet, a test specification, four instrument manuals, a bill of materials, design-review
rules and an engineering change notice), with the answer returned in a fixed shape: a value, the
board revision it holds for, and the sources it came from.

Retrieval is the same top-k-by-cosine-similarity RAG uses (`examples/rag/run.py`); what differs
is what the prompt asks for and what code checks in the reply. The bench's datasheet states a
maximum input voltage of 36.0 V; ECN-2608-04 supersedes that to 32.0 V for board revisions A and
B (`docs/THE-BENCH.md`). The two documents share enough words -- "maximum", "input voltage",
"recommended operating conditions", the revision letters -- that one embedding search over the
whole corpus returns both sections without a second, dependent search. What a plain-text answer
can still get wrong is staying silent about which revision it applies to, or citing the datasheet
without the notice that overrides it, so the model is asked for JSON with a required
`applies_to_revision` field rather than free prose, and code checks that the field is filled in,
that every citation in the reply was actually retrieved, and that a reply citing the superseded
datasheet section also cites the notice that supersedes it whenever that notice was retrieved
(`SUPERSEDED_BY`) -- retrying once with the validation error appended if any of that fails.
Retrieval, prompting, validating and the one retry are all fixed by code; the model only ever
composes the answer inside that structure, so every step is `decided_by: "code"`, the same as
plain RAG.
"""
from __future__ import annotations

import json
from pathlib import Path

from evals.bench import BENCH_CORPUS_DIR
from evals.corpus import Section, load_sections
from examples.common.model import Embedder, Message, Model
from examples.common.trace import Tracer
from examples.common.types import Answer

LEVEL = 2
TOP_K = 8
MAX_RETRIES = 1
REQUIRED_FIELDS = ("answer", "applies_to_revision", "citations")
SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "applies_to_revision": {"type": "string"},
        "citations": {"type": "array", "items": {"type": "string"}},
    },
    "required": list(REQUIRED_FIELDS),
}
#: `docs/THE-BENCH.md`: ECN-2608-04 supersedes this datasheet section's input-voltage figure, for
#: board revisions A and B. A reply that cites the datasheet section without the notice that
#: changes it, when the notice itself was retrieved, is exactly the wrong answer this recipe
#: exists to catch: correct-looking, and wrong for the board actually in the fixture.
SUPERSEDED_BY = {"srb5030-datasheet#3": "ecn-2608-04#1"}
SYSTEM_PROMPT = (
    "You answer questions about the Orbeck SRB-5030 board using only the numbered sources "
    "below: a datasheet, a test specification, programming manuals and other engineering "
    "documents, including any engineering change notice (ECN) among them. An ECN can supersede "
    "a number the datasheet states, for the board revisions it names; where one of your sources "
    "does that, answer with the superseding number, not the datasheet's. Reply as JSON matching "
    f"this schema, with no other text and no markdown fences: {json.dumps(SCHEMA)}. "
    '`applies_to_revision` must name which board revision the answer holds for (for example '
    '"A and B", "C", or "all revisions" when nothing in the sources makes the answer revision '
    "specific) and must never be left blank. `citations` must list, as `file#section`, every "
    "source the answer depends on, including a superseding ECN whenever one applies."
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


def _validate(record: dict, retrieved: set[str]) -> list[str]:
    """What a reply has to have before code will hand it back as the answer.

    Two of these checks exist because of what this bench is for, not because of JSON schemas in
    general: a citation has to be one of the sources code actually retrieved (a model cannot cite
    a document it was never shown), and `applies_to_revision` has to be filled in, because a
    number that is silently missing its revision is exactly the failure this recipe exists to
    catch -- correct for one board revision and wrong for another, with nothing on the page to
    tell them apart.
    """
    problems = [f"missing field: {f}" for f in REQUIRED_FIELDS if f not in record]
    if problems:
        return problems
    if not isinstance(record["answer"], str) or not record["answer"].strip():
        problems.append("answer must be a non-empty string")
    if not isinstance(record["applies_to_revision"], str) or not record["applies_to_revision"].strip():
        problems.append("applies_to_revision must be a non-empty string")
    if not isinstance(record["citations"], list) or not record["citations"]:
        problems.append("citations must be a non-empty list")
    else:
        unknown = [c for c in record["citations"] if c not in retrieved]
        if unknown:
            problems.append(f"citation(s) not among the retrieved sources: {', '.join(unknown)}")
        for superseded, superseding in SUPERSEDED_BY.items():
            if superseded in record["citations"] and superseding in retrieved and superseding not in record["citations"]:
                problems.append(f"cites {superseded} without {superseding}, which supersedes it")
    return problems


def run(
    question: str,
    model: Model,
    embedder: Embedder,
    tracer: Tracer,
    *,
    corpus_dir: Path = BENCH_CORPUS_DIR,
    top_k: int = TOP_K,
) -> Answer:
    sections = load_sections(corpus_dir)
    tracer.record(kind="code", decided_by="code", title="Chunk the bench documents", detail=f"{len(sections)} sections")
    sources = _retrieve(question, sections, embedder, top_k)
    retrieved = {s.cite for s in sources}
    tracer.record(
        kind="code",
        decided_by="code",
        title="Embed and retrieve top-k",
        detail=", ".join(s.cite for s in sources),
    )
    blocks = "\n\n".join(f"[{s.cite}] {s.title}\n{s.text}" for s in sources)
    messages = [
        Message(role="system", content=SYSTEM_PROMPT),
        Message(role="user", content=f"Sources:\n\n{blocks}\n\nQuestion: {question}"),
    ]
    tracer.record(kind="code", decided_by="code", title="Build prompt with sources and schema", detail=f"{len(sources)} sources")
    record: dict = {}
    for attempt in range(MAX_RETRIES + 1):
        completion = model.complete(messages, schema=SCHEMA, max_tokens=400)
        tracer.record(
            kind="model",
            decided_by="code",
            title="Ask the model for a cited, revision-scoped answer" if attempt == 0 else "Ask again with the validation error",
            detail=completion.text[:200],
            tokens_in=completion.tokens_in,
            tokens_out=completion.tokens_out,
            ms=completion.ms,
        )
        try:
            record = json.loads(completion.text)
            problems = _validate(record, retrieved)
        except json.JSONDecodeError as exc:
            record, problems = {}, [f"invalid JSON: {exc}"]
        tracer.record(kind="code", decided_by="code", title="Validate the reply", detail="; ".join(problems) or "valid")
        if not problems:
            text = f"{record['answer']} (applies to: {record['applies_to_revision']})"
            return Answer(text=text, citations=list(record["citations"]))
        if attempt < MAX_RETRIES:
            messages.append(
                Message(role="user", content=f"That did not validate: {'; '.join(problems)}. Reply again with corrected JSON only.")
            )
    return Answer(text=json.dumps({"error": "did not validate after retry", "last": record}), citations=[])
