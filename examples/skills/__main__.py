"""Run the skills example from the command line.

    python -m examples.skills --model stub:scripted
    python -m examples.skills --model stub --question "Is the DW-480 drain pump covered under warranty, and for how long?"

`--model stub` echoes the question back, which is never a tool call, so the model always answers
without ever calling load_skill, and the progressive-disclosure shape this page is about never
shows.
`--model stub:scripted` plays SCRIPTED below: the model loads the one skill whose description
fits the question, then answers using its body.
"""
from __future__ import annotations

import sys

from examples.common.cli import build_cli_model, parse_args
from examples.common.model import StubResponse, ToolCall
from examples.common.trace import Tracer
from examples.skills.run import LEVEL, run

DEFAULT_QUESTION = "Is the DW-480 drain pump covered under warranty, and for how long?"

# Two model calls: the model loads the warranty-checklist skill, then answers once its body is in
# context. The same sequence tests/test_example_skills.py scripts for its "choosing a skill and
# stopping are the only model decisions" end-to-end test.
SCRIPTED = [
    StubResponse(tool_calls=[ToolCall(name="load_skill", arguments={"name": "warranty-checklist"})]),
    StubResponse(text="Covered: the 2-year warranty applies and nothing here voids it."),
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 5: skills, a model-chosen load from a registry.",
        default_question=DEFAULT_QUESTION,
    )
    model = build_cli_model(args.model, example="skills", script=SCRIPTED)
    tracer = Tracer(example="skills", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, None, tracer)
    # Which skill the model chose to load, and the decision to stop, both live in the trace;
    # print every step so a reader sees the load happen before the answer that follows it.
    for step in tracer.steps:
        print(f"[{step.decided_by}] {step.title}: {step.detail}")
    print(answer.text)
    print("skills loaded:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
