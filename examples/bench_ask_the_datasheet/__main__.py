"""Run the ask-the-datasheet example from the command line.

    python -m examples.bench_ask_the_datasheet --model stub:scripted
    python -m examples.bench_ask_the_datasheet --model stub --question "What is the maximum
    input voltage of the SRB-5030, revision B, per its recommended operating conditions?"

`--model stub` echoes the question back, which never validates, so the command prints the "did
not validate" outcome and nothing else. `--model stub:scripted` plays SCRIPTED below: a first
reply that names the revision but cites only the datasheet, the validation failure that is this
recipe's whole point, and a second reply that also cites the notice that supersedes the
datasheet's number.
"""
from __future__ import annotations

import json
import sys

from examples.bench_ask_the_datasheet.run import LEVEL, run
from examples.common.cli import build_cli_embedder, build_cli_model, parse_args
from examples.common.trace import Tracer

DEFAULT_QUESTION = (
    "What is the maximum input voltage of the SRB-5030, revision B, per its recommended "
    "operating conditions?"
)

#: What each source is filed under in the corpus. Both are retrieved for DEFAULT_QUESTION in one
#: search; `tests/test_example_bench_ask_the_datasheet.py` proves that.
DATASHEET_CITE = "srb5030-datasheet#3"  # "Recommended Operating Conditions": states 36.0 V
ECN_CITE = "ecn-2608-04#1"  # "Change": supersedes it to 32.0 V for revisions A and B

#: The right answer, correctly scoped and fully cited.
CORRECT_RECORD = {
    "answer": "The maximum input voltage is 32.0 V, not the datasheet's 36.0 V.",
    "applies_to_revision": "A and B",
    "citations": [ECN_CITE, DATASHEET_CITE],
}

#: The same answer and the same revision, with the superseding notice left off the citation list.
#: Naming the revision right is not enough on its own; this is the exact trap the recipe exists
#: to catch, and `_validate` rejects it even though every other field is correct.
DATASHEET_ONLY_RECORD = dict(CORRECT_RECORD, citations=[DATASHEET_CITE])

# Two model calls: a first reply that gets the answer and the revision right but cites only the
# datasheet, the validation failure that is this recipe's whole point, and a second reply that
# also cites the notice that supersedes the datasheet's number. The same sequence
# tests/test_example_bench_ask_the_datasheet.py scripts for its own end-to-end test.
SCRIPTED = [
    json.dumps(DATASHEET_ONLY_RECORD),
    json.dumps(CORRECT_RECORD),
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 2: ask the datasheet, top-k chunks over the bench corpus with a revision-scoped JSON answer.",
        default_question=DEFAULT_QUESTION,
    )
    model = build_cli_model(args.model, example="bench_ask_the_datasheet", script=SCRIPTED)
    embedder = build_cli_embedder(args.embedder, model_spec=args.model)
    tracer = Tracer(example="bench_ask_the_datasheet", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, embedder, tracer)
    # The retry itself is the point: a reply that names the revision but skips the superseding
    # notice fails validation before it ever reaches the reader as an answer, so print that step
    # beside the final one.
    for step in tracer.steps:
        if step.title in ("Ask again with the validation error", "Validate the reply"):
            print(f"{step.title}: {step.detail}")
    print(answer.text)
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
