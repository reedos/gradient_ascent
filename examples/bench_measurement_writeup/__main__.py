"""Run the measurement writeup example from the command line.

    python -m examples.bench_measurement_writeup --model stub:scripted
    python -m examples.bench_measurement_writeup --model stub --question ""

`--question` fills this example's `notes` parameter, not a question: free text appended to the
prompt (which finding to lead with, a house style note), or the empty string when there is none.
See `examples/common/cli.py` for why every example takes `--question` regardless of what its
first parameter means. The interactive stub returns a short placeholder rather than a report, so
a plain `--model stub` run here shows the figures and the trace but not a real draft.
`--model stub:scripted` plays SCRIPTED below: a full report that uses only the figures code
computed, character for character, and passes the check, the same draft
`tests/test_example_bench_measurement_writeup.py` scripts as its own clean draft.
"""
from __future__ import annotations

import sys

from examples.bench_measurement_writeup.run import LEVEL, run
from examples.common.cli import build_cli_model, parse_args
from examples.common.trace import Tracer

DEFAULT_QUESTION = ""

# One model call: draft the report from the figures code computed and the session notebook.
# Every number below is copied character for character from what compute_results() in run.py
# produces, the same draft tests/test_example_bench_measurement_writeup.py scripts as CLEAN_DRAFT.
SCRIPTED = [
    (
        "Five revision C prototypes were swept over line, load and temperature. At the corner "
        "where line, load and temperature all push the output down together, 9.0 V in, 3.000 A "
        "out, 70 degC, the margin to the 4.900 V output voltage minimum was 73.9 mV for "
        "SRB5030-2609-0001, 58.2 mV for SRB5030-2609-0002, 20.4 mV for SRB5030-2609-0003, 78.5 mV "
        "for SRB5030-2609-0004, and 64.7 mV for SRB5030-2609-0005.\n\n"
        "SRB5030-2609-0003 holds a fifth of the margin the other four hold at that corner, but it "
        "is not a failing board: no single parameter of it is out of specification on its own, "
        "and its corner reading, expanded at a coverage factor of 2 (k = 2), is good to 352.7 uV, "
        "nowhere near the 20.4 mV margin it is being measured against.\n\n"
        "SRB5030-2609-0005's line regulation stays inside its 0.300 percent limit at the cold end "
        "(0.267 percent) and fails it at 70 degC (0.334 percent). At room temperature it reads "
        "0.299 percent, inside the limit by less than the measurement's own 0.0075 percentage "
        "points of uncertainty, so the honest verdict there is cannot say, not a pass.\n\n"
        "Two items are still open. The block recorded at 12.0 V on SRB5030-2609-0001 needs its "
        "input current checked before anyone uses it. And the 200 uV lead and connection "
        "contribution behind every uncertainty above is an assumption from the calibration "
        "procedure, not something measured on this harness."
    ),
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 1: turn the characterization notebook and its computed figures into a report.",
        default_question=DEFAULT_QUESTION,
    )
    model = build_cli_model(args.model, example="bench_measurement_writeup", script=SCRIPTED)
    tracer = Tracer(example="bench_measurement_writeup", level=LEVEL, model_id=model.model_id)
    report = run(args.question, model, tracer)
    print(report.text)
    if report.ok:
        print("check: every number in the draft is one code computed")
    else:
        print("check FAILED, not code's own figures:", ", ".join(report.unsupported))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
