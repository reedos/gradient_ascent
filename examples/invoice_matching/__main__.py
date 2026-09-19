"""Run the invoice-matching example from the command line.

    python -m examples.invoice_matching --model stub:scripted
    python -m examples.invoice_matching --model stub --question "PO-4410"

The question is the invoice text; pass a short string to see the interactive stub's placeholder
reply fail validation, or leave --question out to run the module's own sample invoice. If the
match pauses, pass --decision to resume it immediately with a scripted reviewer choice (approve or
reject) instead of just printing the paused checkpoint.

`--model stub` echoes the invoice text back, which is never valid JSON, so extraction retries once
and then gives up: the run pauses with no invoice to show at all. `--model stub:scripted` plays
SCRIPTED below: the fields a real extraction reads out of SAMPLE_INPUT, which match PO-4410 and
what was actually received against it exactly, so the run posts without pausing -- the clean path
this recipe's own SAMPLE_INPUT is written for, and the same reply
tests/test_example_invoice_matching.py scripts for its own clean-match tests and the token counts
the recipe page quotes.
"""
from __future__ import annotations

import argparse
import json
import sys

from examples.common.cli import build_cli_model, parse_args
from examples.common.trace import Tracer
from examples.invoice_matching.run import LEVEL, SAMPLE_INPUT, PendingMatch, PostedInvoice, resume, run

_REVIEWER_FLAGS = argparse.ArgumentParser(add_help=False)
_REVIEWER_FLAGS.add_argument("--decision", choices=["approve", "reject"], default=None)
_REVIEWER_FLAGS.add_argument("--note", default="")

# One model call: SAMPLE_INPUT is an invoice that matches PO-4410 exactly, so a correct read of it
# is 40 bolts at $12.50 and 40 washers at $6.40, both fully received, totaling $756.00.
SCRIPTED = [
    json.dumps({
        "supplier": "Corrigan Fasteners",
        "po_number": "PO-4410",
        "invoice_number": "INV-77012",
        "currency": "USD",
        "line_items": [
            {"code": "FST-2201", "quantity": 40, "unit_price_cents": 1_250},
            {"code": "FST-2209", "quantity": 40, "unit_price_cents": 640},
        ],
        "total_cents": 75_600,
    }),
]


def main(argv: list[str] | None = None) -> int:
    raw = sys.argv[1:] if argv is None else argv
    reviewer, remaining = _REVIEWER_FLAGS.parse_known_args(raw)
    args = parse_args(
        remaining,
        description="Level 3: match an invoice to a purchase order and goods received.",
        default_question=SAMPLE_INPUT,
    )

    model = build_cli_model(args.model, example="invoice_matching", script=SCRIPTED)
    tracer = Tracer(example="invoice_matching", level=LEVEL, model_id=model.model_id)
    result = run(args.question, model, tracer)

    # Everything after the one read is code, not a verdict a reader has to take on faith: print
    # the lookup and the three-way comparison from the trace before printing what happened.
    for step in tracer.steps:
        if step.title in ("Look up the purchase order", "Compare invoiced, ordered and received"):
            print(f"{step.title}: {step.detail}")

    if isinstance(result, PendingMatch):
        print(f"PAUSED for accounts payable: {result.stage}")
        for reason in result.reasons:
            print(f"  {reason}")
        if reviewer.decision is None:
            print("(pass --decision approve|reject to resume)")
            return 0
        result = resume(result, reviewer.decision, tracer, note=reviewer.note)

    if isinstance(result, PostedInvoice):
        print(f"posted: {result.po_number} {result.invoice_number} to {result.supplier}, ${result.posted_cents / 100:.2f}")
    else:
        print(f"rejected: {result.po_number} {result.invoice_number} -- {result.reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
