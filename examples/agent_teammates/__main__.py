"""Run the always-on-assistant example from the command line.

    python -m examples.agent_teammates --model stub --question "3 new emails: a newsletter, a
    meeting request from a client, and an invoice asking to be paid."

`--question` here is the digest of what changed since the last tick -- the CLI module this repo
shares across examples always calls that flag `--question`, so this example reuses it rather than
add a second argument parser for one flag.
"""
from __future__ import annotations

import sys

from examples.agent_teammates.run import LEVEL, Mailbox, run_tick
from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.common.trace import Tracer


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 7: always-on assistants, a scheduler tick and a three-class policy.",
    )
    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="agent_teammates", level=LEVEL, model_id=model.model_id)
    box = Mailbox()
    approvals: list[dict] = []
    result = run_tick(args.question, model, tracer, box, approvals=approvals)

    print(f"ran unattended: {result.executed}")
    print(f"queued for approval: {result.queued}")
    print(f"refused (forbidden): {result.refused}")
    if not (result.executed or result.queued or result.refused):
        print("(the model proposed nothing this tick, which is a valid answer. --model stub never")
        print(" calls a tool; tests/test_example_agent_teammates.py scripts one that proposes all three classes.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
