"""Run the trip-planning example from the command line.

    python -m examples.trip_planning --model stub:scripted
    python -m examples.trip_planning --model stub --question "Plan a trip from Wrenfield to Aldercliff."

If the model calls `book`, the run pauses; pass --decision to resume it immediately with a
scripted reviewer choice (approve or reject) instead of just printing the paused checkpoint.

`--model stub` never calls a tool (the interactive stub only ever replies with text), so the loop
stops on its very first turn and the run shows an echoed answer with no lookups and no pause at
all -- the one shape this level is not about. `--model stub:scripted` plays SCRIPTED below: three
read-only lookups the model chooses for itself, then a `book` call that pauses the run for a
person, the same four calls tests/test_example_trip_planning.py scripts as the run the recipe
page's cost strip quotes token counts for.
"""
from __future__ import annotations

import argparse
import sys

from examples.common.cli import build_cli_model, parse_args
from examples.common.model import StubResponse, ToolCall
from examples.common.trace import Tracer
from examples.trip_planning.run import LEVEL, PendingBooking, SAMPLE_INPUT, approve, run

_REVIEWER_FLAGS = argparse.ArgumentParser(add_help=False)
_REVIEWER_FLAGS.add_argument("--decision", choices=["approve", "reject"], default=None)
_REVIEWER_FLAGS.add_argument("--note", default="")

# Four model calls on SAMPLE_INPUT: the loop searches routes, then stays, then one attraction's
# hours, all the model's own choice of what to look up next, and on the fourth turn calls book.
SCRIPTED = [
    StubResponse(tool_calls=[ToolCall(name="search_routes", arguments={"origin": "Wrenfield", "destination": "Aldercliff"})]),
    StubResponse(tool_calls=[ToolCall(name="search_stays", arguments={"city": "Aldercliff"})]),
    StubResponse(tool_calls=[ToolCall(name="opening_hours", arguments={"place": "Aldercliff Museum of Tides"})]),
    StubResponse(tool_calls=[ToolCall(name="book", arguments={"kind": "route", "ref": "R1"})]),
]


PAUSE_STEP = "Pause for approval before booking"


def _print_steps(tracer: Tracer, start: int) -> int:
    """Print the trace steps recorded since `start`, and return the new end."""
    for step in tracer.steps[start:]:
        if step.title != PAUSE_STEP:
            print(f"[{step.decided_by}] {step.title}: {step.detail}")
    return len(tracer.steps)


def main(argv: list[str] | None = None) -> int:
    raw = sys.argv[1:] if argv is None else argv
    reviewer, remaining = _REVIEWER_FLAGS.parse_known_args(raw)
    args = parse_args(
        remaining,
        description="Level 5: plan a trip and hold the bookings.",
        default_question=SAMPLE_INPUT,
    )

    model = build_cli_model(args.model, example="trip_planning", script=SCRIPTED)
    tracer = Tracer(example="trip_planning", level=LEVEL, model_id=model.model_id)
    result = run(args.question, model, tracer)

    # Which lookups the model chose, and what each one came back with, are what this level is:
    # the held booking alone shows none of it. The checkpoint step is skipped because the block
    # below prints the same call with its fare and terms, and printing it twice reads as two
    # bookings.
    printed = _print_steps(tracer, 0)

    if isinstance(result, PendingBooking):
        print(f"PAUSED for approval: {result.call.detail}")
        print(f"${result.call.price_cents / 100:.2f} -- {result.call.cancellation}")
        if reviewer.decision is None:
            print("(pass --decision approve|reject to resume)")
            return 0
        result = approve(result, reviewer.decision, tracer, note=reviewer.note)
        _print_steps(tracer, printed)

    print(result.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
