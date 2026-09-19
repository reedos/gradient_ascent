"""Run the prompt-chaining example from the command line.

    python -m examples.prompt_chaining --model stub --question "Is the DR-520 vent length still 35 feet?"
    python -m examples.prompt_chaining --model stub:scripted

`--model stub` echoes the question back for both calls, so the rewrite step always produces one
query (the question itself) and the draft step always echoes rather than citing anything real.
`--model stub:scripted` plays SCRIPTED below: a real rewrite into three differently worded
queries, then a draft that cites the corpus section those extra queries are needed to find.
"""
from __future__ import annotations

import sys

from examples.common.cli import build_cli_model, parse_args
from examples.common.trace import Tracer
from examples.prompt_chaining.run import LEVEL, run

DEFAULT_QUESTION = "Is the DR-520 vent length still 35 feet?"

# Two model calls: rewrite the question into search queries, then draft an answer from what
# retrieval found. The rewrite is written as three differently worded queries on purpose: a
# single query ("DR-520 vent length") ranks the corrected section (service-bulletin#2) below its
# top 2 results, and the extra two queries are what actually bring it in -- the same fact
# tests/test_example_prompt_chaining.py's MaxQueriesTests proves about MAX_QUERIES.
SCRIPTED = [
    "DR-520 vent length\nDR-520 service bulletin update\nDR-520 vent specification revision",
    "The maximum vent run for the DR-520 is now 25 feet. Sources: service-bulletin#2",
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 3: prompt chaining, fixed steps.",
        default_question=DEFAULT_QUESTION,
    )
    model = build_cli_model(args.model, example="prompt_chaining", script=SCRIPTED)
    tracer = Tracer(example="prompt_chaining", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, None, tracer)
    # The four fixed steps, and the citation check dropping what retrieval never found, live in
    # the trace, not the final text alone; print them so the chain itself is visible.
    for step in tracer.steps:
        print(f"{step.title}: {step.detail}")
    print(answer.text)
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
