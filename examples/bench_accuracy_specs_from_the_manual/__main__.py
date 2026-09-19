"""Run the accuracy-table extraction example from the command line.

    python -m examples.bench_accuracy_specs_from_the_manual --model stub --question "mdn6100-programming-manual#2"

`--question` takes a section id from `evals/bench/corpus/`, not a question; the module docstring
in `run.py` explains why there is only one this recipe ever reads.
"""
from __future__ import annotations

import sys

from examples.bench_accuracy_specs_from_the_manual.run import (
    LEVEL,
    confirm_table,
    price_reading,
    run,
)
from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.common.trace import Tracer


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 3: extract the MDN-6100's DC volts accuracy table from its manual.",
    )
    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="bench_accuracy_specs_from_the_manual", level=LEVEL, model_id=model.model_id)
    result = run(args.question, model, tracer)
    if not result.rows:
        # The interactive stub (--model stub, no --allow-stub script of its own) never answers
        # with a real table, so this is the expected outcome of running the command as printed in
        # the README: code refuses to guess at a missing or malformed row rather than return one.
        print("extraction did not validate; no table for a person to check")
        return 0
    print(f"section        {result.section}")
    print(f"rows extracted {len(result.rows)}")
    table = confirm_table(result, approved=True, tracer=tracer)
    priced = price_reading(table, [4.9930], range_v=10.0, days_since_cal=335.0)
    print(f"interval used  {priced.interval}")
    print(f"range used     {priced.range_v:g} V")
    for c in priced.contributions:
        print(f"  {c.name:<22} {c.standard_uncertainty * 1e6:7.1f} uV  {c.note}")
    print(f"combined       {priced.combined_v * 1e6:.1f} uV")
    print(f"expanded, k=2  {priced.expanded_v * 1e6:.1f} uV")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
