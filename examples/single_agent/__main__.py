"""Run the single-agent example from the command line.

    python -m examples.single_agent --model stub --question "What does the DW-300's drain pump cost, and how long is it under warranty?"
"""
from __future__ import annotations

import sys

from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.common.trace import Tracer
from examples.single_agent.run import LEVEL, run


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv, description="Level 5: single agent, plan-and-execute loop."
    )
    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="single_agent", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, None, tracer)
    print(answer.text)
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
