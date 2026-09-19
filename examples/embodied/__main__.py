"""Run the embodied (robots and machines) example from the command line.

    python -m examples.embodied --model stub --question "A part sits 320mm to the right of home; pick it up quickly."

`--question` here becomes the scene description the model sees for one perceive-plan-act step.
"""
from __future__ import annotations

import sys

from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.common.trace import Tracer
from examples.embodied.run import LEVEL, Move, run_step


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 7: robots and machines, one perceive-plan-act step through a safety envelope.",
    )
    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="embodied", level=LEVEL, model_id=model.model_id)
    actuator_log: list[Move] = []

    result = run_step(model, tracer, scene=args.question, actuator_log=actuator_log)
    print(f"outcome: {result.outcome}")
    print(f"move sent toward the actuator: {result.move}")
    print(f"actuator log: {actuator_log}")
    if result.reason:
        print(f"reason: {result.reason}")
    if result.reason == "no move proposed":
        print("(--model stub never calls a tool, so there was nothing for the envelope to check;")
        print(" tests/test_example_embodied.py scripts models that propose moves it refuses and clamps.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
