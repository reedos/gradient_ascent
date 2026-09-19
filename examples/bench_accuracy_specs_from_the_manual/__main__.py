"""Run the accuracy-table extraction example from the command line.

    python -m examples.bench_accuracy_specs_from_the_manual --model stub:scripted
    python -m examples.bench_accuracy_specs_from_the_manual --model stub --question "mdn6100-programming-manual#2"

`--question` takes a section id from `evals/bench/corpus/`, not a question; the module docstring
in `run.py` explains why there is only one this recipe ever reads.

`--model stub` never returns a table that validates, so the command prints the "nothing for a
person to check" outcome and nothing else. `--model stub:scripted` plays SCRIPTED below: the
retry the module docstring describes, with a real validation failure and a real recovery, so the
reader sees the loop `run.py` is written for.
"""
from __future__ import annotations

import json
import sys

from examples.bench_accuracy_specs_from_the_manual.run import (
    INTERVALS,
    LEVEL,
    RANGES_V,
    SAMPLE_INPUT,
    confirm_table,
    price_reading,
    run,
)
from examples.common.bench import MDN6100_DC_ACCURACY
from examples.common.cli import build_cli_model, parse_args
from examples.common.trace import Tracer


def _row(interval: str, range_value: float) -> dict:
    """One row of the manual's real table, as the schema in `run.py` wants it. Building this from
    `examples.common.bench.MDN6100_DC_ACCURACY` instead of retyping the numbers means the scripted
    reply cannot drift from the table `tests/test_bench.py` already checks against the manual."""
    spec = MDN6100_DC_ACCURACY[interval][range_value]
    return {
        "range_value": spec.range_value,
        "interval": spec.interval,
        "ppm_of_reading": spec.ppm_of_reading,
        "ppm_of_range": spec.ppm_of_range,
        "tempco_ppm_of_reading_per_c": spec.tempco_ppm_of_reading_per_c,
        "tempco_ppm_of_range_per_c": spec.tempco_ppm_of_range_per_c,
    }


#: The manual's real 15 rows, one per range per interval, in the order `run.py`'s own schema
#: expects them.
_ALL_ROWS = [_row(interval, range_value) for interval in INTERVALS for range_value in RANGES_V]

#: The same 15 rows with the last one left out: a plausible slip reading a long table, not a
#: malformed reply. This is what `_validate_table` reports as a missing row.
_MISSING_LAST_ROW = [
    row for row in _ALL_ROWS if not (row["interval"] == "1 year" and row["range_value"] == 1000.0)
]

# Two model calls: a first extraction that leaves the 1000 V, 1 year row out, which
# `_validate_table` reports as missing and `run` sends back for one retry, and a second
# extraction with all 15 rows, which validates. The same sequence
# tests/test_example_bench_accuracy_specs_from_the_manual.py scripts for its own end-to-end test.
SCRIPTED = [
    json.dumps(_MISSING_LAST_ROW),
    json.dumps(_ALL_ROWS),
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 3: extract the MDN-6100's DC volts accuracy table from its manual.",
        default_question=SAMPLE_INPUT,
    )
    model = build_cli_model(args.model, example="bench_accuracy_specs_from_the_manual", script=SCRIPTED)
    tracer = Tracer(example="bench_accuracy_specs_from_the_manual", level=LEVEL, model_id=model.model_id)
    result = run(args.question, model, tracer)
    # The retry itself lives in the trace, not in the final table, so print it before the result.
    for step in tracer.steps:
        if step.title.startswith("Extract") or step.title.startswith("Validate"):
            print(f"{step.title}: {step.detail}")
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
