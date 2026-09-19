"""Run the test-failure-triage example from the command line.

    python -m examples.bench_test_failure_triage --model stub:scripted
    python -m examples.bench_test_failure_triage --model stub --question SRB5030-2608-0063

`--question` takes a serial number that failed VOUT in
`evals/bench/data/production-run-2026-08.csv`; the module docstring in `run.py` explains why VOUT.

`--model stub` echoes the note back, which is never valid JSON, so the command falls back to
`no_information` after one retry and never shows a real classification. `--model stub:scripted`
plays SCRIPTED below: the one classification call this serial's note actually needs, reading it
the way `README.md` walks through: a dead board on the fixture with the stale offset, where the
note outranks the fixture's own group signature.
"""
from __future__ import annotations

import json
import sys

from examples.bench_test_failure_triage.run import LEVEL, ROUTES, SAMPLE_INPUT, confirm, run
from examples.common.cli import build_cli_model, parse_args
from examples.common.trace import Tracer

# One model call: SAMPLE_INPUT has a note to read ("dead. no vout at all, u1 not switching"), and
# a clean reply on the first attempt needs no retry. The same reply
# tests/test_example_bench_test_failure_triage.py scripts for this serial's own end-to-end test.
SCRIPTED = [
    json.dumps({"cause": "dead_board", "evidence": "dead. no vout at all, u1 not switching"}),
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 3: sort a failing unit's operator note into a cause, then route it.",
        default_question=SAMPLE_INPUT,
    )
    model = build_cli_model(args.model, example="bench_test_failure_triage", script=SCRIPTED)
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
