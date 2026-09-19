"""Level 1: one call. The question alone, straight to the model. No documents, no tools.

The model has to answer from whatever it already knows, or say it does not know. Since this
model has never seen Halvorsen's synthetic manuals, a correct run mostly means it should decline
lookup and numeric questions it cannot know the answer to, rather than inventing one. There is
exactly one decision point in this level, and it belongs to the code: call the model once, with
the question, and return what comes back. Nothing here is decided by the model.
"""
from __future__ import annotations

from examples.common.model import Embedder, Message, Model
from examples.common.trace import Tracer
from examples.common.types import Answer

LEVEL = 1
SYSTEM_PROMPT = (
    "You answer questions about Halvorsen appliances. You have not been given any manual or "
    "document. If you do not know a specific fact, say so plainly instead of guessing."
)


def run(question: str, model: Model, embedder: Embedder | None, tracer: Tracer) -> Answer:
    del embedder  # level 1 has no retrieval step
    messages = [
        Message(role="system", content=SYSTEM_PROMPT),
        Message(role="user", content=question),
    ]
    tracer.record(kind="code", decided_by="code", title="Build prompt", detail=question)
    completion = model.complete(messages, max_tokens=400)
    tracer.record(
        kind="model",
        decided_by="code",
        title="Ask the model",
        detail=completion.text[:200],
        tokens_in=completion.tokens_in,
        tokens_out=completion.tokens_out,
        ms=completion.ms,
    )
    return Answer(text=completion.text, citations=[])
