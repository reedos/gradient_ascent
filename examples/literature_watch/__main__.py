"""Run the literature-watch example from the command line.

    python -m examples.literature_watch --model stub --question ""

`--question` is the date the watch last ran, as YYYY-MM-DD. Leave it empty to use the module's
own sample date (`SAMPLE_INPUT`, 09/15/2026), which is what the recipe page walks through. The
sources are fixture records inside `run.py`; nothing here reaches the network.
"""
from __future__ import annotations

import sys

from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.common.trace import Tracer
from examples.literature_watch.run import LEVEL, SAMPLE_INPUT, run


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 1: a weekly watch joined to a per-item read, with citations attached by code.",
    )
    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="literature_watch", level=LEVEL, model_id=model.model_id)
    since = args.question.strip() or SAMPLE_INPUT
    digest = run(since, model, tracer)
    print(digest.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
