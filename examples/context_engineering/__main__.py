"""Run the context-engineering example from the command line.

    python -m examples.context_engineering --model stub --question "What is the DW-300's Normal cycle water use?"
"""
from __future__ import annotations

import sys

from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.common.trace import Tracer
from examples.context_engineering.run import LEVEL, run


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 2: context engineering, the whole document set in one prompt.",
    )
    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="context_engineering", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, None, tracer)
    print(answer.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
