"""Run the knowledge-graphs example from the command line.

    python -m examples.knowledge_graphs --model stub
    python -m examples.knowledge_graphs --model stub --question "What warranty class covers the model HLV-5520 fits?"

`--model stub` replays a fixed extraction instead of calling anything: `REPLAYED_TRIPLES` below
holds the triples a model would have to state for the two source sections, transcribed by hand
from `evals/corpus/parts-list.md` and `evals/corpus/warranty-policy.md`. That is what makes the
graph walk runnable with no model and no network, and it is a replay, not a reading: it shows
what the code does with triples, never what a model's extraction of those documents looks like.
Point `--model` at a real backend for that.

This is already what the other examples' `--model stub:scripted` is for: unlike the generic echo
stub, `--model stub` here plays a real, fixed sequence of two extraction replies and the command
demonstrates the full two-hop walk with citations, not a fallback. There is no separate
`stub:scripted` spec wired in on top of it: adding one that played the same `REPLAYED_TRIPLES`
would only reproduce what `--model stub` already shows.
"""
from __future__ import annotations

import sys

from examples.common.cli import parse_args
from examples.common.model import StubModel, StubResponse, build_model
from examples.common.trace import Tracer
from examples.knowledge_graphs.run import LEVEL, run

DEFAULT_QUESTION = "What warranty class covers the model HLV-5520 fits?"

# One canned response per source section, in the order `run` extracts them (parts-list#3, then
# warranty-policy#2), each line transcribed from the section it stands for.
REPLAYED_TRIPLES = (
    (
        "HLV-5510 | fits | DR-210\n"
        "HLV-5520 | fits | DR-520\n"
        "HLV-6601 | fits | DR-210\n"
        "HLV-6601 | fits | DR-520\n"
        "HLV-7735 | fits | DR-520"
    ),
    (
        "DW-300 | warranty_class | 5-year limited (motor and tub), parts only\n"
        "DW-480 | warranty_class | 5-year limited (motor and tub), parts only\n"
        "DR-210 | warranty_class | 7-year limited (drum and motor), parts only\n"
        "DR-520 | warranty_class | 7-year limited (drum and motor), parts only"
    ),
)


def replay_stub() -> StubModel:
    """A `StubModel` that returns `REPLAYED_TRIPLES`, one response per extraction call."""
    return StubModel([StubResponse(text=text) for text in REPLAYED_TRIPLES], model_id="stub-replay")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 2: knowledge graphs, a two-hop answer with its path as provenance.",
        default_question=DEFAULT_QUESTION,
    )
    model = build_model(args.model, stub=replay_stub())
    tracer = Tracer(example="knowledge_graphs", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, None, tracer)
    print(answer.text)
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
