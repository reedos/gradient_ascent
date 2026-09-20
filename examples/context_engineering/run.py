"""Level 2: context engineering. No retrieval -- the whole document set goes in the prompt, if it
fits. What the code decides is what order the parts go in and what to cut when they do not fit.

The request is built from parts that change at different rates. The system instructions and the
reference documents are identical on every call; conversation history and the question are
different every time. Putting the identical parts first and the changing parts last is what lets
a prompt-caching backend reuse the front of the request instead of reprocessing it -- see the
"What it is" prose on the page for the two makers who document this. When the whole thing does
not fit in `token_budget`, the code drops the oldest history turns first and never touches the
static part, which is the one place this level makes a choice at all. Nothing here is decided by
the model.
"""
from __future__ import annotations

from pathlib import Path

from evals.corpus import DEFAULT_CORPUS_DIR, load_documents, load_sections
from examples.common.model import Embedder, Message, Model, count_tokens
from examples.common.trace import Tracer
from examples.common.types import Answer

LEVEL = 2
TOKEN_BUDGET = 8000
SYSTEM_PROMPT = (
    "You answer questions about Halvorsen appliances using only the reference documents below. "
    "If they do not contain the answer, say so instead of guessing."
)


def _static_block(corpus_dir: Path) -> tuple[str, int]:
    """Every reference document, concatenated in a fixed (alphabetical) order. Identical on
    every call, so it is built once and never trimmed: the part a caching backend can reuse."""
    documents = load_documents(corpus_dir)
    block = "\n\n".join(f"[{name}]\n{text}" for name, text in sorted(documents.items()))
    return block, count_tokens(block)


def _fit_history(history: list[Message], budget: int, tracer: Tracer) -> list[Message]:
    """Keep the most recent turns that fit in what is left of the budget after the static block.
    History changes every call, so it is what gets cut -- oldest first -- never the documents."""
    kept: list[Message] = []
    used = 0
    for message in reversed(history):
        cost = count_tokens(message.content)
        if used + cost > budget:
            break
        kept.insert(0, message)
        used += cost
    tracer.record(
        kind="code",
        decided_by="code",
        title="Fit conversation history to the remaining budget",
        detail=f"kept {len(kept)} of {len(history)} turn(s), {used} tokens, budget was {budget}",
    )
    return kept


def run(
    question: str,
    model: Model,
    embedder: Embedder | None,
    tracer: Tracer,
    *,
    corpus_dir: Path = DEFAULT_CORPUS_DIR,
    history: list[Message] | None = None,
    token_budget: int = TOKEN_BUDGET,
) -> Answer:
    del embedder  # nothing is retrieved: the whole document set goes in, or none of it does
    static_block, static_tokens = _static_block(corpus_dir)
    tracer.record(
        kind="code",
        decided_by="code",
        title="Assemble the static, cache-friendly block",
        detail="system instructions + the full document set, same on every call",
        tokens_in=static_tokens,
    )
    kept_history = _fit_history(history or [], max(token_budget - static_tokens, 0), tracer)
    dynamic = "\n".join(f"{m.role}: {m.content}" for m in kept_history)
    user_content = static_block + (f"\n\n{dynamic}" if dynamic else "") + f"\n\nQuestion: {question}"
    messages = [Message(role="system", content=SYSTEM_PROMPT), Message(role="user", content=user_content)]
    tracer.record(
        kind="code",
        decided_by="code",
        title="Build the final prompt",
        detail=f"documents first, then {len(kept_history)} history turn(s), then the question last",
    )
    completion = model.complete(messages, max_tokens=400)
    tracer.record(
        kind="model",
        decided_by="code",
        title="Ask the model once with the full context",
        detail=completion.text[:200],
        tokens_in=completion.tokens_in,
        tokens_out=completion.tokens_out,
        ms=completion.ms,
    )
    return Answer.from_text(completion.text, retrieved_sources=list(load_sections(corpus_dir)))
