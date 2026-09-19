"""Level 0: no model. Read the characterization sweep, find the corner where each of five
prototype boards holds the least margin to the datasheet's output-voltage window, price one of
those readings with an uncertainty budget built from the meter's own accuracy specification, and
guardband every board's line regulation against its limit at every ambient this sweep visited.

Four things this module computes, all of it arithmetic:

- **A margin.** `window_margin` is a subtraction (`margin_to_limit`, twice, keep the smaller).
  `worst_corner_per_board` is that subtraction over every corner this sweep visited, kept once per
  board: nothing here is told in advance which of the 36 corners in a board's own sweep is the
  worst one, or that all five boards turn out to share it.
- **An uncertainty budget.** `budget_for_point` calls `dc_voltage_budget`, `combined_uncertainty`
  and `expanded_uncertainty` from `examples.common.bench`, the same functions every figure in
  `evals/bench/corpus/mdn6100-programming-manual.md` is checked against in `tests/test_bench.py`.
  Nothing here assembles a budget by hand.
- **A guardbanded verdict.** `guarded_verdict` returns pass, fail or `cannot say`, and
  `scan_line_regulation` calls it for every board at every ambient rather than only the one case
  `docs/THE-BENCH.md` happens to name, so a `cannot say` here is something this module found, not
  something it was told to expect.
- **A repeatability problem that belongs to the meter, not the board.** `spread_by_meter_range`
  groups the sweep's own point-to-point spread by the `meter_range_v` column every row already
  carries. `range_cost` prices the same five readings on the range they were actually taken on and
  on the range the rest of the sweep used, which is the other half of that story: the scatter is
  the visible symptom, and the specification's own number is the rest of it.

Nothing here reads a model's opinion of any of it. A margin, a budget and a verdict are code's job
on this bench in every setting, and design verification is no exception: a margin nobody can
reproduce is worse than no margin, and an uncertainty a model assembled looks exactly like one a
budget produced.

The data is read, not regenerated: `from evals.bench import CHARACTERIZATION_CSV`, the file
`evals/bench/make_characterization.py` wrote and `tests/test_bench_characterization.py` proves
reproduces byte for byte. `docs/THE-BENCH.md` and `evals/bench/corpus/characterization-notebook.md`
are the answer key this module's own numbers are checked against.
"""
from __future__ import annotations

import csv
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from evals.bench import CHARACTERIZATION_CSV
from examples.common.bench import (
    VERDICT_PASS,
    VOUT_NOM_V,
    Contribution,
    combined_uncertainty,
    dc_voltage_budget,
    expanded_uncertainty,
    guarded_verdict,
    margin_to_limit,
)
from examples.common.model import Model
from examples.common.trace import Tracer

LEVEL = 0

#: srb5030-datasheet.md section 4: "Output voltage | full line, load and temperature range |
#: 4.900 | 5.000 | 5.100 | V". This is the window this recipe holds every corner against, not the
#: tighter 4.9500-5.0500 V window production tests at one fixed condition (VOUT, srb5030-test-
#: spec.md step 3): a characterization sweep visits the corners that window is meant to survive.
VOUT_MIN_V = 4.900
VOUT_MAX_V = 5.100

#: srb5030-test-spec.md step 4: line regulation, 9.0 V to 32.0 V at 1.000 A, reported as a
#: percentage of the 5.000 V nominal output. 32.0 V and not the datasheet's 36.0 V, because
#: ECN-2608-04 caps the boards this sweep's own revision C prototypes are being compared against;
#: characterization-notebook.md section 1 records swimming the same 32.0 V ceiling on purpose.
LINE_REG_MAX_PCT = 0.300

#: characterization-notebook.md section 2: "Meter: DC volts, 10 V range, selected once per board
#: rather than per reading." The range the sweep script chose, and the range every point in this
#: file should have been read on.
NOMINAL_RANGE_V = 10.0


@dataclass(frozen=True)
class Reading:
    """One row of the characterization sweep: which board, at what condition, and what the meter
    read, on the range it actually read it on."""

    serial: str
    tamb_c: float
    vin_v: float
    iout_a: float
    meter_range_v: float
    vout_v: float


@dataclass(frozen=True)
class CornerMargin:
    """One board's worst corner: the input voltage, load current and ambient where its output
    voltage sits closest to the datasheet's window, and how close."""

    serial: str
    tamb_c: float
    vin_v: float
    iout_a: float
    mean_v: float
    margin_v: float
    side: str  # "lower" | "upper": which edge of the window the margin is measured against


