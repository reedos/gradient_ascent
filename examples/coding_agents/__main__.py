"""Run the coding-agent example from the command line.

    python -m examples.coding_agents --model stub --question "Fix sum_evens so it returns the sum of the even numbers in a list."
"""
from __future__ import annotations

import sys

from examples.coding_agents.run import LEVEL, run
from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.common.trace import Tracer


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 5: coding agent, propose-edit-run-test loop over a function held in memory.",
    )
    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="coding_agents", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, None, tracer)
    print(answer.text)
    print("fixed:", "yes" if answer.citations else "no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
