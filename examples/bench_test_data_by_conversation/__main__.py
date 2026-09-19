"""Run the test-data-by-conversation example from the command line.

    python -m examples.bench_test_data_by_conversation --model stub --question "..."

`--question` is the ad hoc question about the retest export, the soak log or the characterization
sweep; `run.py`'s module docstring says which tables are loaded and what the sandbox will and will
not run.
"""
from __future__ import annotations

import sys

from examples.bench_test_data_by_conversation.run import LEVEL, run
from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.common.trace import Tracer


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 4: the model writes one analysis snippet; a sandbox runs it.",
    )
    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="bench_test_data_by_conversation", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, tracer)
    print(answer.text)
    print("data:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
