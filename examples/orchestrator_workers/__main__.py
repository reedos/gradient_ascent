"""Run the lead-agent-and-workers example from the command line.

    python -m examples.orchestrator_workers --model stub --question "What is the DW-300's annual energy use, and how much does the DR-520's drive belt cost?"
"""
from __future__ import annotations

import sys

from examples.common.cli import interactive_stub, parse_args
from examples.common.model import StubEmbedder, build_embedder, build_model
from examples.common.trace import Tracer
from examples.orchestrator_workers.run import LEVEL, run


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 6: lead agent and workers, a model-decided split over RAG workers.",
    )
    model = build_model(args.model, stub=interactive_stub())
    embedder = build_embedder(args.model, stub=StubEmbedder())
    tracer = Tracer(example="orchestrator_workers", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, embedder, tracer)
    print(answer.text)
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
