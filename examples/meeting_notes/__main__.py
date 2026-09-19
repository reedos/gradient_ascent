"""Run the meeting-notes example from the command line.

    python -m examples.meeting_notes --model stub:scripted
    python -m examples.meeting_notes --model stub --question ""

Leave --question empty to run against the module's own sample transcript (`SAMPLE_INPUT`); pass
your own transcript text instead to extract decisions from it.

`--model stub` echoes the transcript back, which is never valid JSON, so extraction retries once
and then gives up: the notes report an error and no decisions at all. `--model stub:scripted`
plays SCRIPTED below: the reply site/src/content/recipes/meeting-notes.mdx and its run diagram
walk through, the two real decisions plus one the model invented whose quote is nowhere in the
transcript, so the reader sees a decision get dropped and reported rather than silently removed.
The same reply and its token counts are pinned in
tests/test_example_meeting_notes.py's PAGE_RUN_RECORD.
"""
from __future__ import annotations

import json
import sys

from examples.common.cli import build_cli_model, parse_args
from examples.common.trace import Tracer
from examples.meeting_notes.run import LEVEL, SAMPLE_INPUT, run

# One model call: attendees, two grounded decisions, and a third the model invented -- a quote
# that never appears in the transcript -- which the grounding check drops and reports.
SCRIPTED = [
    json.dumps({
        "attendees": ["Priya Okafor", "Marcus Chen", "Deshawn Fitts", "Yuki Tanaka"],
        "decisions": [
            {
                "decision": "Ship the three-step signup flow on Friday.",
                "owner": "Marcus",
                "due_date": "Friday",
                "quote": "We're shipping the three-step signup flow on Friday.",
            },
            {
                "decision": "The FAQ for the new signup flow goes to whoever is on support rotation next week.",
                "owner": "whoever's on support rotation next week",
                "due_date": "",
                "quote": "the FAQ goes to whoever's on support rotation next week.",
            },
            {
                "decision": "Cut the marketing budget by half.",
                "owner": "Deshawn",
                "due_date": "",
                "quote": "We agreed to cut the marketing budget by half.",
            },
        ],
        "open_questions": [
            "Whether the new usage-based pricing applies to the team, or whether they are grandfathered into the old tier.",
        ],
    }),
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 1: meeting notes, extract decisions, owners and open questions.",
        default_question=SAMPLE_INPUT,
    )
    model = build_cli_model(args.model, example="meeting_notes", script=SCRIPTED)
    tracer = Tracer(example="meeting_notes", level=LEVEL, model_id=model.model_id)
    transcript = args.question.strip() or SAMPLE_INPUT
    notes = run(transcript, model, tracer)
    print(notes.text)
    print("citations:", ", ".join(notes.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
