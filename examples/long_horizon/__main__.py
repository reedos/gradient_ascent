"""Run the long-running-task example from the command line.

    python -m examples.long_horizon --model stub:scripted
    python -m examples.long_horizon --model stub --question "What does HLV-2205 cost?"

Each invocation is one simulated session against a checkpoint file. Pass --state twice with the
same path to see a second session load the first one's checkpoint instead of starting over.

`--model stub` never calls the `answer` or `flag_for_review` tool, so the session falls back to
the echoed question with no citations and the checkpoint records an unconfident answer. `--model
stub:scripted` plays SCRIPTED below: the session calls `answer` with a real citation from the
corpus, so the reader sees the one decision this page is about -- answer, grounded, or flag -- and
the checkpoint it leaves behind.
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from examples.common.cli import build_cli_model, parse_args
from examples.common.model import StubResponse, ToolCall
from examples.common.trace import Tracer
from examples.long_horizon.run import LEVEL, run_session

_STATE_FLAGS = argparse.ArgumentParser(add_help=False)
_STATE_FLAGS.add_argument("--state", default=None, help="path to the checkpoint file (default: a new temp file)")

DEFAULT_QUESTION = "What does the DW-300's drain pump cost?"

# One model call: the session answers with a grounded citation rather than flagging the question
# for a person. The same sequence tests/test_example_long_horizon.py scripts for its
# one-model-decided-step test.
SCRIPTED = [
    StubResponse(tool_calls=[ToolCall(name="answer", arguments={"text": "$46.00, part HLV-2201.", "citations": ["parts-list#2"]})]),
]


def _fresh_state_path() -> Path:
    """A new file for every run with no --state. A fixed name in the temp directory would mean
    the second run of the command in this module's docstring loaded the first run's finished
    queue and reported nothing to do, which is a confusing way to meet the example."""
    return Path(tempfile.mkdtemp(prefix="long_horizon_")) / "state.json"


def main(argv: list[str] | None = None) -> int:
    raw = sys.argv[1:] if argv is None else argv
    state_args, remaining = _STATE_FLAGS.parse_known_args(raw)
    args = parse_args(
        remaining,
        description="Level 7: long-running tasks, a queue worked across sessions.",
        default_question=DEFAULT_QUESTION,
    )

    state_path = Path(state_args.state) if state_args.state else _fresh_state_path()
    model = build_cli_model(args.model, example="long_horizon", script=SCRIPTED)
    tracer = Tracer(example="long_horizon", level=LEVEL, model_id=model.model_id)
    answer = run_session(state_path, model, tracer, questions=[args.question])

    # The scheduler trigger and the session's own decision live in the trace, not only in the
    # returned answer, so print them before it.
    for step in tracer.steps:
        if step.title in (
            "Scheduler starts a session",
            "Rebuild context from notes, not the transcript",
            "Model decides whether to answer or flag this question",
            "Record the answer and compact a note",
            "Hand the question to a person",
        ):
            print(f"{step.title}: {step.detail}")

    if answer is None:
        print(f"no answer this session (queue empty, or flagged for a person) -- checkpoint at {state_path}")
    else:
        print(answer.text)
        print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
