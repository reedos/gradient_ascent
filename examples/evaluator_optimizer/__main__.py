"""Run the evaluator-optimizer example from the command line.

    python -m examples.evaluator_optimizer --model stub --question "How often should the DW-300's filter be cleaned?"
    python -m examples.evaluator_optimizer --model stub:scripted

`--model stub` echoes the question back, which the checker always fails (it is never
PASS_TOKEN), so a plain run always burns the whole revision cap and never shows a pass.
`--model stub:scripted` plays SCRIPTED below: a first draft that cites a real corpus section it
was not actually given, a checker that catches it, a revision that fixes it, and a checker that
then passes -- the same draft-fails-then-revision-passes sequence this page's own illustrated
trace (site/src/data/runs/evaluator-optimizer.json) shows.
"""
from __future__ import annotations

import sys

from examples.common.cli import build_cli_model, parse_args
from examples.common.trace import Tracer
from examples.evaluator_optimizer.run import LEVEL, run

DEFAULT_QUESTION = "How often should the DW-300's filter be cleaned?"

# Four model calls: draft, check (fails), revise, check (passes). Retrieval for DEFAULT_QUESTION
# returns care-and-cleaning-guide#1, care-and-cleaning-guide#4, dw300-manual#7, parts-list#1; the
# first draft cites dw300-manual#6 instead, a real section of the real corpus that simply was not
# one of those four, which the checker catches and the revision fixes by citing one that was.
SCRIPTED = [
    "Every 30 cycles. Sources: dw300-manual#6",
    "MISSING: dw300-manual#6",
    "Every 30 cycles, per the care and cleaning guide.\nSources: care-and-cleaning-guide#1",
    "ALL CITATIONS SUPPORTED",
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 3: write and check, capped revision loop.",
        default_question=DEFAULT_QUESTION,
    )
    model = build_cli_model(args.model, example="evaluator_optimizer", script=SCRIPTED)
    tracer = Tracer(example="evaluator_optimizer", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, None, tracer)
    # The failed first draft and the checker's own feedback are what this page is about; both
    # live in the trace, so print them on the way to the final, passing answer.
    for step in tracer.steps:
        if step.kind == "model" or step.title.startswith("Stop:"):
            print(f"{step.title}: {step.detail}")
    print(answer.text)
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
