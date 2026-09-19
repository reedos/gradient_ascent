"""Run the code-execution example from the command line.

    python -m examples.code_execution --model stub:scripted
    python -m examples.code_execution --model stub --question "..."

`--model stub` echoes the question back, which is text, not a valid arithmetic expression, so the
sandbox refuses it on the first call and the write-an-expression-then-answer shape this page is
about never shows.
`--model stub:scripted` plays SCRIPTED below: a valid expression built from numbers in the
retrieved sources, then a final answer once the sandbox has evaluated it.
"""
from __future__ import annotations

import sys

from examples.code_execution.run import LEVEL, run
from examples.common.cli import build_cli_model, parse_args
from examples.common.trace import Tracer

DEFAULT_QUESTION = "What is the total price to replace the heating elements on both a DW-300 and a DW-480?"

# Two model calls: the model writes one expression, the sandbox evaluates it, and the model's
# second reply is the final answer built from that value. This example never offers a tool, so
# both entries are plain text, not a StubResponse with tool_calls. The same sequence
# tests/test_example_code_execution.py scripts for its "writing a valid expression is the only
# model decided step" end-to-end test.
SCRIPTED = [
    "38.50 + 41.00",
    "$79.50 (parts-list#2).",
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 4: the model writes one expression, code runs it in a restricted evaluator.",
        default_question=DEFAULT_QUESTION,
    )
    model = build_cli_model(args.model, example="code_execution", script=SCRIPTED)
    tracer = Tracer(example="code_execution", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, None, tracer)
    # The expression the model wrote and the sandbox's evaluation of it both live in the trace;
    # print every step so a reader sees the one-decision-then-compute shape, not only the answer.
    for step in tracer.steps:
        print(f"[{step.decided_by}] {step.title}: {step.detail}")
    print(answer.text)
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
