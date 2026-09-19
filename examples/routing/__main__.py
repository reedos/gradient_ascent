"""Run the routing example from the command line.

    python -m examples.routing --model stub:scripted
    python -m examples.routing --model stub --question "What does HLV-2205 cost?"

`--model stub` echoes the question back, and the echo is never one of the three labels, so every
question lands in the `unclear` route and the demo shows the fallback and nothing else.
`--model stub:scripted` plays SCRIPTED below: a classifier that answers `lookup`, then the
lookup route's answer, so the reader sees the label, the route the code picked from it, and a
grounded citation.
"""
from __future__ import annotations

import sys

from examples.common.cli import build_cli_model, parse_args
from examples.common.trace import Tracer
from examples.routing.run import LEVEL, run

DEFAULT_QUESTION = "How often should the DW-300's filter be cleaned?"

# Two model calls on this question: classify, then answer inside the lookup route. The same
# sequence tests/test_example_routing.py scripts for its lookup-route test.
SCRIPTED = [
    "lookup",
    "Every 30 cycles. Sources: dw300-manual#6",
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 3: routing, classify then dispatch.",
        default_question=DEFAULT_QUESTION,
    )
    model = build_cli_model(args.model, example="routing", script=SCRIPTED)
    tracer = Tracer(example="routing", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, None, tracer)
    # The label and the route it selected are the whole point of this level, and they live in the
    # trace rather than in the answer text, so print them beside the answer.
    for step in tracer.steps:
        if step.title in ("Classify the question", "Route on the label"):
            print(f"{step.title}: {step.detail}")
    print(answer.text)
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
