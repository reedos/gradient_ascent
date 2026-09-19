"""Run the contract review example from the command line.

    python -m examples.contract_review --model stub --question ""

An empty --question uses the built-in invented agreement; pass any other text with numbered
clauses ("1. ...\\n2. ...") to check a different one against the same checklist. The run always
returns a checkpoint; pass --decision to resume it immediately with a scripted reviewer choice
(acknowledged or sent_back) instead of just printing the findings.
"""
from __future__ import annotations

import argparse
import sys

from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.common.trace import Tracer
from examples.contract_review.run import LEVEL, resume, run

_REVIEWER_FLAGS = argparse.ArgumentParser(add_help=False)
_REVIEWER_FLAGS.add_argument("--decision", choices=["acknowledged", "sent_back"], default=None)
_REVIEWER_FLAGS.add_argument("--note", default="")


def main(argv: list[str] | None = None) -> int:
    raw = sys.argv[1:] if argv is None else argv
    reviewer, remaining = _REVIEWER_FLAGS.parse_known_args(raw)
    args = parse_args(remaining, description="Level 3: check an agreement against a checklist, one call per rule.")

    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="contract_review", level=LEVEL, model_id=model.model_id)
    checkpoint = run(args.question, model, tracer)

    print(f"{len(checkpoint.needs_review)} finding(s) need a person, {len(checkpoint.cleared)} cleared")
    for f in checkpoint.findings:
        note = f" -- {f.note}" if f.note else ""
        print(f"  {f.rule}: {f.status} (clause {f.clause}){note}")

    if reviewer.decision is None:
        print("(pass --decision acknowledged|sent_back to resume)")
        return 0
    record = resume(checkpoint, reviewer.decision, tracer, note=reviewer.note)
    print(f"reviewer decision: {record.reviewer_decision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
