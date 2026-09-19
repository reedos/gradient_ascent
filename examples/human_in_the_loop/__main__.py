"""Run the human-in-the-loop example from the command line.

    python -m examples.human_in_the_loop --model stub --question "What does HLV-2205 cost?"

If the draft trips the confidence or cost threshold, the run pauses; pass --decision to resume it
immediately with a scripted reviewer choice (approve, edit or reject) instead of just printing
the paused checkpoint.
"""
from __future__ import annotations

import argparse
import sys

from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.common.trace import Tracer
from examples.human_in_the_loop.run import LEVEL, PendingReview, resume, run

_REVIEWER_FLAGS = argparse.ArgumentParser(add_help=False)
_REVIEWER_FLAGS.add_argument("--decision", choices=["approve", "edit", "reject"], default=None)
_REVIEWER_FLAGS.add_argument("--note", default="")


def main(argv: list[str] | None = None) -> int:
    raw = sys.argv[1:] if argv is None else argv
    reviewer, remaining = _REVIEWER_FLAGS.parse_known_args(raw)
    args = parse_args(remaining, description="Level 3: human approval, pause and resume.")

    model = build_model(args.model, stub=interactive_stub())
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