@dataclass(frozen=True)
class UncertaintyBudget:
    """One reading's uncertainty budget: the named contributions, combined by root sum of
    squares, expanded at k=2."""

    contributions: tuple[Contribution, ...]
    combined_v: float
    expanded_v: float


@dataclass(frozen=True)
class RegulationCheck:
    """One board's line regulation at one ambient, guardbanded against its limit."""

    serial: str
    tamb_c: float
    value_pct: float
    uncertainty_pct: float
    verdict: str


@dataclass(frozen=True)
class RangeSpread:
    """The output voltage's point-to-point spread, for every point read on one meter range."""

    range_v: float
    n_points: int
    mean_stdev_v: float
    boards: frozenset[str]


@dataclass(frozen=True)
class Report:
    n_readings: int
    corners: list[CornerMargin]  # one per board, worst margin first
    thin_margin: CornerMargin  # corners[0]
    budget: UncertaintyBudget  # for thin_margin's own reading
    thin_verdict: str
    line_regulation: list[RegulationCheck]  # every board, every ambient this sweep visited
    focus_serial: str
    spread_by_range: list[RangeSpread]
    range_cost_ratio: float | None  # None only if this sweep used a single meter range throughout


Points = dict[tuple[str, float, float, float], list[Reading]]


def load_readings(csv_path: Path) -> list[Reading]:
    """Every row of the sweep. `iin_a`, `revision` and `reading_n` are in the file and are not
    read here: they are `test-data-by-conversation`'s and `docs/THE-BENCH.md` story D's, the point
    recorded at a condition it was not taken at, which this page does not go looking for."""
    readings: list[Reading] = []
    with csv_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            readings.append(
                Reading(
                    serial=row["serial"],
                    tamb_c=float(row["tamb_c"]),
                    vin_v=float(row["vin_v"]),
                    iout_a=float(row["iout_a"]),
                    meter_range_v=float(row["meter_range_v"]),
                    vout_v=float(row["vout_v"]),
                )
            )
    return readings


def by_point(readings: list[Reading]) -> Points:
    """`GROUP BY` serial, ambient, input voltage and load current: one entry per corner this sweep
    visited, each holding the five readings taken there."""
    points: Points = defaultdict(list)
    for r in readings:
        points[(r.serial, r.tamb_c, r.vin_v, r.iout_a)].append(r)
    return points


def window_margin(value_v: float) -> tuple[float, str]:
    """Margin to the nearer edge of the datasheet's output-voltage window, and which edge. The
    same two-sided convention `cpk` in `examples/bench_limits_without_a_model/run.py` uses for a
    bounded limit: the smaller of the two one-sided margins, because that is the one a board can
    actually run into."""
    lower = margin_to_limit(value_v, VOUT_MIN_V, side="lower")
    upper = margin_to_limit(value_v, VOUT_MAX_V, side="upper")
    return (lower, "lower") if lower <= upper else (upper, "upper")


def worst_corner_per_board(points: Points) -> list[CornerMargin]:
    """One `CornerMargin` per board: the corner, of every one this sweep visited, where the
    margin to the datasheet's window is smallest. `points` already holds every corner; this keeps
    the minimum per serial and says nothing about which corner that will turn out to be.
    Sorted worst first, so `corners[0]` is the board this sweep should worry about."""
    best: dict[str, CornerMargin] = {}
    for (serial, tamb_c, vin_v, iout_a), readings in points.items():
        mean_v = statistics.fmean(r.vout_v for r in readings)
        margin_v, side = window_margin(mean_v)
        candidate = CornerMargin(serial, tamb_c, vin_v, iout_a, mean_v, margin_v, side)
        if serial not in best or candidate.margin_v < best[serial].margin_v:
            best[serial] = candidate
    return sorted(best.values(), key=lambda c: c.margin_v)


def budget_for_point(readings: list[Reading], *, range_v: float) -> UncertaintyBudget:
    """The uncertainty budget behind one output-voltage reading, at the range it was actually
    read on: meter accuracy, the display's resolution, the repeatability of these five readings,
    and the lead and connection contribution `characterization-notebook.md` section 6 carries over
    from `calibration-procedure.md`. `dc_voltage_budget` is the one function every engineering page
    on this bench imports for this; nothing here writes a second root sum of squares."""
    values = [r.vout_v for r in readings]
    contributions = dc_voltage_budget(values, range_v=range_v)
    combined_v = combined_uncertainty(contributions)
    return UncertaintyBudget(
        contributions=contributions, combined_v=combined_v, expanded_v=expanded_uncertainty(combined_v)
    )


