"""Run the routing example from the command line.

    python -m examples.routing --model stub --question "What does HLV-2205 cost?"
"""
from __future__ import annotations

import sys

from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.routing.run import LEVEL, run
from examples.common.trace import Tracer


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv, description="Level 3: routing, classify then dispatch.")
    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="routing", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, None, tracer)
    print(answer.text)
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
