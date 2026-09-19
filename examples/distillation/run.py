"""Track: adaptation, technique: distillation. A teacher model answers the site's own
exact-graded questions; each answer is filtered by the same accept/require/reject grading
contract `evals/questions.json` carries (see `docs/EVALS.md`); what passes is written as a
student training file. Nothing here trains a student model: like `examples/adaptation`, this is
the data-preparation step, not the job itself.

OpenAI's own distillation guide describes the mechanism this mirrors: "capture results generated
from your model" and then "use the captured responses from the large model that fit your
criteria to generate a dataset" for training a smaller one. `grade_exact` is what "fit your
criteria" means here: a captured answer is kept only if it passes the same pattern check a real
answer would be scored by.

Restricted to the 32 of 60 questions graded `"exact"` rather than `"rubric"`: a rubric-graded
question needs a grader model reading free text, which this example does not call, so those
questions are left out rather than approximately graded by a pattern check they were never
written for.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from examples.common.model import Message, Model
from examples.common.trace import Tracer

LEVEL = 1  # distillation is a track technique, not a rung on the ladder; see content/taxonomy.json
DEFAULT_QUESTIONS_PATH = Path(__file__).resolve().parents[2] / "evals" / "questions.json"
TEACHER_SYSTEM_PROMPT = (
    "You are a Halvorsen appliance support assistant. Answer the question in one or two plain "
    "sentences, with no citations and no hedging."
)


@dataclass(frozen=True)
class Question:
    id: str
    text: str
    accept: list[str]
    require: list[str]
    reject: list[str]


@dataclass(frozen=True)
class DistilledExample:
    id: str
    question: str
    answer: str  # the teacher's own captured text, not the answer key

    def as_chat_record(self) -> dict:
        return {
            "messages": [
                {"role": "system", "content": TEACHER_SYSTEM_PROMPT},
                {"role": "user", "content": self.question},
                {"role": "assistant", "content": self.answer},
            ]
        }


@dataclass(frozen=True)
class DistillResult:
    kept: list[DistilledExample]
    dropped: list[str]  # question ids whose captured answer failed the filter
    out_path: Path


def load_exact_questions(questions_path: Path = DEFAULT_QUESTIONS_PATH) -> list[Question]:
    """The subset of the 60-question set graded by pattern match, the only kind an exact-match
    grader with no model of its own can judge."""
    data = json.loads(questions_path.read_text(encoding="utf-8"))
    return [
        Question(
            id=q["id"],
            text=q["question"],
            accept=q.get("accept") or [],
            require=q.get("require") or [],
            reject=q.get("reject") or [],
        )
        for q in data["questions"]
        if q["grading"] == "exact"
    ]


def grade_exact(answer: str, question: Question) -> bool:
    """The same contract `docs/EVALS.md` describes for the site's own runner: every `reject`
    pattern must be absent, every `require` pattern must be present, and at least one `accept`
    pattern must match when any are given. Patterns are regexes, matched case-insensitively."""
    text = answer.lower()
    if any(re.search(pattern, text, re.I) for pattern in question.reject):
        return False
    if question.require and not all(re.search(pattern, text, re.I) for pattern in question.require):
        return False
    if question.accept and not any(re.search(pattern, text, re.I) for pattern in question.accept):
        return False
    return True


def run(
    tracer: Tracer,
    teacher: Model,
    *,
    questions_path: Path = DEFAULT_QUESTIONS_PATH,
    out_path: Path,
) -> DistillResult:
    questions = load_exact_questions(questions_path)
    tracer.record(kind="code", decided_by="code", title="Load exact-graded questions", detail=f"{len(questions)} of the set")

    kept: list[DistilledExample] = []
    dropped: list[str] = []
    for question in questions:
        completion = teacher.complete(
            [Message(role="system", content=TEACHER_SYSTEM_PROMPT), Message(role="user", content=question.text)],
            max_tokens=200,
        )
        tracer.record(
            kind="model",
            decided_by="code",
            title="Teacher answers one question",
            detail=completion.text[:200],
            tokens_in=completion.tokens_in,
            tokens_out=completion.tokens_out,
            ms=completion.ms,
        )
        if grade_exact(completion.text, question):
            kept.append(DistilledExample(id=question.id, question=question.text, answer=completion.text))
        else:
            dropped.append(question.id)
    tracer.record(
        kind="code",
        decided_by="code",
        title="Filter captured answers against the grading contract",
        detail=f"{len(kept)} kept, {len(dropped)} dropped",
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(ex.as_chat_record(), sort_keys=True) for ex in kept]
    out_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8", newline="\n")
    tracer.record(kind="code", decided_by="code", title="Write student training file", detail=out_path.name)

    return DistillResult(kept=kept, dropped=dropped, out_path=out_path)
