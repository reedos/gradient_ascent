"""Run the inference-time-reasoning example from the command line.

    python -m examples.inference_time_reasoning --model stub \
        --question "What is the total price to replace the heating elements on both a DW-300 and a DW-480?"
"""
from __future__ import annotations

import sys

from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.common.trace import Tracer
from examples.inference_time_reasoning.run import LEVEL, N_SAMPLES, run


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 1: inference-time reasoning, self-consistency by majority vote.",
    )
    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="inference_time_reasoning", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, tracer, n=N_SAMPLES)
    print(answer.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
