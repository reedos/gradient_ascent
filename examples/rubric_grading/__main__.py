"""Run the rubric grading example from the command line.

    python -m examples.rubric_grading --model stub --question "<a submission>"
    python -m examples.rubric_grading --model stub:scripted

`--question` fills this example's submission text, not a question; see `examples/common/cli.py`
for why every example takes `--question` regardless of what its first parameter means. The
interactive stub returns plain text, never the JSON the grader's schema asks for, so a plain
`--model stub` run always ends in a checkpoint (every criterion unevidenced) after both retries,
and the reviewer never runs at all.

`--model stub:scripted` plays SCRIPTED below: the grader scores SAMPLE_INPUT (the misread-rubric-
line submission this recipe's own page walks through), the independent reviewer checks the one
criterion the grader misread, and rejects, naming it -- the same sequence
`site/src/data/runs/recipe-rubric-grading.json` shows and
`tests/test_example_rubric_grading.py`'s reject-path test already scripts by hand.
"""
from __future__ import annotations

import json
import sys

from examples.common.cli import build_cli_model, parse_args
from examples.common.trace import Tracer
from examples.rubric_grading.run import Checkpoint, LEVEL, SAMPLE_INPUT, run

# Three model calls: the grader scores all four criteria in one JSON reply, the independent
# reviewer checks the one criterion the grader misread (real, but not evidence of what the rubric
# asks for), and the reviewer rejects, naming it. The grader's scores below are
# tests/test_example_rubric_grading.py's own WEAK_SCORES, and the reviewer's two turns are its
# own WEAK_REJECT_REASON scenario, so this file and that test cannot drift apart in what they
# claim about SAMPLE_INPUT without the divergence-guard test below catching it.
_GRADER_JSON = json.dumps(
    {
        "scores": [
            {
                "criterion": "thesis",
                "points": 1,
                "quote": "I think lunch should probably be longer, maybe fifteen minutes more.",
                "reasoning": "A position is stated but hedged.",
            },
            {
                "criterion": "evidence",
                "points": 1,
                "quote": "The line for food takes a while some days too, so that eats into the time.",
                "reasoning": "General and not tied to a concrete detail.",
            },
            {
                "criterion": "counterargument",
                "points": 3,
                "quote": "I don't really have a counterargument because everyone agrees lunch should be longer anyway.",
                "reasoning": "Addresses the counterargument directly by stating there is none, because of consensus.",
            },
            {
                "criterion": "organization",
                "points": 1,
                "quote": "In conclusion, lunch should be longer.",
                "reasoning": "Paragraphs are not distinct; ideas repeat.",
            },
        ]
    }
)
SCRIPTED = [
    _GRADER_JSON,
    "CHECK: counterargument",
    "REJECT: counterargument scores 3 but the quote never states an opposing position, "
    "it only claims no one holds one, which the rubric's level 0 describes, not level 3.",
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 6: grade against a rubric, with a second reader.",
        default_question=SAMPLE_INPUT,
    )
    model = build_cli_model(args.model, example="rubric_grading", script=SCRIPTED)
    tracer = Tracer(example="rubric_grading", level=LEVEL, model_id=model.model_id)
    result = run(args.question, model, tracer)

    # Every reviewer turn is decided_by="model"; everything else, including the grader's own
    # call, is code's decision to make. Print both so a reader can tell which is which.
    for step in tracer.steps:
        if step.decided_by == "model" or step.title == "Return that criterion's rubric text and the submission again":
            print(f"{step.title} ({step.decided_by}): {step.detail}")
    if isinstance(result, Checkpoint):
        print(f"CHECKPOINT for the teacher: {result.reason}")
        print(result.detail)
        if result.unevidenced:
            print("unevidenced:", ", ".join(result.unevidenced))
    else:
        print(f"Proposed grade: {result.total_points}/{result.max_points}")
        for score in result.scores:
            print(f"  {score.criterion}: {score.points}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
