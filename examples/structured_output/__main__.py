"""Run the structured-output example from the command line.

    python -m examples.structured_output --model stub --question "What is the DW-480's warranty?"
"""
from __future__ import annotations

import sys

from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.common.trace import Tracer
from examples.structured_output.run import LEVEL, run


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 1: structured output, extract and validate a warranty record.",
    )
    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="structured_output", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, tracer)
    print(answer.text)
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
