"""Run the embeddings-and-search example from the command line.

    python -m examples.embeddings_search
    python -m examples.embeddings_search --model stub --question "DW-300 Normal cycle water use"

`--model` is accepted for a uniform interface with the other examples but is not used: this level
searches, it does not call a model, so there is no `stub:scripted` sequence to script here either.
Embedding always uses the deterministic stub unless a real `Embedder` is wired in by hand; there
is no `--embedder` flag here because the site's other examples do not have one either, and this
one has no answer-generation step to pair it with.
"""
from __future__ import annotations

import sys

from examples.common.cli import parse_args
from examples.common.model import StubEmbedder
from examples.common.trace import Tracer
from examples.embeddings_search.run import LEVEL, run

DEFAULT_QUESTION = "DW-300 Normal cycle water use"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 2: embeddings and search, semantic versus keyword hits for one query.",
        default_question=DEFAULT_QUESTION,
    )
    tracer = Tracer(example="embeddings_search", level=LEVEL, model_id="none")
    answer = run(args.question, None, StubEmbedder(), tracer)
    print(answer.text)
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
