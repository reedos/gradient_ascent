"""Run the memory example from the command line, with a small fixed set of synthetic facts
already written, then one new question answered from whichever of them recall thinks are
relevant.

    python -m examples.memory --model stub:scripted
    python -m examples.memory --model stub --question "Is my dishwasher still covered under warranty?"

`--model stub` echoes the question back, which is never a real judgment about the recalled facts.
`--model stub:scripted` plays SCRIPTED below: the answer a model would give once it read whatever
recall turned up for this question, over these facts.
"""
from __future__ import annotations

import sys

from examples.common.cli import build_cli_embedder, build_cli_model, parse_args
from examples.common.trace import Tracer
from examples.memory.run import LEVEL, run

DEFAULT_QUESTION = "Is my dishwasher still covered under warranty?"

SAMPLE_FACTS = [
    "Owns a Halvorsen DW-300 dishwasher, purchased 2024-03-15.",
    "The DW-300 is installed in a rental property the user manages.",
    "Prefers email over phone for service updates.",
    "Also owns a Halvorsen DR-520 dryer, electric version, purchased 2025-01-10.",
]

# One model call: recall already picked which facts are relevant (the purchase date and the
# rental-property fact), so one ask with them in the prompt is enough. Commercial and rental use
# caps coverage at 90 days from purchase (warranty-policy#3), and 2024-03-15 is well past that.
SCRIPTED = [
    "No. The DW-300 was purchased 2024-03-15 and is installed in a rental property, which limits "
    "coverage to 90 days from the purchase date. That window closed months ago.",
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 2: memory, write/recall/forget over a small synthetic fact set.",
        default_question=DEFAULT_QUESTION,
    )
    model = build_cli_model(args.model, example="memory", script=SCRIPTED)
    embedder = build_cli_embedder(args.embedder, model_spec=args.model)
    tracer = Tracer(example="memory", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, embedder, tracer, facts=SAMPLE_FACTS)
    print(answer.text)
    print("recalled:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
