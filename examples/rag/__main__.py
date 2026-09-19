"""Run the RAG example from the command line.

    python -m examples.rag --model stub:scripted
    python -m examples.rag --model stub --question "What is the DW-300's Normal cycle water use?"

`--model stub` echoes the question back, which shows the retrieval and prompt shape but never
carries a "Sources:" line, so citation parsing always comes up empty.
`--model stub:scripted` plays SCRIPTED below: the one grounded, cited answer a model reading the
retrieved sources would give.
"""
from __future__ import annotations

import sys

from examples.common.cli import build_cli_embedder, build_cli_model, parse_args
from examples.common.trace import Tracer
from examples.rag.run import LEVEL, run

DEFAULT_QUESTION = "What is the DW-300's Normal cycle water use?"

# One model call: retrieval already picked the sources, so one ask with them in the prompt is
# enough.
SCRIPTED = [
    "3.2 gallons per Normal cycle. Sources: dw300-manual#3",
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 2: RAG, top-k chunks with citations.",
        default_question=DEFAULT_QUESTION,
    )
    model = build_cli_model(args.model, example="rag", script=SCRIPTED)
    embedder = build_cli_embedder(args.embedder, model_spec=args.model)
    tracer = Tracer(example="rag", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, embedder, tracer)
    print(answer.text)
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
