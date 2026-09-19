"""Run the skills example from the command line.

    python -m examples.skills --model stub --question "Is the DW-480 drain pump covered under warranty, and for how long?"
"""
from __future__ import annotations

import sys

from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.common.trace import Tracer
from examples.skills.run import LEVEL, run


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv, description="Level 5: skills, a model-chosen load from a registry."
    )
    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="skills", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, None, tracer)
    print(answer.text)
    print("skills loaded:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
