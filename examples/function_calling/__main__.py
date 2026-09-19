"""Run the function-calling example from the command line.

    python -m examples.function_calling --model stub:scripted
    python -m examples.function_calling --model stub --question "What does part HLV-2205 cost?"

`--model stub` echoes the question back, which is never a tool call, so the model always answers
directly and the one-tool-call shape this page is about never shows.
`--model stub:scripted` plays SCRIPTED below: the model calls lookup_part on the part number in
the question, the code runs it, and the model's second reply is the final answer built from the
tool result.
"""
from __future__ import annotations

import sys

from examples.common.cli import build_cli_model, parse_args
from examples.common.model import StubResponse, ToolCall
from examples.common.trace import Tracer
from examples.function_calling.run import LEVEL, run

DEFAULT_QUESTION = "What does part HLV-2205 cost?"

# Two model calls: the model calls lookup_part on the part number, then the code asks for a final
# answer once the tool result is in hand. The same sequence tests/test_example_function_calling.py
# scripts for its own end-to-end test.
SCRIPTED = [
    StubResponse(tool_calls=[ToolCall(name="lookup_part", arguments={"part_number": "HLV-2205"})]),
    StubResponse(text="Part HLV-2205 is a drain pump and costs $52.00. Sources: parts-list#2"),
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 4: one optional tool call.",
        default_question=DEFAULT_QUESTION,
    )
    model = build_cli_model(args.model, example="function_calling", script=SCRIPTED)
    tracer = Tracer(example="function_calling", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, None, tracer)
    # The model's one decision, and the tool result it was given to answer from, both live in the
    # trace rather than in the final text alone, so print every step before the answer.
    for step in tracer.steps:
        print(f"[{step.decided_by}] {step.title}: {step.detail}")
    print(answer.text)
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
