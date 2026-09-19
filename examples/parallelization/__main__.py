"""Run the parallelization example from the command line.

    python -m examples.parallelization --model stub --question "What is the DW-480's Normal cycle water use, and how often should its filter be cleaned?"
"""
from __future__ import annotations

import sys

from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.common.trace import Tracer
from examples.parallelization.run import LEVEL, run


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv, description="Level 3: parallel calls, sectioning.")
    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="parallelization", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, None, tracer)
    print(answer.text)
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
