"""Run the long-running-task example from the command line.

    python -m examples.long_horizon --model stub --question "What does HLV-2205 cost?"

Each invocation is one simulated session against a checkpoint file. Pass --state twice with the
same path to see a second session load the first one's checkpoint instead of starting over.
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.common.trace import Tracer
from examples.long_horizon.run import LEVEL, run_session

_STATE_FLAGS = argparse.ArgumentParser(add_help=False)
_STATE_FLAGS.add_argument("--state", default=None, help="path to the checkpoint file (default: a new temp file)")


def _fresh_state_path() -> Path:
    """A new file for every run with no --state. A fixed name in the temp directory would mean
    the second run of the command in this module's docstring loaded the first run's finished
    queue and reported nothing to do, which is a confusing way to meet the example."""
    return Path(tempfile.mkdtemp(prefix="long_horizon_")) / "state.json"


def main(argv: list[str] | None = None) -> int:
    raw = sys.argv[1:] if argv is None else argv
    state_args, remaining = _STATE_FLAGS.parse_known_args(raw)
    args = parse_args(remaining, description="Level 7: long-running tasks, a queue worked across sessions.")

    state_path = Path(state_args.state) if state_args.state else _fresh_state_path()
    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="long_horizon", level=LEVEL, model_id=model.model_id)
    answer = run_session(state_path, model, tracer, questions=[args.question])

    if answer is None:
        print(f"no answer this session (queue empty, or flagged for a person) -- checkpoint at {state_path}")
    else:
        print(answer.text)
        print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
