"""Run the ask-the-datasheet example from the command line.

    python -m examples.bench_ask_the_datasheet --model stub --question "What is the maximum
    input voltage of the SRB-5030, revision B, per its recommended operating conditions?"
"""
from __future__ import annotations

import sys

from examples.bench_ask_the_datasheet.run import LEVEL, run
from examples.common.cli import interactive_stub, parse_args
from examples.common.model import StubEmbedder, build_embedder, build_model
from examples.common.trace import Tracer


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 2: ask the datasheet, top-k chunks over the bench corpus with a revision-scoped JSON answer.",
    )
    model = build_model(args.model, stub=interactive_stub())
    embedder = build_embedder(args.embedder or args.model, stub=StubEmbedder())
    tracer = Tracer(example="bench_ask_the_datasheet", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, embedder, tracer)
    print(answer.text)
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
