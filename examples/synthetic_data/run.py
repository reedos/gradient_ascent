"""Track: adaptation, technique: synthetic data. A model paraphrases seed questions from the
site's own exact-graded set; each paraphrase is checked for deduplication and leakage against
every question already in the set and every paraphrase already accepted, then a second call
answers the paraphrase blind and the answer is checked with `examples.distillation.run`'s own
accept/require/reject grading contract (see `docs/EVALS.md`) — the same filter that page uses to
check a captured teacher answer, used here to check that a paraphrase still means what its seed
question meant. Only a paraphrase that clears both checks is kept. Nothing here trains anything:
this is the generate-then-verify step a synthetic set needs before it is usable, not training
itself.

Self-Instruct's own paper describes the same two-part shape at the scale of a full dataset: "Our
pipeline generates instructions, input, and output samples from a language model, then filters
invalid or similar ones before using them to finetune the original model." The paraphrase step
below is the generation half; the dedup and verification steps are this file's version of that
filter.

What the verification step cannot see is written as tests rather than left to be discovered: a
paraphrase that negates its seed question, whose blind answer still contains the seed's accept
pattern, passes both checks. Equality over normalized text and one pattern match are the floor,
not a meaning check.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from examples.common.model import Message, Model
from examples.common.trace import Tracer
from examples.distillation.run import Question, grade_exact, load_exact_questions

LEVEL = 1  # synthetic data is a track technique, not a rung on the ladder; see content/taxonomy.json
DEFAULT_QUESTIONS_PATH = Path(__file__).resolve().parents[2] / "evals" / "questions.json"
PARAPHRASE_SYSTEM_PROMPT = (
    "Reword the following question so it asks the same thing in different words. Reply with "
    "only the reworded question and nothing else."
)
ANSWER_SYSTEM_PROMPT = (
    "You are a Halvorsen appliance support assistant. Answer the question in one or two plain "
    "sentences, with no citations and no hedging."
)


@dataclass(frozen=True)
class GeneratedQuestion:
    source_id: str
    text: str


@dataclass(frozen=True)
class Rejection:
    source_id: str
    text: str
    reason: str  # "duplicate" | "failed verification"


@dataclass(frozen=True)
class SyntheticResult:
    kept: list[GeneratedQuestion]
    rejected: list[Rejection]
    out_path: Path


def _normalize(text: str) -> str:
    """The same rule `examples/adaptation`'s own leak check uses: letters and digits only,
    lowercased, so two questions differing only in punctuation or spacing collide."""
    return "".join(ch for ch in text.lower() if ch.isalnum())


def all_question_texts(questions_path: Path = DEFAULT_QUESTIONS_PATH) -> list[str]:
    """Every question in the set, exact-graded and rubric-graded alike.

    Deduplication runs against all 60, not only the 32 this example generates from. A paraphrase
    that lands on a rubric-graded question is a fresh copy of a question the eval set already
    asks: train on it and the later score on that question is no longer measuring anything held
    out. Checking only the seeds would have let that one through.
    """
    data = json.loads(questions_path.read_text(encoding="utf-8"))
    return [q["question"] for q in data["questions"]]


def run(
    tracer: Tracer,
    model: Model,
    *,
    questions_path: Path = DEFAULT_QUESTIONS_PATH,
    out_path: Path,
) -> SyntheticResult:
    seeds: list[Question] = load_exact_questions(questions_path)
    existing = all_question_texts(questions_path)
    tracer.record(
        kind="code",
        decided_by="code",
        title="Load exact-graded seed questions",
        detail=f"{len(seeds)} seeds, deduplicating against {len(existing)} existing questions",
    )

    # Every question already in the set, so a "paraphrase" identical to the question it came from
    # -- or to any other question the eval set asks, including the rubric-graded ones this example
    # never generates from -- is not new data; every novel paraphrase claims its own text the
    # moment it clears this check, whether or not it goes on to pass verification, so two seeds
    # paraphrased the same way never both proceed. This one set is this example's dedup check and
    # its leakage check at once.
    seen = {_normalize(text) for text in existing}
    kept: list[GeneratedQuestion] = []
    rejected: list[Rejection] = []

    for seed in seeds:
        paraphrase = model.complete(
            [Message(role="system", content=PARAPHRASE_SYSTEM_PROMPT), Message(role="user", content=seed.text)],
            max_tokens=100,
        )
        tracer.record(
            kind="model",
            decided_by="code",
            title="Generate a paraphrase",
            detail=paraphrase.text[:200],
            tokens_in=paraphrase.tokens_in,
            tokens_out=paraphrase.tokens_out,
            ms=paraphrase.ms,
        )

        normalized = _normalize(paraphrase.text)
        if normalized in seen:
            rejected.append(Rejection(source_id=seed.id, text=paraphrase.text, reason="duplicate"))
            tracer.record(kind="code", decided_by="code", title="Reject: duplicate or unchanged", detail=seed.id)
            continue
        seen.add(normalized)  # claim the text now: two seeds paraphrased the same way is a
        # generator diversity problem whether or not this one goes on to verify

        answer = model.complete(
            [Message(role="system", content=ANSWER_SYSTEM_PROMPT), Message(role="user", content=paraphrase.text)],
            max_tokens=200,
        )
        tracer.record(
            kind="model",
            decided_by="code",
            title="Answer the paraphrase blind",
            detail=answer.text[:200],
            tokens_in=answer.tokens_in,
            tokens_out=answer.tokens_out,
            ms=answer.ms,
        )

        if not grade_exact(answer.text, seed):
            rejected.append(Rejection(source_id=seed.id, text=paraphrase.text, reason="failed verification"))
            tracer.record(
                kind="code",
                decided_by="code",
                title="Reject: answer no longer matches the seed's grading contract",
                detail=seed.id,
            )
            continue

        kept.append(GeneratedQuestion(source_id=seed.id, text=paraphrase.text))
        tracer.record(kind="code", decided_by="code", title="Keep: new and verified", detail=seed.id)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps({"source_id": g.source_id, "question": g.text}, sort_keys=True) for g in kept]
    out_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8", newline="\n")
    tracer.record(kind="code", decided_by="code", title="Write verified synthetic questions", detail=out_path.name)

    return SyntheticResult(kept=kept, rejected=rejected, out_path=out_path)
