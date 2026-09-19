"""Level 2: memory. A small store with three operations -- write, recall by relevance, and
forget -- standing in for what a chat product's memory feature does between conversations: a
question in one conversation gets answered using facts written down in earlier ones, not from
that conversation's own history, which this level does not see at all.

Recall ranks stored entries by embedding similarity to the new question, the same mechanism
`examples/embeddings_search` uses over documents -- memory here is just a much smaller, per-user
index instead of a shared corpus. Forgetting removes an entry outright: nothing later can recall
what was forgotten, which is the whole point of the operation existing. Every step is
`decided_by: "code"`: the code always writes what it is given, always searches, always forgets
what it is told to, and asks the model once at the end with whatever memory recall turned up.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from examples.common.model import Embedder, Message, Model
from examples.common.trace import Tracer
from examples.common.types import Answer

LEVEL = 2
TOP_K = 3
SYSTEM_PROMPT = (
    "Answer the question using only the remembered facts below, if any are relevant. "
    "Say so plainly if none of them help."
)


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norms = (sum(x * x for x in a) ** 0.5) * (sum(y * y for y in b) ** 0.5)
    return dot / norms if norms else 0.0


@dataclass(frozen=True)
class MemoryEntry:
    id: str
    text: str
    vector: list[float]


@dataclass
class MemoryStore:
    """write, recall by relevance, forget. Nothing here is decided by a model."""

    embedder: Embedder
    _entries: dict[str, MemoryEntry] = field(default_factory=dict)
    _next: int = 0

    def write(self, text: str) -> str:
        entry_id = f"m{self._next}"
        self._next += 1
        vector = self.embedder.embed([text])[0]
        self._entries[entry_id] = MemoryEntry(entry_id, text, vector)
        return entry_id

    def forget(self, entry_id: str) -> bool:
        return self._entries.pop(entry_id, None) is not None

    def recall(self, query: str, k: int = TOP_K) -> list[tuple[MemoryEntry, float]]:
        """Rank stored entries by cosine similarity to the question. The division by both lengths
        is what makes this a cosine for any `Embedder`, not only one that returns unit vectors."""
        if not self._entries:
            return []
        query_vec = self.embedder.embed([query])[0]
        scored = [(e, _cosine(query_vec, e.vector)) for e in self._entries.values()]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:k]


def run(
    question: str,
    model: Model,
    embedder: Embedder,
    tracer: Tracer,
    *,
    facts: list[str] | None = None,
    forget_ids: list[str] | None = None,
    k: int = TOP_K,
) -> Answer:
    store = MemoryStore(embedder)
    written = [store.write(fact) for fact in (facts or [])]
    tracer.record(kind="code", decided_by="code", title="Write facts to memory", detail=f"{len(written)} entries: {', '.join(written) or 'none'}")
    forgotten = [eid for eid in (forget_ids or []) if store.forget(eid)]
    tracer.record(kind="code", decided_by="code", title="Forget requested entries", detail=", ".join(forgotten) or "none")
    recalled = store.recall(question, k=k)
    tracer.record(
        kind="code",
        decided_by="code",
        title="Recall memories relevant to the question",
        detail=", ".join(f"{e.id}={score:.2f}" for e, score in recalled) or "none recalled",
    )
    context = "\n".join(f"- {e.text}" for e, _ in recalled) or "(no relevant memories)"
    prompt = f"Remembered facts:\n{context}\n\nQuestion: {question}"
    messages = [Message(role="system", content=SYSTEM_PROMPT), Message(role="user", content=prompt)]
    completion = model.complete(messages, max_tokens=300)
    tracer.record(
        kind="model",
        decided_by="code",
        title="Answer using recalled memory",
        detail=completion.text[:200],
        tokens_in=completion.tokens_in,
        tokens_out=completion.tokens_out,
        ms=completion.ms,
    )
    return Answer(text=completion.text, citations=[e.id for e, _ in recalled])
