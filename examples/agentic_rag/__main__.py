"""Run the agentic-RAG example from the command line.

    python -m examples.agentic_rag --model stub:scripted
    python -m examples.agentic_rag --model stub --question "Does the 2026 bulletin affect the DR-210?"

`--model stub` echoes the question back, which is never a tool call, so the model stops on its
first turn and the search-then-read loop this page is about never turns.
`--model stub:scripted` plays SCRIPTED below: the model searches, reads the section that search
turned up (since search returns titles only, not full text), and answers once it has read enough.
"""
from __future__ import annotations

import sys

from examples.agentic_rag.run import LEVEL, run
from examples.common.cli import build_cli_model, parse_args
from examples.common.model import StubResponse, ToolCall
from examples.common.trace import Tracer

DEFAULT_QUESTION = "How often should the DW-300's filter be cleaned?"

# Three model calls: search, read the section search named, then stop and answer. The same
# sequence tests/test_example_agentic_rag.py scripts for its "records a model-decided step for
# every tool call and the stop" end-to-end test.
SCRIPTED = [
    StubResponse(tool_calls=[ToolCall(name="search", arguments={"query": "DW-300 filter"})]),
    StubResponse(tool_calls=[ToolCall(name="read", arguments={"cite": "dw300-manual#6"})]),
    StubResponse(text="Every 30 cycles, per dw300-manual#6."),
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 5: agentic RAG, search/read loop.",
        default_question=DEFAULT_QUESTION,
    )
    model = build_cli_model(args.model, example="agentic_rag", script=SCRIPTED)
    tracer = Tracer(example="agentic_rag", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, None, tracer)
    # Each tool call and the stop are model-decided trace steps; print them in order so the loop
    # turning from search to read to answer is visible, not only the final text.
    for step in tracer.steps:
        print(f"[{step.decided_by}] {step.title}: {step.detail}")
    print(answer.text)
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
