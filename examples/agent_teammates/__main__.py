"""Run the always-on-assistant example from the command line.

    python -m examples.agent_teammates --model stub:scripted
    python -m examples.agent_teammates --model stub --question "3 new emails: a newsletter, a
    meeting request from a client, and an invoice asking to be paid."

`--question` here is the digest of what changed since the last tick -- the CLI module this repo
shares across examples always calls that flag `--question`, so this example reuses it rather than
add a second argument parser for one flag.

`--model stub` never calls a tool, so the tick proposes nothing and the three-class policy never
fires. `--model stub:scripted` plays SCRIPTED below: one tick that proposes one action from each
of the three classes in a single call, so the reader sees the policy actually sort them rather
than a tick that found nothing to do.
"""
from __future__ import annotations

import sys

from examples.agent_teammates.run import LEVEL, Mailbox, run_tick
from examples.common.cli import build_cli_model, parse_args
from examples.common.model import StubResponse, ToolCall
from examples.common.trace import Tracer

DEFAULT_QUESTION = (
    "3 new emails: a newsletter, a meeting request from a client, and an invoice asking to be paid."
)

# One model call, proposing three actions in a single tick: one from each policy class, so the
# reader sees all three outcomes -- auto, approval, forbidden -- in one run. The same sequence
# tests/test_example_agent_teammates.py scripts for its all-three-classes test.
SCRIPTED = [
    StubResponse(
        tool_calls=[
            ToolCall(name="archive_email", arguments={"detail": "newsletter"}),
            ToolCall(name="send_email", arguments={"detail": "confirm the meeting"}),
            ToolCall(name="make_payment", arguments={"detail": "pay the invoice, $4,200"}),
        ]
    ),
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 7: always-on assistants, a scheduler tick and a three-class policy.",
        default_question=DEFAULT_QUESTION,
    )
    model = build_cli_model(args.model, example="agent_teammates", script=SCRIPTED)
    tracer = Tracer(example="agent_teammates", level=LEVEL, model_id=model.model_id)
    box = Mailbox()
    approvals: list[dict] = []
    result = run_tick(args.question, model, tracer, box, approvals=approvals)

    print(f"ran unattended: {result.executed}")
    print(f"queued for approval: {result.queued}")
    print(f"refused (forbidden): {result.refused}")
    if not (result.executed or result.queued or result.refused):
        print("(the model proposed nothing this tick, which is a valid answer. --model stub never")
        print(" calls a tool; --model stub:scripted plays a tick that proposes all three classes.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
