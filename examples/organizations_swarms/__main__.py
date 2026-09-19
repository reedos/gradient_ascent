"""Run the organizations-of-agents example from the command line.

    python -m examples.organizations_swarms --model stub:scripted
    python -m examples.organizations_swarms --model stub --question "Fact-check the DW-300 section before it ships"

`--question` becomes one extra open task on the board, alongside three fixed ones, so a single
coordination round always has more than one thing to assign.

`--model stub` never calls the `assign` tool, so the round hands out nothing and every task stays
open. `--model stub:scripted` plays SCRIPTED below: one coordination round that assigns all four
open tasks across the three roles, then tries to hand the same task to a second role in the same
call -- so the reader sees both the split of work across roles and the board refuse the double
claim, exactly the guarantee this page is about.
"""
from __future__ import annotations

import sys

from examples.common.cli import build_cli_model, parse_args
from examples.common.model import StubResponse, ToolCall
from examples.common.trace import Tracer
from examples.organizations_swarms.run import LEVEL, SAMPLE_TASKS, Board, Task, coordinate

DEFAULT_QUESTION = "Fact-check the DW-300 section before it ships"

# One model call, proposing five assignments: the coordinator hands each of the four open tasks
# (T1-T3 fixed, T4 built from the question) to a role, then tries to also give T1 -- already
# claimed by the first proposal in this same call -- to a second role. The same sequence
# tests/test_example_organizations_swarms.py scripts for its own end-to-end test.
SCRIPTED = [
    StubResponse(
        tool_calls=[
            ToolCall(name="assign", arguments={"task_id": "T1", "role": "researcher"}),
            ToolCall(name="assign", arguments={"task_id": "T2", "role": "writer"}),
            ToolCall(name="assign", arguments={"task_id": "T3", "role": "reviewer"}),
            ToolCall(name="assign", arguments={"task_id": "T4", "role": "researcher"}),
            ToolCall(name="assign", arguments={"task_id": "T1", "role": "writer"}),
        ]
    ),
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 7: organizations of agents, a shared task board and a coordinator.",
        default_question=DEFAULT_QUESTION,
    )
    model = build_cli_model(args.model, example="organizations_swarms", script=SCRIPTED)
    tracer = Tracer(example="organizations_swarms", level=LEVEL, model_id=model.model_id)
    board = Board(tasks=[*SAMPLE_TASKS, Task(id="T4", description=args.question)])

    made = coordinate(board, model, tracer)
    # The coordinator's own proposal and what the board did with each one are the point of this
    # level, so print the trace before the final tallies.
    for step in tracer.steps:
        if step.title == "Coordinator assigns open tasks to roles" or step.title.startswith("Refuse") or step.title.startswith("Claim"):
            print(f"{step.title}: {step.detail}")
    print(f"assigned this round: {made}")
    print(f"still open: {[t.id for t in board.tasks if t.status == 'open']}")
    if not made:
        print("(the coordinator assigned nothing. --model stub never calls a tool;")
        print(" --model stub:scripted plays a round that over-assigns and double-claims.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
