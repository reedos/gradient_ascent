"""Run the prompt-engineering example from the command line.

    python -m examples.prompt_engineering --model stub --structured
    python -m examples.prompt_engineering --model stub --no-structured
"""
from __future__ import annotations

import argparse
import sys

from examples.common.cli import interactive_stub
from examples.common.model import build_model
from examples.common.trace import Tracer
from examples.prompt_engineering.run import LEVEL, run

DEFAULT_QUESTION = "What is the DW-480's drain pump part number and price?"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Level 1: prompt engineering, structured vs. bare.")
    parser.add_argument("--model", default="stub", help="stub | ollama:<tag> | claude:<id>")
    parser.add_argument("--question", default=DEFAULT_QUESTION)
    parser.add_argument("--structured", dest="structured", action="store_true", default=True)
    parser.add_argument("--no-structured", dest="structured", action="store_false")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="prompt_engineering", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, tracer, structured=args.structured)
    print(answer.text)
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
