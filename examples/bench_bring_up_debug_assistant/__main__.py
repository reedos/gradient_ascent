"""Run the bring-up debug assistant example from the command line.

    python -m examples.bench_bring_up_debug_assistant --model stub \\
        --question "SRB5030-2608-0011 failed VOUT on FIX-03. Why, and what should we check next?"
"""
from __future__ import annotations

import sys

from examples.bench_bring_up_debug_assistant.run import LEVEL, run
from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.common.trace import Tracer


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 5: bring-up debug assistant, read-only instrument and document tools.",
    )
    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="bench_bring_up_debug_assistant", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, tracer)
    print(answer.text)
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
