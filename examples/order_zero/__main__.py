"""Run the order-zero example from the command line.

    python -m examples.order_zero --question "How often should the DW-300's filter be cleaned?"

`--model` is accepted for a uniform interface with the other examples but is not used: level 0
calls no model.
"""
from __future__ import annotations

import sys

from examples.common.cli import parse_args
from examples.common.trace import Tracer
from examples.order_zero.run import LEVEL, run


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv, description="Level 0: keyword search, no model.")
    tracer = Tracer(example="order_zero", level=LEVEL, model_id="none")
    answer = run(args.question, None, None, tracer)
    print(answer.text)
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
