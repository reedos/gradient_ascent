"""Run the instrument-script example from the command line.

    python -m examples.bench_instrument_script_from_the_manual --model stub:scripted
    python -m examples.bench_instrument_script_from_the_manual --model stub \\
        --question "Set the TRN-2400 to 1.000 A, enable it, read it back, disable it."

`--model stub` echoes the question back as a single line, which the manual's command set rejects
outright, so the command shows one failed attempt and stops at the revision cap with no readings.
`--model stub:scripted` plays SCRIPTED below: a first draft written as if the TRN-2400 were a
Maridun instrument (a long-form keyword and the ON/OFF words Maridun accepts and Tarnley does
not), a first revision that fixes the keyword but not the booleans, and a second revision that
runs clean, the same shape
tests/test_example_bench_instrument_script_from_the_manual.py scripts for its own rejected-and-
fixed test.
"""
from __future__ import annotations

import sys

from examples.bench_instrument_script_from_the_manual.run import LEVEL, TASK, run
from examples.common.cli import build_cli_model, parse_args
from examples.common.trace import Tracer

#: Both of the manual's own dialect mistakes at once: the long-form keyword Maridun accepts and
#: Tarnley does not ("CURRent"), and the ON/OFF words Maridun accepts and Tarnley does not
#: ("INP ON" / "INP OFF").
_BAD_DRAFT = "MODE CC\nCURRent 1.000\nINP ON\nMEAS:VOLT?\nMEAS:CURR?\nINP OFF"
#: The keyword fixed, the booleans not: a plausible half-correction from SYST:ERR? feedback that
#: named both problems but got applied to only one of them.
_PARTIAL_DRAFT = "MODE CC\nCURR 1.000\nINP ON\nMEAS:VOLT?\nMEAS:CURR?\nINP OFF"
#: Both fixed: short-form keyword, 1/0 booleans. Runs clean.
_GOOD_DRAFT = "MODE CC\nCURR 1.000\nINP 1\nMEAS:VOLT?\nMEAS:CURR?\nINP 0"

# Three model calls: a draft with both of the manual's dialect mistakes, a revision that fixes
# only the keyword, and a second revision that also fixes the booleans and runs clean. The
# revision cap is two, so this is the last attempt the loop allows.
SCRIPTED = [_BAD_DRAFT, _PARTIAL_DRAFT, _GOOD_DRAFT]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 3: draft a TRN-2400 script from its manual, check it, revise it.",
        default_question=TASK,
    )
    model = build_cli_model(args.model, example="bench_instrument_script_from_the_manual", script=SCRIPTED)
    tracer = Tracer(example="bench_instrument_script_from_the_manual", level=LEVEL, model_id=model.model_id)
    result = run(args.question, model, tracer)
    for attempt in result.attempts:
        status = "clean" if not attempt.errors else f"{len(attempt.errors)} error(s)"
        print(f"draft ({status}):")
        print("\n".join(f"  {c}" for c in attempt.commands))
        for command, error in attempt.errors:
            print(f"    {command!r} -> {error}")
    if result.readings:
        print("readings:", result.readings)
    else:
        print("no readings: the script never ran clean within the revision cap")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
