"""Level 3: routing. One model call classifies the question as one word; the code reads that
word and picks one of three fixed handlers. Only the classifier calls the model on every
question — the numeric and "ask a person" handlers below never call it at all, so a question
routed to either one is cheaper than one routed to the lookup handler.

The classify step is not a level-4 decision. The model is not offered a tool to call; it answers
a plain classification prompt with one word, and the code parses that word and looks it up in a
fixed dict of handlers, the same way `rag.run` parses citations out of free text. Nothing here
lets the model reach into the set of handlers directly the way a tool call lets it choose and
invoke an action; the code owns the entire mapping from label to handler, decided before this
function ever runs.
"""
from __future__ import annotations

import re
from pathlib import Path

from evals.corpus import DEFAULT_CORPUS_DIR, Section, bm25_search, load_sections, lookup_part
from examples.common.model import Embedder, Message, Model
from examples.common.trace import Tracer
from examples.common.types import Answer
from examples.rag.run import CITE_RE

LEVEL = 3
LOOKUP_K = 3
PART_RE = re.compile(r"HLV-\d{4}")
LABELS = ("lookup", "numeric", "unclear")
CLASSIFY_SYSTEM = (
    "Classify the question as exactly one word: 'lookup' if it asks about a fact described in a "
    "Halvorsen document, 'numeric' if it asks for one part's price or part number, or 'unclear' "
    "if it is neither, or you are not confident. Reply with exactly one of those three words."
)
LOOKUP_SYSTEM = (
    "You answer questions about Halvorsen appliances using only the numbered sources below. End "
    "your answer with a line starting 'Sources:' listing the citations, like 'dw300-manual#3'."
)


def _parse_label(text: str) -> str:
    first_word = text.strip().split()[0].lower().strip(".,:;\"'") if text.strip() else ""
    return first_word if first_word in LABELS else "unclear"


def _lookup_route(question: str, sections: dict[str, Section], model: Model, tracer: Tracer) -> Answer:
    sources = [s for s, score in bm25_search(sections, question, k=LOOKUP_K) if score > 0]
    blocks = "\n\n".join(f"[{s.cite}] {s.title}\n{s.text}" for s in sources)
    completion = model.complete(
        [Message(role="system", content=LOOKUP_SYSTEM), Message(role="user", content=f"Sources:\n\n{blocks}\n\nQuestion: {question}")],
        max_tokens=400,
    )
    tracer.record(
        kind="model", decided_by="code", title="Answer with the lookup prompt", detail=completion.text[:200],
        tokens_in=completion.tokens_in, tokens_out=completion.tokens_out, ms=completion.ms,
    )
    return Answer(text=completion.text, citations=sorted(set(CITE_RE.findall(completion.text.lower()))))


def _numeric_route(question: str, sections: dict[str, Section], model: Model, tracer: Tracer) -> Answer:
    match = PART_RE.search(question.upper())
    if not match:
        tracer.record(kind="code", decided_by="code", title="Numeric route found no part number", detail="falling back to ask a person")
        return _person_route(question, sections, model, tracer)
    line = lookup_part(match.group(0))
    tracer.record(kind="code", decided_by="code", title="Answer with the numeric route", detail=line or f"{match.group(0)} not found")
    if not line:
        return Answer(text=f"{match.group(0)} is not in the parts list.", citations=[])
    cite = next((c for c, s in sections.items() if c.startswith("parts-list") and match.group(0) in s.text), None)
    return Answer(text=line, citations=[cite] if cite else [])


def _person_route(question: str, sections: dict[str, Section], model: Model, tracer: Tracer) -> Answer:
    del question, sections, model  # the fallback answers nothing; it defers, on purpose
    tracer.record(kind="code", decided_by="code", title="Route to a person", detail="no automatic route was confident enough")
    return Answer(text="This needs a person to check; no automatic route here was confident enough to answer it.", citations=[])


ROUTES = {"lookup": _lookup_route, "numeric": _numeric_route, "unclear": _person_route}


def run(
    question: str,
    model: Model,
    embedder: Embedder | None,
    tracer: Tracer,
    *,
    corpus_dir: Path = DEFAULT_CORPUS_DIR,
) -> Answer:
    del embedder  # routing retrieves by keyword inside the lookup route, not by vector
    sections = load_sections(corpus_dir)
    classify = model.complete([Message(role="system", content=CLASSIFY_SYSTEM), Message(role="user", content=question)], max_tokens=5)
    tracer.record(
        kind="model", decided_by="code", title="Classify the question", detail=classify.text.strip(),
        tokens_in=classify.tokens_in, tokens_out=classify.tokens_out, ms=classify.ms,
    )
    label = _parse_label(classify.text)
    tracer.record(kind="code", decided_by="code", title="Route on the label", detail=f"label={label!r} -> {label} route")
    return ROUTES[label](question, sections, model, tracer)