def line_regulation_pct(points: Points, serial: str, tamb_c: float) -> float:
    """`(VOUT at 32.0 V - VOUT at 9.0 V) / 5.000`, as a percentage, at 1.000 A: srb5030-test-
    spec.md step 4's own definition, not this module's."""
    high = statistics.fmean(r.vout_v for r in points[(serial, tamb_c, 32.0, 1.000)])
    low = statistics.fmean(r.vout_v for r in points[(serial, tamb_c, 9.0, 1.000)])
    return 100.0 * (high - low) / VOUT_NOM_V


def regulation_uncertainty_pct(readings: list[Reading], *, range_v: float) -> float:
    """The uncertainty on a regulation figure, not on one reading. Line regulation is a difference
    of two readings taken through the same leads, so the lead-and-connection line cancels
    (`lead_half_width_v=None`), and what is left of each reading combines in quadrature: `sqrt(2)`
    times one reading's own meter-and-resolution-and-repeatability uncertainty, expanded at k=2,
    stated as a percentage of the nominal output. `characterization-notebook.md` section 6 derives
    this by hand for one board; this is the general function behind that arithmetic."""
    values = [r.vout_v for r in readings]
    per_reading = combined_uncertainty(dc_voltage_budget(values, range_v=range_v, lead_half_width_v=None))
    return 100.0 * expanded_uncertainty(per_reading * math.sqrt(2.0)) / VOUT_NOM_V


def scan_line_regulation(points: Points) -> list[RegulationCheck]:
    """Line regulation, guardbanded, for every board at every ambient this sweep visited, not only
    the one board and one ambient `docs/THE-BENCH.md` happens to name. A verdict that is not a
    clean pass is a finding this scan makes, not one it was handed."""
    ambients = sorted({tamb for (_, tamb, _, _) in points})
    serials = sorted({serial for (serial, _, _, _) in points})
    checks = []
    for serial in serials:
        for tamb_c in ambients:
            value_pct = line_regulation_pct(points, serial, tamb_c)
            high_readings = points[(serial, tamb_c, 32.0, 1.000)]
            uncertainty_pct = regulation_uncertainty_pct(high_readings, range_v=NOMINAL_RANGE_V)
            verdict = guarded_verdict(value_pct, uncertainty_pct, upper=LINE_REG_MAX_PCT)
            checks.append(RegulationCheck(serial, tamb_c, value_pct, uncertainty_pct, verdict))
    return checks


def spread_by_meter_range(points: Points) -> list[RangeSpread]:
    """The output voltage's point-to-point spread, grouped by the meter range each point was
    actually read on, not by board and not by corner. Every point in this file was read entirely
    on one range (the sweep script picks a range once per board; characterization-notebook.md
    section 3 records the one exception), so this is one `GROUP BY` on a column the file already
    carries. Sorted by how many points used that range, most first."""
    spreads_by_range: dict[float, list[float]] = defaultdict(list)
    boards_by_range: dict[float, set[str]] = defaultdict(set)
    for (serial, _tamb_c, _vin_v, _iout_a), readings in points.items():
        ranges_here = {r.meter_range_v for r in readings}
        if len(ranges_here) != 1:
            raise ValueError("a point spans more than one meter range")
        range_v = ranges_here.pop()
        spreads_by_range[range_v].append(statistics.stdev(r.vout_v for r in readings))
        boards_by_range[range_v].add(serial)
    return sorted(
        (
            RangeSpread(
                range_v=range_v,
                n_points=len(spreads),
                mean_stdev_v=statistics.fmean(spreads),
                boards=frozenset(boards_by_range[range_v]),
            )
            for range_v, spreads in spreads_by_range.items()
        ),
        key=lambda s: -s.n_points,
    )


def range_cost(points: Points, minority_range_v: float, majority_range_v: float) -> float:
    """How much worse a reading taken on `minority_range_v` really is, priced against the same
    five readings on `majority_range_v` instead. The spread in `spread_by_meter_range` is the
    visible half of this story; this is the specification's own number for the other half."""
    sample = next(
        readings for readings in points.values() if readings and readings[0].meter_range_v == minority_range_v
    )
    values = [r.vout_v for r in sample]
    wrong = expanded_uncertainty(combined_uncertainty(dc_voltage_budget(values, range_v=minority_range_v)))
    right = expanded_uncertainty(combined_uncertainty(dc_voltage_budget(values, range_v=majority_range_v)))
    return wrong / right


