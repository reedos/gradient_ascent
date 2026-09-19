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
from examples.prompt_engineering.run import LEVEL, STRUCTURED_SYSTEM, run

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
    # The interactive stub (--model stub) only ever echoes the last user message, which is the
    # same passage-and-question text either way, so `answer.text` alone cannot show what changed
    # between the two runs: the difference is in the system prompt, not the reply. Print it, and
    # print the same PART/PRICE check the technique page describes, so the two commands are
    # actually distinguishable and the check's pass/fail is visible even against the stub.
    print(f"structured: {args.structured}")
    if args.structured:
        print(f"system prompt: {STRUCTURED_SYSTEM!r}")
    else:
        print("system prompt: none; the bare prompt is just the passage and the question")
    print(f"reply: {answer.text}")
    print("matched PART/PRICE format:", "yes" if answer.citations else "no")
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
