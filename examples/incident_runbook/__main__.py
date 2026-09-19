"""Run the incident-runbook example from the command line.

    python -m examples.incident_runbook --model stub --question "(the write-up text)"

Pass --question "" to use the module's own sample write-up. The draft always pauses for the
incident owner; pass --decision to resume it immediately with a scripted choice (approve, edit
or reject) instead of just printing the paused draft.
"""
from __future__ import annotations

import argparse
import sys

from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.common.trace import Tracer
from examples.incident_runbook.run import LEVEL, SAMPLE_INPUT, resume, run

_OWNER_FLAGS = argparse.ArgumentParser(add_help=False)
_OWNER_FLAGS.add_argument("--decision", choices=["approve", "edit", "reject"], default=None)
_OWNER_FLAGS.add_argument("--note", default="")


def main(argv: list[str] | None = None) -> int:
    raw = sys.argv[1:] if argv is None else argv
    owner, remaining = _OWNER_FLAGS.parse_known_args(raw)
    args = parse_args(remaining, description="Level 3: incident write-up to draft runbook, pause and resume.")

    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="incident_runbook", level=LEVEL, model_id=model.model_id)
    pending = run(args.question or SAMPLE_INPUT, model, tracer)

    print(f"PAUSED for approval: {len(pending.steps)} step(s), {len(pending.dropped)} dropped")
    print(pending.text)
    if owner.decision is None:
        print("(pass --decision approve|edit|reject to resume)")
        return 0

    runbook = resume(pending, owner.decision, tracer, note=owner.note)
    print(runbook.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
