"""Run the agent-harness example from the command line.

    python -m examples.agent_harness --model stub:scripted
    python -m examples.agent_harness --model stub --question "What does the DW-300's drain pump cost, and how long is it under warranty?"

Runs with the default harness: every tool result kept, no hook. See tests/test_example_agent_harness.py
for the same question run through a tight context policy and a veto hook instead.

`--model stub` echoes the question back, which is never a tool call, so the model stops on its
first turn and the pluggable-parts loop this page is about never turns.
`--model stub:scripted` plays SCRIPTED below: a search, a lookup, and a final answer that reads
from both tool results, which is what the default (generous) context policy leaves it able to do.
"""
from __future__ import annotations

import sys

from examples.agent_harness.run import LEVEL, run
from examples.common.cli import build_cli_model, parse_args
from examples.common.model import StubResponse, ToolCall
from examples.common.trace import Tracer

DEFAULT_QUESTION = "What does the DW-300's drain pump cost, and how long is it under warranty?"

# Three model calls: search for the warranty term, look up the part price, then answer from both
# results, which stay in context under the default keep_everything policy. This mirrors the
# scripted responder tests/test_example_agent_harness.py uses to show the harness changes the
# outcome: the same three-call shape, fixed here into an ordered sequence for the generous policy
# this command runs with by default.
SCRIPTED = [
    StubResponse(tool_calls=[ToolCall(name="search", arguments={"query": "DW-300 warranty term"})]),
    StubResponse(tool_calls=[ToolCall(name="lookup_part", arguments={"part_number": "HLV-2201"})]),
    StubResponse(text="$46.00, and the DW-300 has a 2-year full warranty."),
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 5: the agent harness, default configuration.",
        default_question=DEFAULT_QUESTION,
    )
    model = build_cli_model(args.model, example="agent_harness", script=SCRIPTED)
    tracer = Tracer(example="agent_harness", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, None, tracer)
    # Every action the model picks, and what the harness did with it, live in the trace; print
    # each step so a reader sees the loop turn from search to lookup to answer.
    for step in tracer.steps:
        print(f"[{step.decided_by}] {step.title}: {step.detail}")
    print(answer.text)
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
