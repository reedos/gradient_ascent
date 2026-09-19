"""Run the coding-agent example from the command line.

    python -m examples.coding_agents --model stub:scripted
    python -m examples.coding_agents --model stub --question "Fix sum_evens so it returns the sum of the even numbers in a list."

`--model stub` echoes the question back, which is never a tool call, so the model never proposes
an edit and the propose-run-test loop this page is about never turns.
`--model stub:scripted` plays SCRIPTED below: a first fix that is still wrong (it fails the same
tests the buggy source did, for a different reason), a second fix that passes every case, and the
model's own report that it is done.
"""
from __future__ import annotations

import sys

from examples.coding_agents.run import LEVEL, TASK, run
from examples.common.cli import build_cli_model, parse_args
from examples.common.model import StubResponse, ToolCall
from examples.common.trace import Tracer

DEFAULT_QUESTION = TASK

# A fix that still fails: it counts the even numbers instead of summing them, so the first test
# case returns 3 instead of 12.
_STILL_BROKEN_SOURCE = (
    "def sum_evens(numbers):\n"
    '    """Return the sum of the even numbers in numbers."""\n'
    "    total = 0\n"
    "    for n in numbers:\n"
    "        if n % 2 == 0:\n"
    "            total += 1\n"
    "    return total\n"
)
# The correct fix: sum the even numbers rather than counting them.
_CORRECT_SOURCE = (
    "def sum_evens(numbers):\n"
    '    """Return the sum of the even numbers in numbers."""\n'
    "    total = 0\n"
    "    for n in numbers:\n"
    "        if n % 2 == 0:\n"
    "            total += n\n"
    "    return total\n"
)

# Three model calls: a wrong first fix, a correct second fix, then the model's own decision to
# stop once the test result says every case passed. The same sequence
# tests/test_example_coding_agents.py scripts for its "a wrong fix then a right one takes three
# model decisions" end-to-end test.
SCRIPTED = [
    StubResponse(tool_calls=[ToolCall(name="propose_edit", arguments={"new_source": _STILL_BROKEN_SOURCE})]),
    StubResponse(tool_calls=[ToolCall(name="propose_edit", arguments={"new_source": _CORRECT_SOURCE})]),
    StubResponse(text="That fixed it."),
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 5: coding agent, propose-edit-run-test loop over a function held in memory.",
        default_question=DEFAULT_QUESTION,
    )
    model = build_cli_model(args.model, example="coding_agents", script=SCRIPTED)
    tracer = Tracer(example="coding_agents", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, None, tracer)
    # Every proposed edit and every test result live in the trace; print each step so a reader
    # sees the retry after the first fix fails, not only the final report.
    for step in tracer.steps:
        print(f"[{step.decided_by}] {step.title}: {step.detail}")
    print(answer.text)
    print("fixed:", "yes" if answer.citations else "no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
