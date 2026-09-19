"""Run the agentic-RAG example from the command line.

    python -m examples.agentic_rag --model stub --question "Does the 2026 bulletin affect the DR-210?"
"""
from __future__ import annotations

import sys

from examples.agentic_rag.run import LEVEL, run
from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.common.trace import Tracer


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv, description="Level 5: agentic RAG, search/read loop.")
    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="agentic_rag", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, None, tracer)
    print(answer.text)
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
