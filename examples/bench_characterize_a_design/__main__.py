"""Run the characterize-a-design example from the command line.

    python -m examples.bench_characterize_a_design --serial SRB5030-2609-0003
    python -m examples.bench_characterize_a_design --serial SRB5030-2609-0005

`--serial` is any of the five boards in `evals/bench/data/characterization-2026-09.csv`
(SRB5030-2609-0001 through -0005); it defaults to the empty string, which `run()` treats as
unrecognized and falls back to whichever board its own corner scan finds to hold the least
margin. There is no `--model` flag: level 0 calls no model, so `run()`'s `model` parameter (kept
only to fit the shared `(text, model, tracer)` convention every recordable example follows) is
always passed `None` here.
"""
from __future__ import annotations

import argparse
import sys

from examples.common.trace import Tracer
from examples.bench_characterize_a_design.run import LEVEL, Report, run


def _print_report(report: Report) -> None:
    print(f"{report.n_readings} readings, {len(report.corners)} boards\n")

    print("Worst corner per board (margin to the datasheet's 4.900-5.100 V window):")
    for c in report.corners:
        print(
            f"  {c.serial:<20} tamb={c.tamb_c:>5.1f}  vin={c.vin_v:>5.1f}  iout={c.iout_a:>5.3f}  "
            f"{c.mean_v:.5f} V  margin={c.margin_v * 1000.0:>6.1f} mV ({c.side})"
        )

    thin = report.thin_margin
    print(f"\nThinnest margin: {thin.serial}, {thin.margin_v * 1000.0:.1f} mV, verdict {report.thin_verdict}")
    print("Uncertainty budget for that reading:")
    for contribution in report.budget.contributions:
        print(f"  {contribution.name:<20} {contribution.standard_uncertainty * 1e6:>8.1f} uV  {contribution.note}")
    print(f"  {'combined':<20} {report.budget.combined_v * 1e6:>8.1f} uV")
    print(f"  {'expanded, k=2':<20} {report.budget.expanded_v * 1e6:>8.1f} uV")

    print(f"\nLine regulation, focused on {report.focus_serial}:")
    for c in report.line_regulation:
        if c.serial != report.focus_serial:
            continue
        print(f"  tamb={c.tamb_c:>5.1f}  {c.value_pct:.4f}%  +/-{c.uncertainty_pct:.4f}%  {c.verdict}")
    not_pass = [c for c in report.line_regulation if c.verdict != "pass"]
    if not_pass:
        print("Not a clean pass, anywhere in the sweep:")
        for c in not_pass:
            print(f"  {c.serial}  tamb={c.tamb_c:>5.1f}  {c.value_pct:.4f}%  {c.verdict}")

    print("\nOutput voltage spread, by meter range:")
    for s in report.spread_by_range:
        print(f"  {s.range_v:>6.1f} V range  {s.n_points:>3} points  mean spread {s.mean_stdev_v * 1e6:>6.1f} uV  {len(s.boards)} board(s)")
    if report.range_cost_ratio is not None:
        print(f"Priced on the wrong range: {report.range_cost_ratio:.2f}x the expanded uncertainty of the right one.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Level 0: margin at every corner, an uncertainty budget, a guardbanded verdict, and the range story."
    )
    parser.add_argument(
        "--serial", default="",
        help="SRB5030-2609-0001 through -0005 (default: whichever board holds the least margin)",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    tracer = Tracer(example="bench_characterize_a_design", level=LEVEL, model_id="none")
    report = run(args.serial, None, tracer)
    _print_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
