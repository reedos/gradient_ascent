"""Run the MCP example from the command line.

    python -m examples.mcp --model stub:scripted
    python -m examples.mcp --model stub --question "..."

`--model stub` echoes the question back, which is never a tool call, so the run never reaches the
stand-in MCP server's `tools/call` and the point of this page never shows.
`--model stub:scripted` plays SCRIPTED below: the model calls the one tool the stand-in server
lists, the server returns matching sections, and the model's second reply answers from them.
"""
from __future__ import annotations

import sys

from examples.common.cli import build_cli_model, parse_args
from examples.common.model import StubResponse, ToolCall
from examples.common.trace import Tracer
from examples.mcp.run import LEVEL, run

DEFAULT_QUESTION = "What does part HLV-2205 cost?"

# Two model calls: the model calls search_halvorsen_docs through the stand-in server, then the
# code asks for a final answer once the tool result is in hand. The same sequence
# tests/test_example_mcp.py scripts for its own end-to-end test.
SCRIPTED = [
    StubResponse(tool_calls=[ToolCall(name="search_halvorsen_docs", arguments={"query": "HLV-2205"})]),
    StubResponse(text="HLV-2205 is a drain pump that costs $52.00. Sources: parts-list#2"),
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 4: the model calls a tool listed by a stand-in MCP server.",
        default_question=DEFAULT_QUESTION,
    )
    model = build_cli_model(args.model, example="mcp", script=SCRIPTED)
    tracer = Tracer(example="mcp", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, None, tracer)
    # The list/call round trip through the stand-in server, and the model's one decision, live in
    # the trace; print every step so a reader sees the protocol shape, not only the answer.
    for step in tracer.steps:
        print(f"[{step.decided_by}] {step.title}: {step.detail}")
    print(answer.text)
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
