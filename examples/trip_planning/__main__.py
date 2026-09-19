"""Run the trip-planning example from the command line.

    python -m examples.trip_planning --model stub --question "Plan a trip from Wrenfield to Aldercliff."

If the model calls `book`, the run pauses; pass --decision to resume it immediately with a
scripted reviewer choice (approve or reject) instead of just printing the paused checkpoint.
"""
from __future__ import annotations

import argparse
import sys

from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.common.trace import Tracer
from examples.trip_planning.run import LEVEL, PendingBooking, approve, run

_REVIEWER_FLAGS = argparse.ArgumentParser(add_help=False)
_REVIEWER_FLAGS.add_argument("--decision", choices=["approve", "reject"], default=None)
_REVIEWER_FLAGS.add_argument("--note", default="")


def main(argv: list[str] | None = None) -> int:
    raw = sys.argv[1:] if argv is None else argv
    reviewer, remaining = _REVIEWER_FLAGS.parse_known_args(raw)
    args = parse_args(remaining, description="Level 5: plan a trip and hold the bookings.")

    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="trip_planning", level=LEVEL, model_id=model.model_id)
    result = run(args.question, model, tracer)

    if isinstance(result, PendingBooking):
        print(f"PAUSED for approval: {result.call.detail}")
        print(f"${result.call.price_cents / 100:.2f} -- {result.call.cancellation}")
        if reviewer.decision is None:
            print("(pass --decision approve|reject to resume)")
            return 0
        result = approve(result, reviewer.decision, tracer, note=reviewer.note)

    print(result.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
