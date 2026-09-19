"""Run the incident-runbook example from the command line.

    python -m examples.incident_runbook --model stub:scripted
    python -m examples.incident_runbook --model stub --question "(the write-up text)"

Pass --question "" (or leave it out) to use the module's own sample write-up. The draft always
pauses for the incident owner; pass --decision to resume it immediately with a scripted choice
(approve, edit or reject) instead of just printing the paused draft.

`--model stub` echoes the write-up back for both calls, which is never valid JSON, so both calls
retry once and both give up: the draft pauses with zero steps and nothing to approve. `--model
stub:scripted` plays SCRIPTED below: the timeline extraction and the drafted steps the sample
write-up actually produces, the same two replies tests/test_example_incident_runbook.py scripts
as its own good-path model and the recipe page's cost strip quotes the token counts for.
"""
from __future__ import annotations

import argparse
import json
import sys

from examples.common.cli import build_cli_model, parse_args
from examples.common.trace import Tracer
from examples.incident_runbook.run import LEVEL, SAMPLE_INPUT, resume, run

_OWNER_FLAGS = argparse.ArgumentParser(add_help=False)
_OWNER_FLAGS.add_argument("--decision", choices=["approve", "edit", "reject"], default=None)
_OWNER_FLAGS.add_argument("--note", default="")

# Two model calls: pull the timeline out of the write-up, then draft a runbook step for each
# repeatable event. Seven timeline events; four are repeatable (e2, e4, e5, e6) and become steps,
# three are one-off or never touched (the page firing, the join, the closing) and are left out.
SCRIPTED = [
    json.dumps({
        "events": [
            {"time": "02:14", "actor": "on-call system", "action": "pages jrivera; order-sync-worker queue-depth alert, over threshold"},
            {"time": "02:19", "actor": "jrivera", "action": "checks the queue-depth dashboard: order-sync-queue at 42,100 and climbing, normal is under 500"},
            {"time": "02:26", "actor": "jrivera", "action": "decides this is bad enough to wake the on-call lead and calls dcho"},
            {"time": "02:38", "actor": "dcho", "action": "restarts the order-sync-worker pool"},
            {"time": "02:47", "actor": "dcho", "action": "rolls the worker image back to the previous build; queue depth keeps climbing for a few minutes, the rollback alone does not change the direction"},
            {"time": "03:16", "actor": "jrivera", "action": "checks the order-sync-lag metric: back under 30 seconds, inside the normal range"},
            {"time": "03:20", "actor": "dcho", "action": "drafts a short email to the three enterprise accounts with delayed orders"},
        ]
    }),
    json.dumps({
        "steps": [
            {"action": "Check the order-sync-queue depth on the queue-depth dashboard", "role": "on-call engineer", "check": "depth is at or below 500", "from_event": "e2"},
            {"action": "Restart the order-sync-worker pool", "role": "on-call engineer", "check": "crash-looping pods report running and the crash count stops climbing", "from_event": "e4"},
            {"action": "If a recent deploy is suspected, roll back the image, but do not expect the rollback alone to drain the queue", "role": "on-call engineer", "check": "queue depth starts dropping only after the pool is restarted, not from the rollback by itself", "from_event": "e5"},
            {"action": "Check the order-sync-lag metric", "role": "on-call engineer", "check": "lag is back under 30 seconds", "from_event": "e6"},
        ]
    }),
]


def main(argv: list[str] | None = None) -> int:
    raw = sys.argv[1:] if argv is None else argv
    owner, remaining = _OWNER_FLAGS.parse_known_args(raw)
    args = parse_args(
        remaining,
        description="Level 3: incident write-up to draft runbook, pause and resume.",
        default_question=SAMPLE_INPUT,
    )

    model = build_cli_model(args.model, example="incident_runbook", script=SCRIPTED)
    tracer = Tracer(example="incident_runbook", level=LEVEL, model_id=model.model_id)
    pending = run(args.question, model, tracer)

    print(f"PAUSED for approval: {len(pending.steps)} step(s), {len(pending.dropped)} dropped")
    print(pending.text)
    if owner.decision is None:
        print("(pass --decision approve|edit|reject to resume)")
        return 0

    runbook = resume(pending, owner.decision, tracer, note=owner.note)
    print(runbook.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
