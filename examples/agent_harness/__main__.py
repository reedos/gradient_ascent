"""Run the agent-harness example from the command line.

    python -m examples.agent_harness --model stub --question "What does the DW-300's drain pump cost, and how long is it under warranty?"

Runs with the default harness: every tool result kept, no hook. See tests/test_example_agent_harness.py
for the same question run through a tight context policy and a veto hook instead.
"""
from __future__ import annotations

import sys

from examples.agent_harness.run import LEVEL, run
from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.common.trace import Tracer


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv, description="Level 5: the agent harness, default configuration."
    )
    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="agent_harness", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, None, tracer)
    print(answer.text)
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
