"""Run the agent-graphs example from the command line.

    python -m examples.agent_graphs --model stub --question "What is the maximum vent run for the DR-520, and does anything supersede the manual's figure?"
"""
from __future__ import annotations

import sys

from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.common.trace import Tracer
from examples.agent_graphs.run import LEVEL, run


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 6: agent graphs, a supervisor node that hands off from an allowlist.",
    )
    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="agent_graphs", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, None, tracer)
    print(answer.text)
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
