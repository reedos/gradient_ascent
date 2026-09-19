"""Track: adaptation. Builds and validates a small supervised fine-tuning file from the site's
own 60-question set, instead of calling any training API — nothing on this site trains a model.

Each question becomes one chat-format example: a `system`/`user`/`assistant` message list, the
shape Together AI's fine-tuning data preparation guide documents for a conversational JSONL
file, where "each message has a role (system, user, or assistant) and content" and a
conversation "must start with system or user and alternate user and assistant afterwards".
Questions are shuffled with a fixed seed and split into a training file and a held-out
validation file. `leaked_questions` then checks that no question's normalized text appears in
both files - the check a held-out split is for, since a model that was shown a question during
training, even reworded in case or spacing, was not really held out from it.

This module never imports `examples.common.model`: nothing here calls a model, real or stubbed,
because there is nothing to fine-tune it against. `LEVEL` is set to 1 only because `Tracer`
requires an int; adaptation is a track that applies at every level, not a rung on the ladder
(see `content/taxonomy.json`), and this file makes no claim about where it sits.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

from examples.common.trace import Tracer

LEVEL = 1
DEFAULT_QUESTIONS_PATH = Path(__file__).resolve().parents[2] / "evals" / "questions.json"
SYSTEM_PROMPT = (
    "You are a Halvorsen appliance support assistant. Answer in one or two plain sentences, in "
    "the style of the answer key, with no citations and no hedging."
)


@dataclass(frozen=True)
class Example:
    id: str
    question: str
    answer: str

    def as_chat_record(self) -> dict:
        """One line of the fine-tuning JSONL file: a `messages` list of role/content pairs."""
        return {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": self.question},
                {"role": "assistant", "content": self.answer},
            ]
        }


@dataclass(frozen=True)
class BuildResult:
    train: list[Example]
    val: list[Example]
    train_path: Path
    val_path: Path
    leaked: list[str]  # question ids in val whose text also appears in train; empty when clean


def load_examples(questions_path: Path = DEFAULT_QUESTIONS_PATH) -> list[Example]:
    """Every question in the set, as a training example. Every question carries a plain-language
    `answer` even when its kind is `unanswerable` (the correct completion there is the model
    saying so), so nothing is filtered out by kind."""
    data = json.loads(questions_path.read_text(encoding="utf-8"))
    return [Example(id=q["id"], question=q["question"], answer=q["answer"]) for q in data["questions"]]


def _normalize(text: str) -> str:
    """Keep the letters and digits, lowercased, and nothing else. Two questions that differ only
    in case, spacing or punctuation normalize to the same string and count as the same question.

    Dropping punctuation rather than turning it into a space is what makes that sentence true.
    Turning it into a space kept the word boundary, so "don't" became "don t" and "dont" stayed
    "dont" -- a leak that differed by one apostrophe walked straight through the check that was
    documented as catching exactly that. Running the words together can in principle make two
    genuinely different questions collide, which for a leak check errs the safe way: it reports
    a duplicate to look at rather than letting one past.
    """
    return "".join(ch for ch in text.lower() if ch.isalnum())


def leaked_questions(train: list[Example], val: list[Example]) -> list[str]:
    """Val-set ids whose normalized question text also appears in the train set. A held-out split
    is only worth anything if training never saw the same question under a different id.

    This catches only questions that are identical once normalized. A paraphrase in genuinely
    different words ("how long is the warranty" against "what is the warranty period") is a
    near-duplicate this equality test cannot see; catching those needs a similarity measure, and
    an embedding of each question is the usual one."""
    train_texts = {_normalize(ex.question) for ex in train}
    return sorted(ex.id for ex in val if _normalize(ex.question) in train_texts)


def split(examples: list[Example], *, val_fraction: float, seed: int) -> tuple[list[Example], list[Example]]:
    shuffled = list(examples)
    random.Random(seed).shuffle(shuffled)
    val_count = max(1, round(len(shuffled) * val_fraction))
    return shuffled[val_count:], shuffled[:val_count]  # train, val


def _write_jsonl(path: Path, examples: list[Example]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(ex.as_chat_record(), sort_keys=True) for ex in examples]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def run(
    tracer: Tracer,
    *,
    questions_path: Path = DEFAULT_QUESTIONS_PATH,
    out_dir: Path,
    val_fraction: float = 0.2,
    seed: int = 0,
) -> BuildResult:
    examples = load_examples(questions_path)
    tracer.record(kind="code", decided_by="code", title="Load questions as chat examples", detail=f"{len(examples)} examples")

    train, val = split(examples, val_fraction=val_fraction, seed=seed)
    tracer.record(
        kind="code",
        decided_by="code",
        title="Shuffle and split into train and validation",
        detail=f"{len(train)} train, {len(val)} val, seed={seed}",
    )

    train_path, val_path = out_dir / "train.jsonl", out_dir / "val.jsonl"
    _write_jsonl(train_path, train)
    _write_jsonl(val_path, val)
    tracer.record(kind="code", decided_by="code", title="Write JSONL files", detail=f"{train_path.name}, {val_path.name}")

    leaked = leaked_questions(train, val)
    tracer.record(
        kind="code",
        decided_by="code",
        title="Check for leaked questions between splits",
        detail=", ".join(leaked) or "none",
    )
    return BuildResult(train=train, val=val, train_path=train_path, val_path=val_path, leaked=leaked)
