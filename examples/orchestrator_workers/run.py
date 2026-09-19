"""Level 6: lead agent and workers. One lead call reads the question and splits it into
independent sub-questions; the code spawns one worker per sub-question, up to `MAX_WORKERS`, and
a second lead call combines what the workers found. The worker is `examples.rag.run.run`,
reused unmodified: each worker is itself a level-2 single call, over the same synthetic corpus.

The lead's own output is what decides how many workers to spawn and what each one is asked --
the split is not something code could write down in advance, since it depends on what the
question actually asks. That is the one place `decided_by="model"` appears in this file. Every
other step is `decided_by="code"`: code always runs the split call, always enforces the worker
cap and the team's token budget, always hands each worker its sub-question, and always returns
each worker's answer to the lead. See `examples/rag/run.py` for why a worker's own steps are
`decided_by="code"` too -- retrieval there is fixed, not a choice.
"""
from __future__ import annotations

from pathlib import Path

from evals.corpus import DEFAULT_CORPUS_DIR
from examples.common.model import Embedder, Message, Model
from examples.common.trace import Tracer
from examples.common.types import Answer
from examples.rag.run import CITE_RE
from examples.rag.run import run as rag_worker

LEVEL = 6
MAX_WORKERS = 3
MAX_TEAM_TOKENS = 6000
SPLIT_SYSTEM = (
    "Split the question below into independent sub-questions about Halvorsen appliances, one "
    f"per worker, at most {MAX_WORKERS}, one per line, no numbering, no extra text. If the "
    "question is already one simple lookup, reply with just that one line."
)
COMBINE_SYSTEM = (
    "Combine the worker answers below into one answer to the original question. Use only what "
    "the workers reported, keep every citation a worker used, and end with a line starting "
    "'Sources:' listing all of them."
)


def _split(question: str, model: Model, tracer: Tracer) -> list[str]:
    completion = model.complete([Message(role="user", content=f"{SPLIT_SYSTEM}\n\nQuestion: {question}")], max_tokens=150)
    tracer.record(
        kind="model",
        decided_by="model",
        title="Lead splits the task",
        detail=completion.text,
        tokens_in=completion.tokens_in,
        tokens_out=completion.tokens_out,
        ms=completion.ms,
    )
    seen: set[str] = set()
    subquestions: list[str] = []
    for line in completion.text.splitlines():
        subq = line.strip("-* ").strip()
        if subq and subq.lower() not in seen:
            seen.add(subq.lower())
            subquestions.append(subq)
    return subquestions


def _combine(question: str, worker_answers: list[tuple[str, Answer]], model: Model, tracer: Tracer) -> str:
    block = "\n\n".join(f"Sub-question: {subq}\nWorker answer: {answer.text}" for subq, answer in worker_answers)
    prompt = f"Original question: {question}\n\n{block}\n\n{COMBINE_SYSTEM}"
    completion = model.complete([Message(role="user", content=prompt)], max_tokens=400)
    tracer.record(
        kind="model",
        decided_by="code",
        title="Lead combines worker answers",
        detail=completion.text[:200],
        tokens_in=completion.tokens_in,
        tokens_out=completion.tokens_out,
        ms=completion.ms,
    )
    return completion.text


def run(
    question: str,
    model: Model,
    embedder: Embedder,
    tracer: Tracer,
    *,
    corpus_dir: Path = DEFAULT_CORPUS_DIR,
    max_workers: int = MAX_WORKERS,
    max_team_tokens: int = MAX_TEAM_TOKENS,
) -> Answer:
    subquestions = _split(question, model, tracer)

    if len(subquestions) > max_workers:
        tracer.record(
            kind="code",
            decided_by="code",
            title="Cap the team",
            detail=f"lead asked for {len(subquestions)} workers, capped at {max_workers}",
        )
        subquestions = subquestions[:max_workers]

    worker_answers: list[tuple[str, Answer]] = []
    for i, subq in enumerate(subquestions, start=1):
        team_tokens = tracer.tokens_in_total() + tracer.tokens_out_total()
        if team_tokens >= max_team_tokens:
            tracer.record(
                kind="code",
                decided_by="code",
                title="Team token budget reached",
                detail=f"stopping before worker {i} of {len(subquestions)}: {team_tokens} >= {max_team_tokens}",
            )
            break
        tracer.record(kind="code", decided_by="code", title=f"Spawn worker {i}", detail=subq)
        worker_answer = rag_worker(subq, model, embedder, tracer, corpus_dir=corpus_dir)
        worker_answers.append((subq, worker_answer))

    if not worker_answers:
        return Answer(text="No worker returned an answer.", citations=[])

    combined_text = _combine(question, worker_answers, model, tracer)
    citations = sorted(
        {c for _, a in worker_answers for c in a.citations} | set(CITE_RE.findall(combined_text.lower()))
    )
    return Answer(text=combined_text, citations=citations)
