"""Run the workflow-graphs example from the command line.

    python -m examples.workflow_graphs --model stub --question "How often should the DW-300's filter be cleaned?"
    python -m examples.workflow_graphs --model stub:scripted

`--model stub` echoes the question back, which the check node always fails, so a plain run always
hits MAX_REVISIONS and never shows the graph's ordinary path. `--model stub:scripted` plays
SCRIPTED below: the same draft-fails-then-revision-passes sequence as
`examples/evaluator_optimizer` (the two share DRAFT_SYSTEM, CHECK_SYSTEM and REVISE_SYSTEM, and
retrieval for DEFAULT_QUESTION returns the same four sections either way), so the run visits
retrieve, draft, check, revise and check again, and every checkpoint is true about what the
retrieve node actually returned.
"""
from __future__ import annotations

import sys

from examples.common.cli import build_cli_model, parse_args
from examples.common.trace import Tracer
from examples.workflow_graphs.run import LEVEL, run

DEFAULT_QUESTION = "How often should the DW-300's filter be cleaned?"

# Four model calls: draft, check (fails), revise, check (passes). Retrieval for DEFAULT_QUESTION
# returns care-and-cleaning-guide#1, care-and-cleaning-guide#4, dw300-manual#7, parts-list#1; the
# first draft cites dw300-manual#6 instead, a real section of the real corpus that simply was not
# one of those four, which the check node catches and the revise node fixes by citing one that
# was actually retrieved. Run the same question with one built from gibberish words for the
# retrieve node's other edge, straight to 'no_match' with no model call at all -- see this page's
# own Try It.
SCRIPTED = [
    "Every 30 cycles. Sources: dw300-manual#6",
    "MISSING: dw300-manual#6",
    "Every 30 cycles, per the care and cleaning guide.\nSources: care-and-cleaning-guide#1",
    "ALL CITATIONS SUPPORTED",
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 3: workflow graphs, a dict-based graph runner.",
        default_question=DEFAULT_QUESTION,
    )
    model = build_cli_model(args.model, example="workflow_graphs", script=SCRIPTED)
    tracer = Tracer(example="workflow_graphs", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, None, tracer)
    # Which nodes the run visited, and what each checkpoint recorded, is the point of a graph
    # runner; both live in the trace rather than in the answer text, so print them beside it.
    for step in tracer.steps:
        if step.title.startswith("Node:") or step.title.startswith("Checkpoint after"):
            print(f"{step.title}: {step.detail}")
    print(answer.text)
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
