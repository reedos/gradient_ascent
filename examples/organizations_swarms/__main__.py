"""Run the organizations-of-agents example from the command line.

    python -m examples.organizations_swarms --model stub --question "Fact-check the DW-300 section before it ships"

`--question` becomes one extra open task on the board, alongside three fixed ones, so a single
coordination round always has more than one thing to assign.
"""
from __future__ import annotations

import sys

from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.common.trace import Tracer
from examples.organizations_swarms.run import LEVEL, SAMPLE_TASKS, Board, Task, coordinate


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 7: organizations of agents, a shared task board and a coordinator.",
    )
    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="organizations_swarms", level=LEVEL, model_id=model.model_id)
    board = Board(tasks=[*SAMPLE_TASKS, Task(id="T4", description=args.question)])

    made = coordinate(board, model, tracer)
    print(f"assigned this round: {made}")
    print(f"still open: {[t.id for t in board.tasks if t.status == 'open']}")
    if not made:
        print("(the coordinator assigned nothing. --model stub never calls a tool;")
        print(" tests/test_example_organizations_swarms.py scripts one that over-assigns and double-claims.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
