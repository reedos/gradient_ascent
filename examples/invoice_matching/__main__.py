"""Run the invoice-matching example from the command line.

    python -m examples.invoice_matching --model stub --question "PO-4410"

The question is the invoice text; pass a short string to see the interactive stub's placeholder
reply fail validation, or edit this file to pass one of the module's own sample invoices. If the
match pauses, pass --decision to resume it immediately with a scripted reviewer choice (approve or
reject) instead of just printing the paused checkpoint.
"""
from __future__ import annotations

import argparse
import sys

from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.common.trace import Tracer
from examples.invoice_matching.run import LEVEL, PendingMatch, resume, run

_REVIEWER_FLAGS = argparse.ArgumentParser(add_help=False)
_REVIEWER_FLAGS.add_argument("--decision", choices=["approve", "reject"], default=None)
_REVIEWER_FLAGS.add_argument("--note", default="")


def main(argv: list[str] | None = None) -> int:
    raw = sys.argv[1:] if argv is None else argv
    reviewer, remaining = _REVIEWER_FLAGS.parse_known_args(raw)
    args = parse_args(remaining, description="Level 3: match an invoice to a purchase order and goods received.")

    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="invoice_matching", level=LEVEL, model_id=model.model_id)
    result = run(args.question, model, tracer)

    if isinstance(result, PendingMatch):
        print(f"PAUSED for accounts payable: {result.stage}")
        for reason in result.reasons:
            print(f"  {reason}")
        if reviewer.decision is None:
            print("(pass --decision approve|reject to resume)")
            return 0
        result = resume(result, reviewer.decision, tracer, note=reviewer.note)

    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
