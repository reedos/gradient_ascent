"""Run the inference-time-reasoning example from the command line.

    python -m examples.inference_time_reasoning --model stub:scripted
    python -m examples.inference_time_reasoning --model stub \
        --question "What is the total price to replace the heating elements on both a DW-300 and a DW-480?"

`--model stub` echoes the question back five times, none of which end with an "Answer:" line, so
every sample counts as "no answer" and the vote is unanimous over nothing.
`--model stub:scripted` plays SCRIPTED below: five samples that work the arithmetic differently,
three landing on the right total and two slipping in different directions, so the majority vote
has something real to pick between.
"""
from __future__ import annotations

import sys

from examples.common.cli import build_cli_model, parse_args
from examples.common.trace import Tracer
from examples.inference_time_reasoning.run import LEVEL, N_SAMPLES, run

DEFAULT_QUESTION = "What is the total price to replace the heating elements on both a DW-300 and a DW-480?"

# Five model calls, one per self-consistency sample. The heating elements are $38.50 (DW-300,
# parts-list#2) and $41.00 (DW-480, parts-list#2), so the correct total is $79.50; three samples
# get there and two drift, which is what makes the majority vote worth taking.
SCRIPTED = [
    "Working through it...\nHLV-4471 (DW-300 heating element) is $38.50, and HLV-4472 (DW-480 "
    "heating element) is $41.00. $38.50 + $41.00 = $79.50.\nAnswer: 79.50",
    "Working through it...\n$38.50 + $41.00 = $79.50.\nAnswer: 79.50",
    "Working through it...\nRounding as I go: about $38.50 + $41.00 comes to $79.00.\nAnswer: 79.00",
    "Working through it...\n$38.50 + $41.00 = $79.50.\nAnswer: 79.50",
    "Working through it...\nCarried a digit wrong: $38.50 + $41.00 = $80.50.\nAnswer: 80.50",
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 1: inference-time reasoning, self-consistency by majority vote.",
        default_question=DEFAULT_QUESTION,
    )
    model = build_cli_model(args.model, example="inference_time_reasoning", script=SCRIPTED)
    tracer = Tracer(example="inference_time_reasoning", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, tracer, n=N_SAMPLES)
    # The vote is the whole point of this level, and it lives in the trace: print each sample's
    # final line alongside the tally, not just the winning answer.
    for step in tracer.steps:
        if step.title.startswith("Sample") or step.title in ("Tally the votes", "Return the majority answer"):
            print(f"{step.title}: {step.detail.splitlines()[-1] if step.kind == 'model' else step.detail}")
    print(answer.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
