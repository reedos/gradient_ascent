"""Run the structured-output example from the command line.

    python -m examples.structured_output --model stub:scripted
    python -m examples.structured_output --model stub --question "What is the DW-480's warranty?"

`--model stub` echoes the passage and question back, which is not JSON, so it never validates and
the retry always runs out with an error.
`--model stub:scripted` plays SCRIPTED below: a first reply that fails validation (a string where
an integer belongs), then the corrected reply the retry gets after the error is appended, so the
reader sees the retry actually happen rather than the same failure twice.
"""
from __future__ import annotations

import json
import sys

from examples.common.cli import build_cli_model, parse_args
from examples.common.trace import Tracer
from examples.structured_output.run import LEVEL, run

DEFAULT_QUESTION = "What is the DW-480's warranty?"

_VALID_RECORD = {
    "model": "DW-480",
    "full_warranty_years": 2,
    "limited_years": 5,
    "limited_scope": "dishwasher motor and tub",
    "commercial_rental_days": 90,
}

# Two model calls: a first reply that fails validation (full_warranty_years as a word instead of
# an integer), then a corrected reply after the code appends the validation error.
SCRIPTED = [
    json.dumps(dict(_VALID_RECORD, full_warranty_years="two")),
    json.dumps(_VALID_RECORD),
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 1: structured output, extract and validate a warranty record.",
        default_question=DEFAULT_QUESTION,
    )
    model = build_cli_model(args.model, example="structured_output", script=SCRIPTED)
    tracer = Tracer(example="structured_output", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, tracer)
    # The retry is the point of this level, and it lives in the trace rather than in the final
    # text alone, so print the validation step from each attempt beside the final record.
    for step in tracer.steps:
        if step.title in (
            "Ask the model for JSON",
            "Validate against the schema",
            "Ask again with the validation error",
        ):
            print(f"{step.title}: {step.detail}")
    print(answer.text)
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
