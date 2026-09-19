"""Run the measurement writeup example from the command line.

    python -m examples.bench_measurement_writeup --model stub --question ""

`--question` fills this example's `notes` parameter, not a question: free text appended to the
prompt (which finding to lead with, a house style note), or the empty string when there is none.
See `examples/common/cli.py` for why every example takes `--question` regardless of what its
first parameter means. The interactive stub returns a short placeholder rather than a report, so
a plain `--model stub` run here shows the figures and the trace but not a real draft; the check
rejecting a bad draft is demonstrated with a scripted stub in
`tests/test_example_bench_measurement_writeup.py`.
"""
from __future__ import annotations

import sys

from examples.bench_measurement_writeup.run import LEVEL, run
from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.common.trace import Tracer


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 1: turn the characterization notebook and its computed figures into a report.",
    )
    model = build_model(args.model, stub=interactive_stub())
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
