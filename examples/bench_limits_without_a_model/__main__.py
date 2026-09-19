"""Run the limits-without-a-model example from the command line.

    python -m examples.bench_limits_without_a_model --measurement RIPPLE
    python -m examples.bench_limits_without_a_model --measurement VOUT

`--measurement` is any name in the `measurement` column of
`evals/bench/data/production-run-2026-08.csv` (`R_OUT`, `IQ_NL`, `VOUT`, `LINE_REG`, `LOAD_REG`,
`EFF_FL`, `RIPPLE`, `I_LIM`); it defaults to `RIPPLE`.

`--model` is accepted and otherwise unused: level 0 calls no model, so `run()`'s `model`
parameter (kept only to fit the shared `(text, model, tracer)` convention every recordable
example follows) is always passed `None` here, whatever `--model` names. The flag exists so this
command runs the same way every other example's does; there is no `--model stub:scripted` for
this example, because there is no model call for a scripted reply to stand in for.
"""
from __future__ import annotations

import argparse
import sys

from examples.common.cli import MODEL_HELP
from examples.common.trace import Tracer
from examples.bench_limits_without_a_model.run import LEVEL, GroupStats, GroupYield, Report, run


def _print_group(title: str, rows: list[GroupStats]) -> None:
    print(f"\n{title}")
    print(f"{'':<10}{'n':>5}{'mean':>10}{'sd':>10}{'cpk':>8}{'yield%':>9}")
    for g in rows:
        cpk = f"{g.cpk:.2f}" if g.cpk is not None else "n/a"
        sd = f"{g.sd:.4f}" if g.sd is not None else "n/a"
        print(f"{g.key:<10}{g.n:>5}{g.mean:>10.4f}{sd:>10}{cpk:>8}{g.yield_pct:>8.1f}%")


def _print_yield(title: str, rows: list[GroupYield]) -> None:
    print(f"\n{title}")
    for g in rows:
        print(f"{g.key:<10} n={g.n:<4} failed={g.failed:<3} yield={g.yield_pct:.1f}%")


def _print_report(report: Report) -> None:
    lim = f"{report.lower} to {report.upper} {report.unit}" if report.lower and report.upper else (
        f"<= {report.upper} {report.unit}" if report.upper is not None else f">= {report.lower} {report.unit}"
    )
    print(f"{report.measurement}: {report.n} readings, limit {lim}")
    print(f"mean={report.mean:.4f} sd={report.sd:.4f} cpk={report.cpk:.2f}" if report.cpk is not None else "")
    _print_group("by lot", report.by_lot)
    _print_group("by fixture", report.by_fixture)
    _print_group("by day", report.by_day)
    _print_group("by shift", report.by_shift)
    c = report.chart
    print(f"\ncontrol chart: center={c.center:.2f} UCL={c.ucl:.2f} LCL={c.lcl:.2f}")
    print(f"{c.out_of_control} of {report.n} points beyond the control limits")
    print(f"\nfirst-pass yield, whole unit: {report.overall_yield_pct:.1f}%")
    _print_yield("yield by lot", report.yield_by_lot)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Level 0: check a measurement against its limits, yield, Cpk, a control chart, grouped four ways."
    )
    parser.add_argument(
        "--measurement", default="RIPPLE",
        help="R_OUT | IQ_NL | VOUT | LINE_REG | LOAD_REG | EFF_FL | RIPPLE | I_LIM (default RIPPLE)",
    )
    parser.add_argument(
        "--model", default="stub",
        help=f"{MODEL_HELP}; accepted for consistency with every other example's command, never used: level 0 calls no model",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    tracer = Tracer(example="bench_limits_without_a_model", level=LEVEL, model_id="none")
    report = run(args.measurement, None, tracer)
    _print_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
