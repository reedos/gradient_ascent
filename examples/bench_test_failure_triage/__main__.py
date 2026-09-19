"""Run the test-failure-triage example from the command line.

    python -m examples.bench_test_failure_triage --model stub --question SRB5030-2608-0063

`--question` takes a serial number that failed VOUT in
`evals/bench/data/production-run-2026-08.csv`; the module docstring in `run.py` explains why VOUT.
"""
from __future__ import annotations

import sys

from examples.bench_test_failure_triage.run import LEVEL, ROUTES, confirm, run
from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.common.trace import Tracer


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 3: sort a failing unit's operator note into a cause, then route it.",
    )
    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="bench_test_failure_triage", level=LEVEL, model_id=model.model_id)
    disposition = run(args.question, model, tracer)
    print(f"serial          {disposition.row.serial}")
    print(f"measurement     {disposition.row.measurement} = {disposition.row.value}{disposition.row.unit}")
    print(f"fixture / lot   {disposition.row.fixture} / {disposition.row.lot}")
    print(f"note            {disposition.row.note or '(none)'}")
    print(f"group signature {disposition.group_signature}")
    print(f"cause           {disposition.cause} ({disposition.evidence or 'no evidence quoted'})")
    print(f"proposed route  {disposition.route}: {ROUTES[disposition.route]}")
    final = confirm(disposition, approved=True, tracer=tracer)
    print(f"confirmed route {final}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
