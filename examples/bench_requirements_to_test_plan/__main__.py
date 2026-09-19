"""Run the requirements-to-test-plan example from the command line.

    python -m examples.bench_requirements_to_test_plan --model stub --question "B"

`--question` takes a board revision, "A", "B" or "C" (see `run.run`'s docstring for why the
revision matters). If the coverage check passes, the run pauses for a person's approval; pass
--decision to resume it immediately instead of just printing the checkpoint.
"""
from __future__ import annotations

import argparse
import sys

from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.common.trace import Tracer
from examples.bench_requirements_to_test_plan.run import LEVEL, Blocked, resume, run

_REVIEWER_FLAGS = argparse.ArgumentParser(add_help=False)
_REVIEWER_FLAGS.add_argument("--decision", choices=["approve", "reject"], default=None)
_REVIEWER_FLAGS.add_argument("--note", default="")


def main(argv: list[str] | None = None) -> int:
    raw = sys.argv[1:] if argv is None else argv
    reviewer, remaining = _REVIEWER_FLAGS.parse_known_args(raw)
    args = parse_args(
        remaining,
        description="Level 3: prompt chaining, requirements into a test plan with a traceability table.",
    )

    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="bench_requirements_to_test_plan", level=LEVEL, model_id=model.model_id)
    result = run(args.question, model, tracer)

    if isinstance(result, Blocked):
        print(f"BLOCKED: the coverage check found {len(result.coverage.problems)} problem(s)")
        for problem in result.coverage.problems:
            print(f"  {problem.requirement_id}: {problem.reason}")
        print("(fix the requirements or the proposals and run again; nothing is pending approval)")
        return 1

    print("PENDING APPROVAL: the plan cleared the coverage check")
    for row in result.rows:
        print(f"  {row.requirement.id}: {row.proposal.measurement} on {row.proposal.instrument}")
    if reviewer.decision is None:
        print("(pass --decision approve|reject to resume)")
        return 0

    answer = resume(result, reviewer.decision, tracer, note=reviewer.note)
    print(answer.text)
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
