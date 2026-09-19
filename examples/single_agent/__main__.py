"""Run the single-agent example from the command line.

    python -m examples.single_agent --model stub:scripted
    python -m examples.single_agent --model stub --question "What does the DW-300's drain pump cost, and how long is it under warranty?"

`--model stub` echoes the question back for every call: the plan call gets it as plain text (that
part is real, since the plan call takes no tools), but the loop that follows never receives a
tool call from it, so the model always stops on its first turn and the plan-then-act shape this
page is about never shows.
`--model stub:scripted` plays SCRIPTED below: a plan, two actions on that plan (a search and a
lookup), and a final answer once the model decides it has enough.
"""
from __future__ import annotations

import sys

from examples.common.cli import build_cli_model, parse_args
from examples.common.model import StubResponse, ToolCall
from examples.common.trace import Tracer
from examples.single_agent.run import LEVEL, run

DEFAULT_QUESTION = "What does the DW-300's drain pump cost, and how long is it under warranty?"

# Four model calls: the plan (text only, no tools offered), two actions the model takes on that
# plan, and the stop. The same sequence tests/test_example_single_agent.py scripts for its
# "records a model-decided step for every action and the stop" end-to-end test.
SCRIPTED = [
    StubResponse(text="1. Search for the warranty term. 2. Look up the part price."),
    StubResponse(tool_calls=[ToolCall(name="search", arguments={"query": "DW-300 full warranty parts and labor"})]),
    StubResponse(tool_calls=[ToolCall(name="lookup_part", arguments={"part_number": "HLV-2201"})]),
    # Every section this names is one the two tool calls above actually returned. The citations
    # this example reports come from the tools rather than from the reply, so a scripted answer
    # citing something retrieval never found would print an answer and a citation list that
    # contradict each other.
    StubResponse(text="$46.00, covered in full for 2 years. Sources: parts-list#2, warranty-policy#1"),
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 5: single agent, plan-and-execute loop.",
        default_question=DEFAULT_QUESTION,
    )
    model = build_cli_model(args.model, example="single_agent", script=SCRIPTED)
    tracer = Tracer(example="single_agent", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, None, tracer)
    # The plan, each action the model takes on it, and the stop are all trace steps; print them
    # in order so the loop's turns are visible, not just the answer they end in.
    for step in tracer.steps:
        print(f"[{step.decided_by}] {step.title}: {step.detail}")
    print(answer.text)
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
