"""Level 1: inference-time reasoning, self-consistency by majority vote. Sample the same
question `n` times, ask each sample to end with a line the code can parse, and return whichever
final answer the largest share of samples agree on. The sample count is fixed and the vote is
always taken the same way, so every step is `decided_by: "code"`: the model only chooses what
each individual sample says, never what the run does with them.
"""
from __future__ import annotations

import re
from collections import Counter

from examples.common.model import Message, Model
from examples.common.trace import Tracer
from examples.common.types import Answer

LEVEL = 1
N_SAMPLES = 5
ANSWER_RE = re.compile(r"\$?(\d+(?:\.\d+)?)")
SYSTEM_PROMPT = (
    "Work through the arithmetic step by step, then end your reply with one line starting "
    "'Answer: ' followed by the number alone."
)


def _extract(text: str) -> str | None:
    """The number on the last line starting 'Answer:', or None if no sample said one."""
    for line in reversed(text.splitlines()):
        if line.strip().lower().startswith("answer:"):
            match = ANSWER_RE.search(line)
            return match.group(1) if match else None
    return None


def run(question: str, model: Model, tracer: Tracer, *, n: int = N_SAMPLES) -> Answer:
    messages = [Message(role="system", content=SYSTEM_PROMPT), Message(role="user", content=question)]
    tracer.record(kind="code", decided_by="code", title="Build one fixed prompt", detail=question)
    votes: Counter[str] = Counter()
    for i in range(n):
        completion = model.complete(messages, max_tokens=200)
        answer = _extract(completion.text) or "no answer"
        votes[answer] += 1
        tracer.record(
            kind="model",
            decided_by="code",
            title=f"Sample {i + 1} of {n}",
            detail=completion.text[:200],
            tokens_in=completion.tokens_in,
            tokens_out=completion.tokens_out,
            ms=completion.ms,
        )
    winner, count = votes.most_common(1)[0]
    tracer.record(kind="code", decided_by="code", title="Tally the votes", detail=f"{dict(votes)}")
    tracer.record(
        kind="code",
        decided_by="code",
        title="Return the majority answer",
        detail=f"{winner} ({count}/{n} samples agreed)",
    )
    return Answer(text=f"{winner} ({count}/{n} samples agreed)", citations=[])
