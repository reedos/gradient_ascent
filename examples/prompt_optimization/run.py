"""Track: adaptation, technique: prompt optimization. A tiny version of what DSPy's own
optimizers do: search over candidate instructions against a metric, on a development split, then
report the winner's score on a held-out split it was never chosen against. DSPy's own paper
describes its optimizer as "a compiler that will optimize any DSPy pipeline to maximize a given
metric" — this example is a minimal version of that idea, with three differences worth naming: it
searches over a fixed list of whole system prompts rather than composing few-shot examples or
instructions piece by piece, it grades with `examples.distillation.run.grade_exact`'s own
accept/require/reject contract rather than a general metric function, and it never touches
weights, only the instruction text.

The split matters more than the search here. `run` scores every candidate on the development
split only; the held-out split is touched exactly once, after a winner is already chosen, and only
by the winner. A number from the development split answers "which candidate looked best while we
were choosing," not "how good is the one we picked" -- that is what the held-out score is for.

Three properties the tests hold this file to, because each one is a way the separation could rot
without the result looking any different: the split is a deterministic, disjoint partition for a
given seed; every held-out question is asked exactly once, after selection, and only under the
selected instruction; and a tie resolves to the first candidate in list order, which means a run
whose candidates all tie has selected nothing at all.

`max_questions` bounds the search. The full set costs one call per question per candidate plus
the held-out pass, which is 80 calls on the 32 exact-graded questions, more than a demonstration
needs. It takes the first `n` questions of the set rather than sampling, so two runs of the same
bound search the same questions, and it is applied before the split rather than after, so a
bounded run is a smaller version of the same procedure and not a different one. What it does
narrow is what a score is evidence about: 4/4 on four questions is four questions.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

from examples.common.model import Message, Model
from examples.common.trace import Tracer
from examples.distillation.run import Question, grade_exact, load_exact_questions

LEVEL = 1  # prompt optimization is a track technique, not a rung on the ladder; see content/taxonomy.json
DEFAULT_QUESTIONS_PATH = Path(__file__).resolve().parents[2] / "evals" / "questions.json"

CANDIDATE_INSTRUCTIONS = [
    "Answer the question in one short sentence.",
    "You are a Halvorsen appliance support assistant. Answer in one or two plain sentences, "
    "with no citations and no hedging.",
    "Think step by step, then give the final answer as a single sentence starting with 'Answer:'.",
]


@dataclass(frozen=True)
class CandidateScore:
    instruction: str
    dev_correct: int
    dev_total: int

    @property
    def dev_score(self) -> float:
        return self.dev_correct / self.dev_total if self.dev_total else 0.0


@dataclass(frozen=True)
class OptimizationResult:
    candidates: list[CandidateScore]
    selected: str
    held_out_correct: int
    held_out_total: int

    @property
    def held_out_score(self) -> float:
        return self.held_out_correct / self.held_out_total if self.held_out_total else 0.0


def split_dev_held_out(
    questions: list[Question], *, held_out_fraction: float, seed: int
) -> tuple[list[Question], list[Question]]:
    shuffled = list(questions)
    random.Random(seed).shuffle(shuffled)
    held_out_count = max(1, round(len(shuffled) * held_out_fraction))
    return shuffled[held_out_count:], shuffled[:held_out_count]  # dev, held_out


def _score(model: Model, instruction: str, questions: list[Question], tracer: Tracer, *, phase: str) -> tuple[int, int]:
    correct = 0
    for question in questions:
        completion = model.complete(
            [Message(role="system", content=instruction), Message(role="user", content=question.text)],
            max_tokens=200,
        )
        tracer.record(
            kind="model",
            decided_by="code",
            title=f"{phase}: answer one question",
            detail=completion.text[:200],
            tokens_in=completion.tokens_in,
            tokens_out=completion.tokens_out,
            ms=completion.ms,
        )
        if grade_exact(completion.text, question):
            correct += 1
    return correct, len(questions)


def run(
    tracer: Tracer,
    model: Model,
    *,
    questions_path: Path = DEFAULT_QUESTIONS_PATH,
    instructions: list[str] | None = None,
    held_out_fraction: float = 0.25,
    max_questions: int | None = None,
    seed: int = 0,
) -> OptimizationResult:
    instructions = instructions if instructions is not None else CANDIDATE_INSTRUCTIONS
    questions = load_exact_questions(questions_path)
    loaded = len(questions)
    if max_questions is not None:
        if max_questions < 1:
            raise ValueError(f"max_questions={max_questions} leaves no questions to search over")
        questions = questions[:max_questions]
    detail = f"{len(questions)} questions"
    if len(questions) < loaded:
        detail = f"{len(questions)} of {loaded} questions, bounded by max_questions={max_questions}"
    tracer.record(kind="code", decided_by="code", title="Load exact-graded questions", detail=detail)

    dev, held_out = split_dev_held_out(questions, held_out_fraction=held_out_fraction, seed=seed)
    if not dev:
        # Selecting on an empty development split is not selection: every candidate ties at zero
        # and `max` returns the first one, which would then be reported with a held-out score as
        # though a search had chosen it. Fail here instead of returning a meaningless winner.
        raise ValueError(
            f"held_out_fraction={held_out_fraction} leaves no development questions to select on"
        )
    tracer.record(
        kind="code",
        decided_by="code",
        title="Split into a development set and a held-out set",
        detail=f"{len(dev)} development, {len(held_out)} held-out",
    )

    candidates: list[CandidateScore] = []
    for instruction in instructions:
        correct, total = _score(model, instruction, dev, tracer, phase="select")
        candidates.append(CandidateScore(instruction=instruction, dev_correct=correct, dev_total=total))
        tracer.record(
            kind="code",
            decided_by="code",
            title="Score one candidate on the development split",
            detail=f"{correct}/{total}",
        )

    # `max` keeps the first of equal scores, so a tie resolves to the earliest candidate in the
    # list. That is a deterministic rule rather than a judgment: a run whose candidates all tie
    # has selected nothing, and its "winner" is list order.
    best = max(candidates, key=lambda c: c.dev_score)
    tied = [c.instruction for c in candidates if c.dev_correct == best.dev_correct]
    tracer.record(
        kind="code",
        decided_by="code",
        title="Select the candidate with the best development score",
        detail=f"{best.dev_score:.2f} on the development split"
        + (f"; {len(tied)} candidates tied, first in list order kept" if len(tied) > 1 else ""),
    )

    held_correct, held_total = _score(model, best.instruction, held_out, tracer, phase="report")
    tracer.record(
        kind="code",
        decided_by="code",
        title="Score the selected candidate on the held-out split",
        detail=f"{held_correct}/{held_total}",
    )

    return OptimizationResult(
        candidates=candidates,
        selected=best.instruction,
        held_out_correct=held_correct,
        held_out_total=held_total,
    )
