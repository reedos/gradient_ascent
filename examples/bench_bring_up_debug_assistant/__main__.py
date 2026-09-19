"""Run the bring-up debug assistant example from the command line.

    python -m examples.bench_bring_up_debug_assistant --model stub:scripted
    python -m examples.bench_bring_up_debug_assistant --model stub \\
        --question "SRB5030-2608-0011 failed VOUT on FIX-03. Why, and what should we check next?"

`--model stub` never calls a tool, so the loop stops on its first turn and the command prints a
placeholder cause with no tool use in the trace at all. `--model stub:scripted` plays SCRIPTED
below: the same six-tool-call walkthrough tests/test_example_bench_bring_up_debug_assistant.py
scripts for its own full-walkthrough test, ending on a stated cause and a next measurement rather
than a tool call.
"""
from __future__ import annotations

import sys

from examples.bench_bring_up_debug_assistant.run import LEVEL, run
from examples.common.cli import build_cli_model, parse_args
from examples.common.model import StubResponse, ToolCall
from examples.common.trace import Tracer

DEFAULT_QUESTION = "SRB5030-2608-0011 failed VOUT on FIX-03. Why, and what should we check next?"

# Seven model calls: six tool calls that read the log, two documents and three live measurements,
# then a final turn with no tool call, which is the model's own decision to stop. The same
# sequence tests/test_example_bench_bring_up_debug_assistant.py scripts for its full walkthrough.
SCRIPTED = [
    StubResponse(tool_calls=[ToolCall(name="test_log", arguments={"serial": "SRB5030-2608-0011"})]),
    StubResponse(tool_calls=[ToolCall(name="read_doc", arguments={"cite": "failure-analysis-guide#3"})]),
    StubResponse(tool_calls=[ToolCall(name="read_doc", arguments={"cite": "failure-analysis-guide#7"})]),
    StubResponse(tool_calls=[ToolCall(name="measure", arguments={"instrument": "dmm", "command": "MEAS:VOLT:DC?"})]),
    StubResponse(tool_calls=[ToolCall(name="measure", arguments={"instrument": "load", "command": "MEAS:VOLT?"})]),
    # A plausible next step for a model that has not yet been told the measure tool only queries:
    # a reset, refused before it ever reaches the DMM.
    StubResponse(tool_calls=[ToolCall(name="measure", arguments={"instrument": "dmm", "command": "*RST"})]),
    (
        "Cause: FIX-03's channel 2 offset, not the board. Only VOUT moved and the DMM disagrees "
        "with the load's own terminal reading by about the fixture's offset, the signature "
        "failure-analysis-guide#7 gives for a stale channel offset rather than an open sense "
        "lead. Next measurement: verify FIX-03 channel 2 per calibration-procedure#5, then "
        "retest this serial on another fixture per failure-analysis-guide#1."
    ),
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 5: bring-up debug assistant, read-only instrument and document tools.",
        default_question=DEFAULT_QUESTION,
    )
    model = build_cli_model(args.model, example="bench_bring_up_debug_assistant", script=SCRIPTED)
    tracer = Tracer(example="bench_bring_up_debug_assistant", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, tracer)
    # The tool calls and the one refusal are the point of a level 5 trace, and they live in the
    # trace rather than in the final answer, so print them before it.
    for step in tracer.steps:
        if step.kind == "model" or step.title.startswith("Run tool") or "Refuse" in step.title:
            print(f"{step.title}: {step.detail}")
    print(answer.text)
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
