"""Run the rubric grading example from the command line.

    python -m examples.rubric_grading --model stub --question "<a submission>"

`--question` fills this example's submission text, not a question; see `examples/common/cli.py`
for why every example takes `--question` regardless of what its first parameter means. The
interactive stub returns plain text, never the JSON the grader's schema asks for, so a plain
`--model stub` run always ends in a checkpoint (every criterion unevidenced); the accept and
reject paths are demonstrated with a scripted stub in
`tests/test_example_rubric_grading.py`.
"""
from __future__ import annotations

import sys

from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.common.trace import Tracer
from examples.rubric_grading.run import Checkpoint, LEVEL, run


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 6: grade against a rubric, with a second reader.",
    )
    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="rubric_grading", level=LEVEL, model_id=model.model_id)
    result = run(args.question, model, tracer)

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
