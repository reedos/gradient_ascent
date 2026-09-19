"""Run the instrument-script example from the command line.

    python -m examples.bench_instrument_script_from_the_manual --model stub --question "Set the TRN-2400 to 1.000 A, enable it, read it back, disable it."
"""
from __future__ import annotations

import sys

from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.common.trace import Tracer
from examples.bench_instrument_script_from_the_manual.run import LEVEL, run


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 3: draft a TRN-2400 script from its manual, check it, revise it.",
    )
    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="bench_instrument_script_from_the_manual", level=LEVEL, model_id=model.model_id)
    result = run(args.question, model, tracer)
    for attempt in result.attempts:
        status = "clean" if not attempt.errors else f"{len(attempt.errors)} error(s)"
        print(f"draft ({status}):")
        print("\n".join(f"  {c}" for c in attempt.commands))
    if result.readings:
        print("readings:", result.readings)
    else:
        print("no readings: the script never ran clean within the revision cap")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
