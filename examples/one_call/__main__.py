"""Run the one-call example from the command line.

    python -m examples.one_call --model stub --question "What voltage does a DR-210 need?"
"""
from __future__ import annotations

import sys

from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.common.trace import Tracer
from examples.one_call.run import LEVEL, run


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv, description="Level 1: one call, no documents.")
    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="one_call", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, None, tracer)
    print(answer.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
