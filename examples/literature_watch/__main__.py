"""Run the literature-watch example from the command line.

    python -m examples.literature_watch --model stub:scripted
    python -m examples.literature_watch --model stub --question ""

`--question` is the date the watch last ran, as YYYY-MM-DD. Leave it empty to use the module's
own sample date (`SAMPLE_INPUT`, 09/15/2026), which is what the recipe page walks through. The
sources are fixture records inside `run.py`; nothing here reaches the network.

The watch half calls no model at all (a date comparison and a set difference), but the read half
does: one call per new record. `--model stub` echoes each record back, which is never valid JSON,
so both new records fail to summarize after a retry and the digest reports two failures with zero
items. `--model stub:scripted` plays SCRIPTED below: the two summaries a real read of those
records produces, the same replies tests/test_example_literature_watch.py scripts as its own
canonical run.
"""
from __future__ import annotations

import json
import sys

from examples.common.cli import build_cli_model, parse_args
from examples.common.trace import Tracer
from examples.literature_watch.run import LEVEL, SAMPLE_INPUT, run

# Two model calls: one per new record the watch half finds for the sample week (the journal
# source is read before the preprint source, since the watch walks its sources by name).
SCRIPTED = [
    json.dumps({
        "what_is_new": "Matches 2,800 anonymized walking trips against a modeled shade map at the hour each trip was taken.",
        "why_it_matters": "It puts a number on how far people will walk out of their way for shade, and the temperature at which they stop.",
        "read_if": "You are deciding where shade is worth building along a walking route.",
    }),
    json.dumps({
        "what_is_new": "Two years of operating a 120-unit street-level logger network, including the failures.",
        "why_it_matters": "The enclosure revision and the field calibration procedure are both published.",
        "read_if": "You are running or planning a low-cost sensor network outdoors.",
    }),
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 1: a weekly watch joined to a per-item read, with citations attached by code.",
        default_question=SAMPLE_INPUT,
    )
    model = build_cli_model(args.model, example="literature_watch", script=SCRIPTED)
    tracer = Tracer(example="literature_watch", level=LEVEL, model_id=model.model_id)
    since = args.question.strip() or SAMPLE_INPUT
    digest = run(since, model, tracer)
    print(digest.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
