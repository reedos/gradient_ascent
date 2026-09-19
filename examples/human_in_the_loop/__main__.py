"""Run the human-in-the-loop example from the command line.

    python -m examples.human_in_the_loop --model stub --question "What does HLV-2205 cost?"
    python -m examples.human_in_the_loop --model stub:scripted
    python -m examples.human_in_the_loop --model stub:scripted --decision approve
    python -m examples.human_in_the_loop --model stub:scripted --decision reject

If the draft trips the confidence or cost threshold, the run pauses; pass --decision to resume it
immediately with a scripted reviewer choice (approve, edit or reject) instead of just printing
the paused checkpoint.

`--model stub` happens to pause too (the echoed text has no citation, so it reads as
low_confidence), but for the wrong reason and never shows a genuine draft. `--model stub:scripted`
plays SCRIPTED below: one draft that names a real dollar figure, which pauses for high_cost, the
reason this page's own illustrated trace (site/src/data/runs/human-in-the-loop.json) shows.
`resume` itself calls no model, so --decision does not change SCRIPTED, only what the run prints
after the pause: --decision approve ships the draft unchanged, --decision reject ships no answer
at all.
"""
from __future__ import annotations

import argparse
import sys

from examples.common.cli import build_cli_model, parse_args
from examples.common.trace import Tracer
from examples.human_in_the_loop.run import LEVEL, PendingReview, resume, run

DEFAULT_QUESTION = "What does HLV-2205 cost?"

# One model call: the draft. Retrieval for DEFAULT_QUESTION finds exactly parts-list#2, and the
# draft names a dollar figure from it, which trips the high_cost threshold and pauses the run
# before any decision is made. `resume` (below) is a second, separate call in the run's own sense,
# but it is plain code, not a model call, so it adds nothing to this sequence.
SCRIPTED = [
    "It costs $52.00. Sources: parts-list#2",
]

_REVIEWER_FLAGS = argparse.ArgumentParser(add_help=False)
_REVIEWER_FLAGS.add_argument("--decision", choices=["approve", "edit", "reject"], default=None)
_REVIEWER_FLAGS.add_argument("--note", default="")


def main(argv: list[str] | None = None) -> int:
    raw = sys.argv[1:] if argv is None else argv
    reviewer, remaining = _REVIEWER_FLAGS.parse_known_args(raw)
    args = parse_args(
        remaining,
        description="Level 3: human approval, pause and resume.",
        default_question=DEFAULT_QUESTION,
    )

    model = build_cli_model(args.model, example="human_in_the_loop", script=SCRIPTED)
    tracer = Tracer(example="human_in_the_loop", level=LEVEL, model_id=model.model_id)
    result = run(args.question, model, None, tracer)

    if isinstance(result, PendingReview):
        print(f"PAUSED for review: {result.reason}")
        print(result.draft_text)
        if reviewer.decision is None:
            print("(pass --decision approve|edit|reject to resume)")
            return 0
        result = resume(result, reviewer.decision, tracer, note=reviewer.note)

    print(result.text)
    print("citations:", ", ".join(result.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
