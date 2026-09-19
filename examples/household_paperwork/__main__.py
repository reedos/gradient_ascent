"""Run the household paperwork report from the command line.

    python -m examples.household_paperwork
    python -m examples.household_paperwork --question "2026-09-19"

The question is the date the report is run for; leave it empty to use the module's own `AS_OF`
(by way of `SAMPLE_INPUT`, the same date as a string). No model is called at any level of this
example, so `--model` is accepted only because every example here takes it, and it is ignored:
there is nothing `--model stub:scripted` could script, and the output is the same either way.
"""
from __future__ import annotations

from examples.common.cli import parse_args
from examples.common.trace import Tracer
from examples.household_paperwork.run import LEVEL, SAMPLE_INPUT, run


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        argv or __import__("sys").argv[1:],
        description="Level 0: household paperwork, no model.",
        default_question=SAMPLE_INPUT,
    )
    tracer = Tracer(example="household_paperwork", level=LEVEL, model_id="none")
    report = run(args.question, None, tracer)
    print(report.text)
    print("records used:", ", ".join(report.citations))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
