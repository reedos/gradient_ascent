"""Run the review-and-debate example from the command line.

    python -m examples.debate_review --model stub --question "What is the maximum vent run for the DR-520?"
    python -m examples.debate_review --model stub:scripted

`--model stub` echoes the question back for both the author and the reviewer, so the reviewer's
own turn never starts with 'CHECK:' and the run always accepts the echo on the spot -- it never
shows a genuine independent search. `--model stub:scripted` plays SCRIPTED below: an author draft
that misses a superseding service bulletin, a reviewer that searches for one -- for real, against
the corpus, not an echo of the draft -- finds it, and rejects, naming it.
"""
from __future__ import annotations

import sys

from examples.common.cli import build_cli_model, parse_args
from examples.common.trace import Tracer
from examples.debate_review.run import LEVEL, run

DEFAULT_QUESTION = "What is the maximum vent run for the DR-520?"

# Three model calls: the author's draft, the reviewer's decision to check one claim, and the
# reviewer's verdict after its own search runs (code, not scripted -- see
# examples/debate_review/run.py's _reviewer_search) returns what the corpus actually says.
SCRIPTED = [
    "The DR-520's vent run is limited to 35 feet with up to 4 elbows. Sources: dr520-manual#4",
    "CHECK: DR-520 vent run service bulletin",
    "REJECT: the draft never checked for a superseding bulletin, and service-bulletin#1 confirms one revises this figure.",
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 6: review and debate, an independent reviewer with its own retrieval.",
        default_question=DEFAULT_QUESTION,
    )
    model = build_cli_model(args.model, example="debate_review", script=SCRIPTED)
    tracer = Tracer(example="debate_review", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, None, tracer)
    # The reviewer's own decisions, and what its own search actually found, are the whole point;
    # both live in the trace, so print them on the way to the final answer with its verdict.
    for step in tracer.steps:
        if step.decided_by == "model" or step.title == "Reviewer's own search runs":
            print(f"{step.title} ({step.decided_by}): {step.detail}")
    print(answer.text)
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
