"""Run the project-tracker-upkeep example from the command line.

    python -m examples.project_tracker_upkeep --model stub:scripted

`--question` is the date the run stands on, as YYYY-MM-DD; it defaults to the module's own sample
date (`SAMPLE_INPUT`, 09/18/2026), which is what the recipe page walks through. The document and
the three sources are fixtures inside `run.py`; nothing here reaches the network.

Nothing this command prints has been written to the document except the changes marked "updated".
The rest is a queue for a person, which is the point of the recipe.

`SCRIPTED` is three replies, one per unread message, in the order the run reads them. The third
is an empty proposals list on purpose: most messages change nothing, and an example that never
shows that is teaching the wrong expectation.
"""
from __future__ import annotations

import json
import sys

from examples.common.cli import build_cli_model, parse_args
from examples.common.trace import Tracer
from examples.project_tracker_upkeep.run import LEVEL, SAMPLE_INPUT, run

#: One reply per message. Each quote below is copied from the message it belongs to, so all three
#: survive `_check_quotes`; `tests/test_example_project_tracker_upkeep.py` asserts that this is
#: the same sequence its own tests are written against.
SCRIPTED = [
    json.dumps(
        {
            "proposals": [
                {
                    "project": "Brightwater Commons",
                    "field": "milestone_date",
                    "value": "10/02/2026",
                    "quote": "the permit hearing has been moved to 10/02/2026",
                }
            ]
        }
    ),
    json.dumps(
        {
            "proposals": [
                {
                    "project": "Ferndale Library",
                    "field": "risk",
                    "value": "The board wants a line-by-line shelving breakdown before sign-off.",
                    "quote": "the board wants a line-by-line breakdown of the shelving costs",
                }
            ]
        }
    ),
    json.dumps({"proposals": []}),
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 3: reconcile a tracker document against its sources, and hold every overwrite for a person.",
        default_question=SAMPLE_INPUT,
    )
    model = build_cli_model(args.model, example="project_tracker_upkeep", script=SCRIPTED)
    tracer = Tracer(example="project_tracker_upkeep", level=LEVEL, model_id=model.model_id)
    as_of = args.question.strip() or SAMPLE_INPUT
    result = run(as_of, model, tracer)
    print(result.summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
