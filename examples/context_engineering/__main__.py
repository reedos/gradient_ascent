"""Run the context-engineering example from the command line.

    python -m examples.context_engineering --model stub:scripted
    python -m examples.context_engineering --model stub --question "What is the DW-300's Normal cycle water use?"

`--model stub` echoes the question back, which shows the request shape and nothing else.
`--model stub:scripted` plays SCRIPTED below: the one grounded answer a model that had the whole
document set in front of it would give.
"""
from __future__ import annotations

import sys

from examples.common.cli import build_cli_model, parse_args
from examples.common.trace import Tracer
from examples.context_engineering.run import LEVEL, run

DEFAULT_QUESTION = "What is the DW-300's Normal cycle water use?"

# One model call: the whole document set is already in the prompt, so one ask is enough.
SCRIPTED = [
    "3.2 gallons per Normal cycle, per the DW-300 manual's cycles section.",
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 2: context engineering, the whole document set in one prompt.",
        default_question=DEFAULT_QUESTION,
    )
    model = build_cli_model(args.model, example="context_engineering", script=SCRIPTED)
    tracer = Tracer(example="context_engineering", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, None, tracer)
    print(answer.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
