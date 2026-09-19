"""Run the contract review example from the command line.

    python -m examples.contract_review --model stub:scripted
    python -m examples.contract_review --model stub --question ""

An empty --question uses the built-in invented agreement; pass any other text with numbered
clauses ("1. ...\\n2. ...") to check a different one against the same checklist. The run always
returns a checkpoint; pass --decision to resume it immediately with a scripted reviewer choice
(acknowledged or sent_back) instead of just printing the findings.

`--model stub` sends the same one-rule-alone prompt six times but the interactive stub echoes the
prompt back, which is never valid JSON, so every rule downgrades to `unclear` and the run shows six
identical, uninformative findings. `--model stub:scripted` plays SCRIPTED below: the six real
findings this checklist produces against the built-in agreement, the same replies
tests/test_example_contract_review.py scripts for its own full-run assertions and the token counts
the recipe page quotes.
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
from typing import Any

from examples.common.cli import SCRIPTED_SPEC, build_cli_model, parse_args
from examples.common.model import Model
from examples.common.trace import Tracer
from examples.contract_review.run import LEVEL, resume, run

_REVIEWER_FLAGS = argparse.ArgumentParser(add_help=False)
_REVIEWER_FLAGS.add_argument("--decision", choices=["acknowledged", "sent_back"], default=None)
_REVIEWER_FLAGS.add_argument("--note", default="")

# Six model calls, one per checklist rule, in CHECKLIST order: payment_terms, liability_cap,
# notice_period, assignment, governing_law, data_deletion. Each reply is the finding that rule
# actually produces against the built-in agreement, copied verbatim from
# tests/test_example_contract_review.py's own _REPLIES so the two cannot drift apart.
SCRIPTED = [
    json.dumps({
        "rule": "payment_terms", "status": "breach", "clause": 5,
        "quote": "Client shall pay each Vendor invoice within forty-five (45) days of the invoice date.",
    }),
    json.dumps({
        "rule": "liability_cap", "status": "meets", "clause": 9,
        "quote": (
            "Vendor's total liability arising under this Agreement shall not exceed the fees "
            "paid by Client in the twelve (12) months preceding the event giving rise to the claim."
        ),
    }),
    json.dumps({
        "rule": "notice_period", "status": "meets", "clause": 7,
        "quote": "Either party may terminate this Agreement for convenience upon sixty (60) days' prior written notice to the other party.",
    }),
    json.dumps({
        "rule": "assignment", "status": "breach", "clause": 12,
        "quote": "Either party may assign this Agreement, in whole or in part, to any third party without the other party's consent",
    }),
    json.dumps({
        "rule": "governing_law", "status": "unclear", "clause": 13,
        "quote": "governed by the laws of the state in which Vendor maintains its principal place of business",
    }),
    json.dumps({
        "rule": "data_deletion", "status": "missing", "clause": None, "quote": "",
    }),
]


class _SerializedModel:
    """Wraps a `Model` so its `complete` calls are serialized with a lock.

    `run` calls the model from a `ThreadPoolExecutor`, one thread per checklist rule at once, and
    `examples/common/cli.py`'s scripted stub advances its reply counter with no lock of its own
    (it is a fixture for a manual run, not something built for concurrent callers). Without this,
    two threads can read the same counter value before either writes it back, so two rules
    consume the same scripted reply and one reply in SCRIPTED never gets used at all. Serializing
    here fixes that: every reply in SCRIPTED is consumed exactly once. Which physical rule lands
    on which reply can still vary between runs -- the lock does not make the thread pool schedule
    threads in submission order -- but every run of `--model stub:scripted` now shows six distinct,
    populated findings rather than sometimes dropping one to a duplicate. Only used for the
    scripted stub: a live backend's own concurrency is untouched."""

    def __init__(self, model: Model) -> None:
        self._model = model
        self._lock = threading.Lock()
        self.model_id = model.model_id

    def complete(self, *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            return self._model.complete(*args, **kwargs)


def main(argv: list[str] | None = None) -> int:
    raw = sys.argv[1:] if argv is None else argv
    reviewer, remaining = _REVIEWER_FLAGS.parse_known_args(raw)
    args = parse_args(
        remaining,
        description="Level 3: check an agreement against a checklist, one call per rule.",
        # `default_question=""` rather than SAMPLE_INPUT itself: `run` already treats an empty
        # question as the built-in agreement (see run.py), and SAMPLE_INPUT *is* that agreement's
        # full text, which contains a literal "%" (clause 5's interest rate). argparse's own help
        # formatting in Python 3.14 rejects a help string with a bare "%" in it at add_argument
        # time, so passing the actual SAMPLE_INPUT text here crashes every invocation, not just
        # --help. Passing "" gets the same run-time behavior without carrying a second constant.
        default_question="",
    )

    model = build_cli_model(args.model, example="contract_review", script=SCRIPTED)
    if args.model == SCRIPTED_SPEC:
        model = _SerializedModel(model)
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
