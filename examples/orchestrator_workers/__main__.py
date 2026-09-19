"""Run the lead-agent-and-workers example from the command line.

    python -m examples.orchestrator_workers --model stub:scripted
    python -m examples.orchestrator_workers --model stub --question "What is the DW-300's annual energy use, and how much does the DR-520's drive belt cost?"

`--model stub` asks the lead to split the question, and the echo comes back as one unbroken line,
so the lead's own split always names exactly one sub-question and the demo shows a team of one.
`--model stub:scripted` plays SCRIPTED below: a split into two independent sub-questions, one
worker answer for each, and a combine call that keeps both citations, so the reader sees the team
actually divide the work rather than agree with itself.
"""
from __future__ import annotations

import sys

from examples.common.cli import build_cli_embedder, build_cli_model, parse_args
from examples.common.trace import Tracer
from examples.orchestrator_workers.run import LEVEL, run

DEFAULT_QUESTION = (
    "What is the DW-300's annual energy use, and how much does the DR-520's drive belt cost?"
)

# Four model calls: the lead splits the question into its two independent parts, each of the two
# workers (a level-2 RAG call apiece) answers its own sub-question, and the lead combines both
# answers, keeping each one's citation. The same sequence tests/test_example_orchestrator_workers.py
# scripts for its own end-to-end test.
SCRIPTED = [
    "What is the DW-300's annual energy use?\nWhat does the DR-520's drive belt cost?",
    "260 kWh per year. Sources: dw300-manual#3",
    "$9.75, part HLV-6601. Sources: parts-list#3",
    "The DW-300 uses about 260 kWh per year [dw300-manual#3]. The DR-520's drive belt costs $9.75 "
    "[parts-list#3]. Sources: dw300-manual#3, parts-list#3",
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 6: lead agent and workers, a model-decided split over RAG workers.",
        default_question=DEFAULT_QUESTION,
    )
    model = build_cli_model(args.model, example="orchestrator_workers", script=SCRIPTED)
    embedder = build_cli_embedder(args.embedder, model_spec=args.model)
    tracer = Tracer(example="orchestrator_workers", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, embedder, tracer)
    # The split and the per-worker spawns are the point of this level, and they live in the trace
    # rather than in the final text, so print them before the combined answer.
    for step in tracer.steps:
        if step.title == "Lead splits the task" or step.title.startswith("Spawn worker"):
            print(f"{step.title}: {step.detail}")
    print(answer.text)
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
