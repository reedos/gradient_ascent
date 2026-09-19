"""Level 1: prompt engineering. The same question, sent to the model two ways.

The bare prompt is the question alone. The structured prompt adds a role, an explicit output
format, and one worked example -- the techniques the makers' own guides describe as instructions,
examples, and format (see this example's technique page for citations). Nothing here is decided
by the model: the code always builds the prompt style it was asked for and asks the model exactly
once. What changes between the two runs is entirely in the prompt, not in the control flow.
"""
from __future__ import annotations

import re

from examples.common.model import Message, Model
from examples.common.trace import Tracer
from examples.common.types import Answer

LEVEL = 1
FIELD_RE = re.compile(r"PART:\s*(\S+)\s+PRICE:\s*\$?([\d.]+)", re.IGNORECASE)

# A passage combining two corpus facts (dw480-manual#8 names the part, parts-list#2 prices it),
# standing in for whatever context a real system would have already retrieved.
PASSAGE = (
    "The DW-480 drain pump is part number HLV-2205, available through authorized service "
    "(dw480-manual#8). The parts list prices HLV-2205 at $52.00 (parts-list#2)."
)

STRUCTURED_SYSTEM = (
    "You are a parts-desk assistant. Read the passage and answer in exactly this format, with no "
    "other text:\nPART: <part number>\nPRICE: <price>\n\n"
    "Example passage: 'The heating element is part HLV-4471, priced at $38.50.'\n"
    "Example answer:\nPART: HLV-4471\nPRICE: $38.50"
)


def run(question: str, model: Model, tracer: Tracer, *, structured: bool = True) -> Answer:
    if structured:
        messages = [
            Message(role="system", content=STRUCTURED_SYSTEM),
            Message(role="user", content=f"{PASSAGE}\n\nQuestion: {question}"),
        ]
        tracer.record(
            kind="code",
            decided_by="code",
            title="Build the structured prompt",
            detail="role + output format + one worked example",
        )
    else:
        messages = [Message(role="user", content=f"{PASSAGE}\n\nQuestion: {question}")]
        tracer.record(kind="code", decided_by="code", title="Build the bare prompt", detail=question)
    completion = model.complete(messages, max_tokens=200)
    tracer.record(
        kind="model",
        decided_by="code",
        title="Ask the model",
        detail=completion.text[:200],
        tokens_in=completion.tokens_in,
        tokens_out=completion.tokens_out,
        ms=completion.ms,
    )
    match = FIELD_RE.search(completion.text)
    citations = ["dw480-manual#8", "parts-list#2"] if match else []
    tracer.record(
        kind="code",
        decided_by="code",
        title="Check the reply against the expected format",
        detail="matched PART/PRICE" if match else "did not match the expected format",
    )
    return Answer(text=completion.text, citations=citations)
