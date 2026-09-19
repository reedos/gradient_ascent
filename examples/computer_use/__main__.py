"""Run the computer-use example from the command line.

    python -m examples.computer_use --model stub --question "Search for warranty information"
"""
from __future__ import annotations

import sys

from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.common.trace import Tracer
from examples.computer_use.run import LEVEL, run


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 4: the model picks one action on a screen; code runs it or refuses it.",
    )
    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="computer_use", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, None, tracer)
    print(answer.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
