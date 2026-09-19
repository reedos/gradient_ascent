"""Run the one-call example from the command line.

    python -m examples.one_call --model stub:scripted
    python -m examples.one_call --model stub --question "What voltage does a DR-210 need?"

`--model stub` echoes the question back, which shows the shape of the run and nothing else.
`--model stub:scripted` plays SCRIPTED below: the one reply a model that had never seen the
Halvorsen manuals should give, which is the declining-to-guess answer this page is about.
"""
from __future__ import annotations

import sys

from examples.common.cli import build_cli_model, parse_args
from examples.common.trace import Tracer
from examples.one_call.run import LEVEL, run

DEFAULT_QUESTION = "What voltage does a DR-210 need?"

# One model call: build the prompt, ask once, return what came back.
SCRIPTED = [
    "I don't have any Halvorsen documentation here, so I can't tell you the DR-210's supply "
    "voltage. It is on the rating plate behind the door and in the installation section of the "
    "manual for that model. I would rather say I don't know than guess at a number you would "
    "wire to.",
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 1: one call, no documents.",
        default_question=DEFAULT_QUESTION,
    )
    model = build_cli_model(args.model, example="one_call", script=SCRIPTED)
    tracer = Tracer(example="one_call", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, None, tracer)
    print(answer.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
