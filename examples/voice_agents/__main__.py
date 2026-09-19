"""Run the voice-agents example from the command line.

    python -m examples.voice_agents --model stub:scripted
    python -m examples.voice_agents --model stub --question "What time do you close tonight?"

`--model stub` echoes the question back once with no tool call, so the model yields the floor
after a single chunk and the turn shows only one decision. `--model stub:scripted` plays SCRIPTED
below: the model speaks one chunk, calls `continue_speaking` to keep the floor, then speaks a
second chunk and stops on its own -- so the reader sees the chunk-by-chunk decision this page is
about, not a single flat answer.
"""
from __future__ import annotations

import sys

from examples.common.cli import build_cli_model, parse_args
from examples.common.model import StubResponse, ToolCall
from examples.common.trace import Tracer
from examples.voice_agents.run import LEVEL, run

DEFAULT_QUESTION = "What time do you close tonight?"

# Two model calls: the first chunk keeps talking, the second chunk yields the floor on its own,
# with no forced cut-off. The same sequence tests/test_example_voice_agents.py scripts for its
# multi-chunk test.
SCRIPTED = [
    StubResponse(text="We close at nine,", tool_calls=[ToolCall(name="continue_speaking", arguments={})]),
    "but the kitchen closes at eight-thirty.",
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 5: voice agents, a text simulation of one turn's control flow.",
        default_question=DEFAULT_QUESTION,
    )
    model = build_cli_model(args.model, example="voice_agents", script=SCRIPTED)
    tracer = Tracer(example="voice_agents", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, None, tracer)
    # Each chunk's decision to keep talking or yield is where this level's claim lives, so print
    # them before the assembled answer.
    for step in tracer.steps:
        if step.title in (
            "Model chooses to keep talking",
            "Model finishes and yields the floor",
            "Caller interrupts; code cuts the agent off",
            "Latency budget reached; code cuts the agent off",
            "Chunk cap reached; code cuts the agent off",
        ):
            print(f"{step.title}: {step.detail}")
    print(answer.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
