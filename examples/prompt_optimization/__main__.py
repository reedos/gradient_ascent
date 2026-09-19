"""Run the prompt optimization example from the command line.

    python -m examples.prompt_optimization --model stub

No training API is contacted and nothing is written to disk; this only searches, selects and
reports scores.
"""
from __future__ import annotations

import argparse
import sys

from examples.common.cli import interactive_stub
from examples.common.model import build_model
from examples.common.trace import Tracer
from examples.prompt_optimization.run import run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Search candidate instructions on a development split; report the winner on a held-out split.")
    parser.add_argument("--model", default="stub", help="stub | ollama:<tag> | claude:<id>")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="prompt_optimization", level=1, model_id=model.model_id)
    result = run(tracer, model)

    for c in result.candidates:
        marker = " <- selected" if c.instruction == result.selected else ""
        print(f"{c.dev_correct}/{c.dev_total} dev  {c.instruction!r}{marker}")
    print(f"held-out score for the selected candidate: {result.held_out_correct}/{result.held_out_total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
