"""Run the weekly-status-report example from the command line.

    python -m examples.weekly_status_report --model stub:scripted

`--question` is the free-text note whoever ran the report added this week; it defaults to the
module's own sample note (`SAMPLE_INPUT`), which is what the recipe page walks through. The three
sources are fixture records inside `run.py`; nothing here reaches the network.

`SCRIPTED` is the one reply a model that followed the system prompt would return for the sample
week: a report built only from the figures code computed, including all four of the must-say ones.
Running it that way prints a report that passes both checks, which is what the page describes.
`--model stub` prints the echo stub's placeholder instead, and the checks then report four
must-say figures left out, which is also worth seeing once.
"""
from __future__ import annotations

import sys

from examples.common.cli import build_cli_model, parse_args
from examples.common.trace import Tracer
from examples.weekly_status_report.run import LEVEL, SAMPLE_INPUT, run

#: One reply, for the one call this example makes. Every number in it is one of the 38 figures
#: `compute_figures` produces for the sample week; `tests/test_example_weekly_status_report.py`
#: asserts that this is the same draft its own tests are written against.
SCRIPTED = [
    """Week ending 09/18/2026

Ferndale Library is the one to look at before Monday. It has used 98.3 percent of its budgeted
hours, 59.0 of 60, and still has 3 tasks open. One of those is the accessibility review, which
was due 09/10/2026 and is still not closed. The client's budget question from Tuesday has been
waiting on us for 6 days.

Brightwater Commons closed 2 tasks this week and opened 1. The permit application was due
09/16/2026 and is the project's one overdue item; the revised site plan thread has been waiting
on us for 8 days. Hours are at 36.1 percent of the 180 budgeted.

Halloway Bridge Survey opened the draft report this week and closed nothing. Nothing on it is
overdue, and the next thing due is 10/02/2026. It has used 9.5 hours of its 60.

Across the three projects, 3 tasks closed, 3 opened, and 2 are overdue. 2 client threads have
been waiting on us for more than 3 days.

The time spreadsheet is current only to 09/15/2026, so hours are counted through 09/11/2026 and
this week's are not in them yet. One project name in the inbox matched nothing on our list, so 1
thread is not counted against any project here."""
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 1: a standing weekly report, with every figure computed and checked by code.",
        default_question=SAMPLE_INPUT,
    )
    model = build_cli_model(args.model, example="weekly_status_report", script=SCRIPTED)
    tracer = Tracer(example="weekly_status_report", level=LEVEL, model_id=model.model_id)
    notes = args.question.strip() or SAMPLE_INPUT
    report = run(notes, model, tracer)
    print(report.text)
    print()
    print(f"Checks: {len(report.unsupported)} unsupported number(s), {len(report.missing)} must-say figure(s) left out.")
    if report.confirm_by_eye:
        print("Too short to check, confirm by eye: " + ", ".join(f.label for f in report.confirm_by_eye))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
