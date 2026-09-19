"""Run the requirements-to-test-plan example from the command line.

    python -m examples.bench_requirements_to_test_plan --model stub:scripted
    python -m examples.bench_requirements_to_test_plan --model stub --question "B"

`--question` takes a board revision, "A", "B" or "C" (see `run.run`'s docstring for why the
revision matters). If the coverage check passes, the run pauses for a person's approval; pass
--decision to resume it immediately instead of just printing the checkpoint.

`--model stub` echoes the question back for every requirement, which is never valid JSON, so
every proposal comes back empty, the coverage check fails on all eight requirements, and the
command exits 1 with a BLOCKED report: that is a real defect this recipe's README does not
mention. `--model stub:scripted` plays SCRIPTED below: one correct, cited proposal per
requirement, in the fixed call order, so the coverage check clears and the command exits 0 with a
plan pending a person's approval.
"""
from __future__ import annotations

import argparse
import json
import sys

from examples.bench_requirements_to_test_plan.run import (
    LEVEL,
    Blocked,
    Requirement,
    _requirements_for_revision,
    resume,
    run,
)
from examples.common.cli import build_cli_model, parse_args
from examples.common.trace import Tracer

_REVIEWER_FLAGS = argparse.ArgumentParser(add_help=False)
_REVIEWER_FLAGS.add_argument("--decision", choices=["approve", "reject"], default=None)
_REVIEWER_FLAGS.add_argument("--note", default="")

#: The revision SCRIPTED below is written for. Any non-C revision reads the same eight
#: requirements (only revision C drops the ECN's supersession), so this is also DEFAULT_QUESTION.
DEFAULT_QUESTION = "B"

#: The right instrument for each requirement, the way `docs/THE-BENCH.md` says to choose one: the
#: ripple and switching-frequency requirements go to the scope, not the meter, since the meter's
#: AC volts function stops at 300 kHz.
_INSTRUMENT_BY_REQ = {
    "REQ-VIN": "MDN-4010",
    "REQ-VOUT": "MDN-6100",
    "REQ-LINEREG": "MDN-6100",
    "REQ-LOADREG": "MDN-6100",
    "REQ-RIPPLE": "TRN-1102",
    "REQ-IQNL": "MDN-4010",
    "REQ-FSW": "TRN-1102",
    "REQ-ILIM": "TRN-2400",
}
#: A proposed procedure for each requirement, in the terms `srb5030-test-spec.md` section 5
#: already uses for the seven it covers; REQ-FSW has no production step at all, so this is a
#: procedure a person still has to review before it becomes one, not a citation to an existing one.
_MEASUREMENT_BY_REQ = {
    "REQ-VIN": "sweep the MDN-4010 across the input range and confirm the board holds regulation",
    "REQ-VOUT": "read VOUT on the MDN-6100, four-wire, 10 V range, at 24.0 V in, 1.000 A out",
    "REQ-LINEREG": "read VOUT at the low and high end of the input sweep at 1.000 A out and report the percent difference",
    "REQ-LOADREG": "read VOUT at 0.100 A and 3.000 A out at 24.0 V in and report the percent difference",
    "REQ-RIPPLE": "TRN-1102 channel 1 on TP2, AC coupled, 20 MHz bandwidth limit, single acquisition, MEAS:VPP?",
    "REQ-IQNL": "set 24.0 V in, load input off, read the MDN-4010's own current with MEAS:CURR?",
    "REQ-FSW": "TRN-1102 on the switch node; measure the period between rising edges and compute frequency",
    "REQ-ILIM": "TRN-2400 ramped in 50 mA steps from 3.500 A at 24.0 V in; report the first current at which VOUT falls below 4.900 V",
}


def _proposal_json(requirement: Requirement) -> str:
    """A correct, schema-shaped proposal for one requirement: the effective limit (the ECN's, not
    the superseded datasheet figure, wherever one applies), so this never trips the stale-limit
    check `check_coverage` runs on every proposal."""
    return json.dumps(
        {
            "requirement": requirement.id,
            "instrument": _INSTRUMENT_BY_REQ[requirement.id],
            "measurement": _MEASUREMENT_BY_REQ[requirement.id],
            "lower": requirement.lower,
            "upper": requirement.effective_upper(),
            "unit": requirement.unit,
        }
    )


# Eight model calls, one per requirement, in the fixed order run.py's own chain asks them in: a
# correct, cited proposal for every one, so the coverage check clears. The same sequence
# tests/test_example_bench_requirements_to_test_plan.py builds independently and pins against
# SCRIPTED.
SCRIPTED = [_proposal_json(r) for r in _requirements_for_revision(DEFAULT_QUESTION)]


def main(argv: list[str] | None = None) -> int:
    raw = sys.argv[1:] if argv is None else argv
    reviewer, remaining = _REVIEWER_FLAGS.parse_known_args(raw)
    args = parse_args(
        remaining,
        description="Level 3: prompt chaining, requirements into a test plan with a traceability table.",
        default_question=DEFAULT_QUESTION,
    )

    model = build_cli_model(args.model, example="bench_requirements_to_test_plan", script=SCRIPTED)
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
