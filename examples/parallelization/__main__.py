"""Run the parallelization example from the command line.

    python -m examples.parallelization --model stub --question "What is the DW-480's Normal cycle water use, and how often should its filter be cleaned?"
    python -m examples.parallelization --model stub:scripted

`--model stub` echoes the question back from every parallel call, so every section "answers" the
same way and the combine step cannot show what it is for. `--model stub:scripted` plays SCRIPTED
below: one real answer, one real decline, and one real answer, so the combined result reads like
a question two of three sections actually covered.
"""
from __future__ import annotations

import sys

from examples.common.cli import build_cli_model, parse_args
from examples.common.trace import Tracer
from examples.parallelization.run import LEVEL, run

DEFAULT_QUESTION = "What is the DW-480's Normal cycle water use, and how often should its filter be cleaned?"

# Three model calls, one per candidate section retrieved for DEFAULT_QUESTION, in retrieval
# order: care-and-cleaning-guide#1, dw480-manual#3, dw480-manual#6. The calls run in parallel
# threads, but examples/parallelization/run.py's use of concurrent.futures.Executor.map guarantees
# completions[i] is the result of calling section candidates[i] regardless of which thread finishes
# first, so SCRIPTED[i] always lands on the section it was written for.
SCRIPTED = [
    "NOT IN THIS SECTION",
    "The Normal cycle uses 3.0 gallons of water.",
    "The DW-480's filter is self-cleaning and needs no routine cleaning.",
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 3: parallel calls, sectioning.",
        default_question=DEFAULT_QUESTION,
    )
    model = build_cli_model(args.model, example="parallelization", script=SCRIPTED)
    tracer = Tracer(example="parallelization", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, None, tracer)
    # Each branch answered alone, with no view of the others; print every branch's own result
    # before the merged answer, or a reader cannot tell one branch ran from three.
    for step in tracer.steps:
        if step.title.startswith("Answer from") or step.title == "Combine the sections that answered":
            print(f"{step.title}: {step.detail}")
    print(answer.text)
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
