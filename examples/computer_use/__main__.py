"""Run the computer-use example from the command line.

    python -m examples.computer_use --model stub:scripted
    python -m examples.computer_use --model stub --question "Search for warranty information"

`--model stub` echoes the question back, which is never a tool call, so the model always answers
directly and the pick-one-action-on-a-screen shape this page is about never shows.
`--model stub:scripted` plays SCRIPTED below: the model types the search term into the one field
the allowlist permits, and the code runs it.
"""
from __future__ import annotations

import sys

from examples.common.cli import build_cli_model, parse_args
from examples.common.model import StubResponse, ToolCall
from examples.common.trace import Tracer
from examples.computer_use.run import LEVEL, run

DEFAULT_QUESTION = "Search for warranty information"

# One model call: the model picks exactly one action, this level never takes a second screenshot.
# The same call tests/test_example_computer_use.py scripts for its "clicking an allowed element is
# the only model decided step" end-to-end test, adapted here to typing into the search field
# instead, since that is the action this question would actually call for.
SCRIPTED = [
    StubResponse(tool_calls=[ToolCall(name="type", arguments={"id": "search-box", "text": "warranty"})]),
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 4: the model picks one action on a screen; code runs it or refuses it.",
        default_question=DEFAULT_QUESTION,
    )
    model = build_cli_model(args.model, example="computer_use", script=SCRIPTED)
    tracer = Tracer(example="computer_use", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, None, tracer)
    # The screen render and the model's one choice both live in the trace; print every step so a
    # reader sees what the model picked and whether the allowlist let it run.
    for step in tracer.steps:
        print(f"[{step.decided_by}] {step.title}: {step.detail}")
    print(answer.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
