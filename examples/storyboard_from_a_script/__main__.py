"""Run the storyboard-from-a-script example from the command line.

    python -m examples.storyboard_from_a_script --model stub --question "1. A hand opens a box."

The question is the numbered script to storyboard, in "N. text" lines; leave it empty to run the
module's own SAMPLE_INPUT script. `--model stub` uses the generic interactive stub, which never
replies with real JSON, so the run below falls back to an empty scene and shot list rather than
crashing; the scripted responses that actually exercise the chain live in the tests.
"""
from __future__ import annotations

from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.common.trace import Tracer
from examples.storyboard_from_a_script.run import LEVEL, SAMPLE_INPUT, run


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or __import__("sys").argv[1:], description="Level 3: turn a script into a shot list.")
    script = args.question.strip() or SAMPLE_INPUT
    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="storyboard_from_a_script", level=LEVEL, model_id=model.model_id)
    report = run(script, model, tracer)
    print(report.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
