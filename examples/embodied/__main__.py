"""Run the embodied (robots and machines) example from the command line.

    python -m examples.embodied --model stub:scripted
    python -m examples.embodied --model stub --question "A part sits 320mm to the right of home; pick it up quickly."

`--question` here becomes the scene description the model sees for one perceive-plan-act step.

`--model stub` never calls the `move` tool, so the envelope has nothing to check and refuses for
lack of a proposal. `--model stub:scripted` plays SCRIPTED below: a move that asks to go further
right than the workspace allows, at a speed above the cap -- "quickly," as the scene says -- so the
reader sees the model's own proposal and the envelope's code pulling it back to something safe.
"""
from __future__ import annotations

import sys

from examples.common.cli import build_cli_model, parse_args
from examples.common.model import StubResponse, ToolCall
from examples.common.trace import Tracer
from examples.embodied.run import LEVEL, Move, run_step

DEFAULT_QUESTION = "A part sits 320mm to the right of home; pick it up quickly."

# One model call: the model proposes a target past the workspace's x bound at a speed above the
# cap, so the envelope clamps both rather than refusing or actuating the raw proposal. The same
# sequence tests/test_example_embodied.py scripts for its own end-to-end test.
SCRIPTED = [
    StubResponse(tool_calls=[ToolCall(name="move", arguments={"x": 320.0, "y": 0.0, "z": 50.0, "speed": 400.0})]),
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 7: robots and machines, one perceive-plan-act step through a safety envelope.",
        default_question=DEFAULT_QUESTION,
    )
    model = build_cli_model(args.model, example="embodied", script=SCRIPTED)
    tracer = Tracer(example="embodied", level=LEVEL, model_id=model.model_id)
    actuator_log: list[Move] = []

    result = run_step(model, tracer, scene=args.question, actuator_log=actuator_log)
    # The model's own proposal is the trace's point as much as the envelope's verdict, so print
    # both.
    for step in tracer.steps:
        if step.title.startswith("Model proposes") or step.title.startswith("Safety envelope"):
            print(f"{step.title}: {step.detail}")
    print(f"outcome: {result.outcome}")
    print(f"move sent toward the actuator: {result.move}")
    print(f"actuator log: {actuator_log}")
    if result.reason:
        print(f"reason: {result.reason}")
    if result.reason == "no move proposed":
        print("(--model stub never calls a tool, so there was nothing for the envelope to check;")
        print(" --model stub:scripted plays a model that proposes a move the envelope clamps.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
