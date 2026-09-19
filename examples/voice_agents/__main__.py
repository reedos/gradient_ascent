"""Run the voice-agents example from the command line.

    python -m examples.voice_agents --model stub --question "What time do you close tonight?"
"""
from __future__ import annotations

import sys

from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.common.trace import Tracer
from examples.voice_agents.run import LEVEL, run


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 5: voice agents, a text simulation of one turn's control flow.",
    )
    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="voice_agents", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, None, tracer)
    print(answer.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