def run(
    serial: str,
    model: Model | None,
    tracer: Tracer,
    *,
    csv_path: Path = CHARACTERIZATION_CSV,
) -> Report:
    """Read the sweep, find each board's worst corner, price one of those readings, guardband
    every board's line regulation, and group the spread by the meter range it was read on.
    `model` is accepted only to fit the shared `(text, model, tracer)` convention every recordable
    example in this repo follows; level 0 calls no model, so it is never used.

    `serial` selects which board's line-regulation figures the returned report highlights
    (`Report.focus_serial`); the corner and spread findings below cover all five boards regardless.
    A `serial` this sweep does not recognize falls back to the board `worst_corner_per_board` finds
    to hold the least margin, discovered from this run's own arithmetic rather than a name typed in
    advance, so a caller that does not know a board's serial (`scripts/record_trace.py`'s generic
    driver, exercising every recordable example with one placeholder question) still gets the one
    board this report has most to say about."""
    del model
    readings = load_readings(csv_path)
    tracer.record(
        kind="code", decided_by="code", title="Load the sweep",
        detail=f"{len(readings)} readings from {csv_path.name}",
    )
    points = by_point(readings)

    corners = worst_corner_per_board(points)
    thin = corners[0]
    tracer.record(
        kind="code", decided_by="code", title="Sweep every corner, keep the worst one per board",
        detail=(
            f"{len(corners)} boards, {len(points)} corners each; the thinnest margin is "
            f"{thin.serial} at tamb={thin.tamb_c:g} vin={thin.vin_v:g} iout={thin.iout_a:g}, "
            f"{thin.margin_v * 1000.0:.1f} mV to the {thin.side} edge of the window"
        ),
    )

    valid_serials = {c.serial for c in corners}
    normalized = serial.strip().upper()
    if normalized not in valid_serials:
        tracer.record(
            kind="code", decided_by="code", title="Unrecognized serial, focusing on the thinnest margin",
            detail=f"{serial!r} is not one of this sweep's boards; using {thin.serial}",
        )
        normalized = thin.serial
    focus_serial = normalized

    budget = budget_for_point(points[(thin.serial, thin.tamb_c, thin.vin_v, thin.iout_a)], range_v=NOMINAL_RANGE_V)
    tracer.record(
        kind="code", decided_by="code", title="Uncertainty budget for that corner's output voltage",
        detail=(
            f"{len(budget.contributions)} contributions, combined {budget.combined_v * 1e6:.1f} uV, "
            f"expanded k=2 {budget.expanded_v * 1e6:.1f} uV"
        ),
    )

    thin_verdict = guarded_verdict(thin.mean_v, budget.expanded_v, lower=VOUT_MIN_V, upper=VOUT_MAX_V)
    tracer.record(
        kind="code", decided_by="code", title="Guardband the worst corner against the datasheet window",
        detail=f"{thin.mean_v:.5f} V against {VOUT_MIN_V} to {VOUT_MAX_V} V: {thin_verdict}",
    )

    reg_checks = scan_line_regulation(points)
    not_pass = [c for c in reg_checks if c.verdict != VERDICT_PASS]
    tracer.record(
        kind="code", decided_by="code", title="Guardband line regulation, every board, every ambient",
        detail=(
            f"{len(reg_checks)} checks, {len(not_pass)} not a clean pass: "
            + ", ".join(f"{c.serial}@{c.tamb_c:g}degC={c.verdict}" for c in not_pass)
            if not_pass
            else f"{len(reg_checks)} checks, all pass"
        ),
    )

    spreads = spread_by_meter_range(points)
    tracer.record(
        kind="code", decided_by="code", title="Group the output voltage's spread by meter range",
        detail="; ".join(
            f"{s.range_v:g} V range: {s.n_points} points, mean spread {s.mean_stdev_v * 1e6:.1f} uV, "
            f"{len(s.boards)} board(s)"
            for s in spreads
        ),
    )

    cost: float | None = None
    if len(spreads) > 1:
        majority, minority = spreads[0], spreads[-1]
        cost = range_cost(points, minority.range_v, majority.range_v)
        tracer.record(
            kind="code", decided_by="code", title="Price the slipped-range readings on the range they should have been on",
            detail=(
                f"{minority.range_v:g} V range priced against {majority.range_v:g} V: "
                f"{cost:.2f}x the expanded uncertainty"
            ),
        )

    return Report(
        n_readings=len(readings),
        corners=corners,
        thin_margin=thin,
        budget=budget,
        thin_verdict=thin_verdict,
        line_regulation=reg_checks,
        focus_serial=focus_serial,
        spread_by_range=spreads,
        range_cost_ratio=cost,
    )
