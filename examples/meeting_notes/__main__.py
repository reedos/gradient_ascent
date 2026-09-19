"""Run the meeting-notes example from the command line.

    python -m examples.meeting_notes --model stub --question ""

Leave --question empty to run against the module's own sample transcript (`SAMPLE_INPUT`); pass
your own transcript text instead to extract decisions from it.
"""
from __future__ import annotations

import sys

from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.common.trace import Tracer
from examples.meeting_notes.run import LEVEL, SAMPLE_INPUT, run


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 1: meeting notes, extract decisions, owners and open questions.",
    )
    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="meeting_notes", level=LEVEL, model_id=model.model_id)
    transcript = args.question.strip() or SAMPLE_INPUT
    notes = run(transcript, model, tracer)
    print(notes.text)
    print("citations:", ", ".join(notes.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
