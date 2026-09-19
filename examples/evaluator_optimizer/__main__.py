"""Run the evaluator-optimizer example from the command line.

    python -m examples.evaluator_optimizer --model stub --question "How often should the DW-300's filter be cleaned?"
"""
from __future__ import annotations

import sys

from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.common.trace import Tracer
from examples.evaluator_optimizer.run import LEVEL, run


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv, description="Level 3: write and check, capped revision loop.")
    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="evaluator_optimizer", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, None, tracer)
    print(answer.text)
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
