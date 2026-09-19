"""Run the memory example from the command line, with a small fixed set of synthetic facts
already written, then one new question answered from whichever of them recall thinks are
relevant.

    python -m examples.memory --model stub --question "Is my dishwasher still covered under warranty?"
"""
from __future__ import annotations

import sys

from examples.common.cli import interactive_stub, parse_args
from examples.common.model import StubEmbedder, build_embedder, build_model
from examples.common.trace import Tracer
from examples.memory.run import LEVEL, run

SAMPLE_FACTS = [
    "Owns a Halvorsen DW-300 dishwasher, purchased 2024-03-15.",
    "The DW-300 is installed in a rental property the user manages.",
    "Prefers email over phone for service updates.",
    "Also owns a Halvorsen DR-520 dryer, electric version, purchased 2025-01-10.",
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 2: memory, write/recall/forget over a small synthetic fact set.",
    )
    model = build_model(args.model, stub=interactive_stub())
    # `build_embedder` takes "stub" or "ollama:<tag>" only, so a `claude:` model spec (which has
    # no embedding endpoint behind this interface) recalls with the stub rather than crashing.
    embedder = build_embedder(args.model if args.model.startswith("ollama:") else "stub", stub=StubEmbedder())
    tracer = Tracer(example="memory", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, embedder, tracer, facts=SAMPLE_FACTS)
    print(answer.text)
    print("recalled:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
