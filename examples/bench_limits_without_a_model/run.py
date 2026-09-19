"""Level 0: no model. Read the production log, check each row against its own limits, count
first-pass yield, compute Cpk, run an individuals control chart, and group all of it by lot, by
fixture, by day and by shift.

Every one of those is arithmetic a test engineer already has the numbers for:

- A limit check is two comparisons (`value < lower`, `value > upper`).
- First-pass yield is a count: units with no failing row, over units attempted.
- Cpk is a mean, a standard deviation and a subtraction. `cpk` below uses the standard one-sided
  form against whichever single limit a step has, and the standard two-sided form (the smaller of
  the two one-sided numbers) against a step with both. It is the same formula
  `tests/test_bench_data.py` uses to check the bench data itself.
- A control chart is a mean, a standard deviation and a plot: `control_chart` below is a
  Shewhart individuals (I) chart, whose control limits come from the average moving range
  between consecutive readings, not from the sample standard deviation and not from the spec
  limits. That is deliberate: a control limit says the process just moved, a spec limit says a
  unit is out of tolerance, and the two numbers answer different questions.
- `GROUP BY` is `group_stats` and `yield_by`, called once each for lot, fixture, day and shift.

Nothing here reads a model's opinion of any of it, and the pass or fail decision in
`within_limits` never will: a wrong pass ships a bad unit, and a model that is right 99 times in
100 is a one percent defect rate added to a line that measures its own defect rate in parts per
million.

The data is read, not regenerated: `from evals.bench import PRODUCTION_CSV`, the file
`evals/bench/make_data.py` wrote and `tests/test_bench_data.py` proves reproduces byte for byte.
`docs/THE-BENCH.md` is the answer key this module's own numbers are checked against.
"""
from __future__ import annotations

import csv
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from evals.bench import PRODUCTION_CSV
from examples.common.model import Model
from examples.common.trace import Tracer

LEVEL = 0

#: The individuals-chart constant for a moving range of two consecutive readings (n=2): the
#: standard Shewhart table value, not tuned to this data. `sigma = mean_moving_range / D2`.
D2_MOVING_RANGE_N2 = 1.128

#: The eight step names `evals/bench/corpus/srb5030-test-spec.md` and the production log's own
#: `measurement` column use, in test order. `DEFAULT_MEASUREMENT` is what `run()` falls back to
#: for anything else: a fixed, code-decided default, the same shape as routing's own "unclear"
#: fallback, not a guess about what the caller meant.
MEASUREMENTS = ("R_OUT", "IQ_NL", "VOUT", "LINE_REG", "LOAD_REG", "EFF_FL", "RIPPLE", "I_LIM")
DEFAULT_MEASUREMENT = "RIPPLE"


@dataclass(frozen=True)
class Reading:
    """One row of the production log for one measurement: who took it, where, and whether it
    cleared its own two limits. `passed` is recomputed here from `value`, `lower` and `upper`;
    the log's own `result` column is read only by the tests, to prove the two agree."""

    serial: str
    lot: str
    fixture: str
    shift: str
    day: str
    value: float
    unit: str
    lower: float | None
    upper: float | None
    passed: bool


@dataclass(frozen=True)
class GroupStats:
    """Mean, spread, capability and yield for one measurement, within one group (one lot, one
    fixture, one day or one shift)."""

    key: str
    n: int
    mean: float
    sd: float | None
    cpk: float | None
    yield_pct: float


@dataclass(frozen=True)
class GroupYield:
    """Whole-unit first-pass yield for one group: did the unit clear every step it reached, not
    just the one measurement `GroupStats` is about."""

    key: str
    n: int
    failed: int
    yield_pct: float


@dataclass(frozen=True)
class ControlChart:
    """A Shewhart individuals chart over one measurement, in the order the log recorded it."""

    center: float
    sigma: float
    ucl: float
    lcl: float
    flagged: list[Reading] = field(default_factory=list)

    @property
    def out_of_control(self) -> int:
        return len(self.flagged)


@dataclass(frozen=True)
class Report:
    measurement: str
    unit: str
    lower: float | None
    upper: float | None
    n: int
    mean: float
    sd: float
    cpk: float | None
    by_lot: list[GroupStats]
    by_fixture: list[GroupStats]
    by_day: list[GroupStats]
    by_shift: list[GroupStats]
    chart: ControlChart
    overall_yield_pct: float
    yield_by_lot: list[GroupYield]


def within_limits(value: float, lower: float | None, upper: float | None) -> bool:
    """The whole pass or fail decision: two comparisons, no judgment, nothing a model could get
    right 99 times out of 100 and wrong the hundredth."""
    if lower is not None and value < lower:
        return False
    if upper is not None and value > upper:
        return False
    return True


def cpk(values: list[float], lower: float | None, upper: float | None) -> float | None:
    """The standard capability index. One-sided against whichever single limit exists
    (`(USL - mean) / (3 * sigma)` or `(mean - LSL) / (3 * sigma)`); the smaller of the two
    one-sided numbers when both limits exist, which is the standard two-sided Cpk. `None` when
    there is no limit to be capable against, or fewer than two readings to take a spread from."""
    if len(values) < 2 or (lower is None and upper is None):
        return None
    mean = statistics.fmean(values)
    sd = statistics.stdev(values)
    if sd == 0.0:
        return None
    candidates = []
    if upper is not None:
        candidates.append((upper - mean) / (3.0 * sd))
    if lower is not None:
        candidates.append((mean - lower) / (3.0 * sd))
    return min(candidates)


def _to_float(text: str) -> float | None:
    return float(text) if text else None


def load_readings(csv_path: Path, measurement: str) -> list[Reading]:
    """Every row for one measurement, in the order the log recorded them: production order, the
    same order a control chart needs. The pass/fail verdict is recomputed by `within_limits`
    rather than trusted from the log's own `result` column."""
    readings: list[Reading] = []
    with csv_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["measurement"] != measurement:
                continue
            lower = _to_float(row["lower_limit"])
            upper = _to_float(row["upper_limit"])
            value = float(row["value"])
            readings.append(
                Reading(
                    serial=row["serial"],
                    lot=row["lot"],
                    fixture=row["fixture"],
                    shift=row["shift"],
                    day=row["timestamp"][:10],
                    value=value,
                    unit=row["unit"],
                    lower=lower,
                    upper=upper,
                    passed=within_limits(value, lower, upper),
                )
            )
    return readings


def group_stats(readings: list[Reading], key: Callable[[Reading], str]) -> list[GroupStats]:
    """`GROUP BY key`, then mean, standard deviation, Cpk and yield within each group."""
    groups: dict[str, list[Reading]] = defaultdict(list)
    for r in readings:
        groups[key(r)].append(r)
    out = []
    for name in sorted(groups):
        rows = groups[name]
        values = [r.value for r in rows]
        failed = sum(1 for r in rows if not r.passed)
        out.append(
            GroupStats(
                key=name,
                n=len(rows),
                mean=statistics.fmean(values),
                sd=statistics.stdev(values) if len(values) > 1 else None,
                cpk=cpk(values, rows[0].lower, rows[0].upper),
                yield_pct=100.0 * (len(rows) - failed) / len(rows),
            )
        )
    return out


def control_chart(readings: list[Reading]) -> ControlChart:
    """A Shewhart individuals chart: center line is the mean, sigma is estimated from the
    average moving range between consecutive readings (`mRbar / 1.128`), not from the sample
    standard deviation. A sample standard deviation over a run that includes a shifted subgroup
    is inflated by the shift itself; the moving-range estimate is not, which is why it is the
    textbook choice for an individuals chart and not an arbitrary alternative to `statistics.
    stdev`. Points beyond the resulting control limits are flagged without being told which lot,
    fixture, day or shift they belong to -- that grouping is `group_stats`' job, not this one's."""
    values = [r.value for r in readings]
    if len(values) < 2:
        mean = values[0] if values else 0.0
        return ControlChart(center=mean, sigma=0.0, ucl=mean, lcl=mean)
    moving_ranges = [abs(values[i] - values[i - 1]) for i in range(1, len(values))]
    mr_bar = statistics.fmean(moving_ranges)
    sigma = mr_bar / D2_MOVING_RANGE_N2
    mean = statistics.fmean(values)
    ucl = mean + 3.0 * sigma
    lcl = max(0.0, mean - 3.0 * sigma)
    flagged = [r for r in readings if r.value > ucl or r.value < lcl]
    return ControlChart(center=mean, sigma=sigma, ucl=ucl, lcl=lcl, flagged=flagged)


@dataclass(frozen=True)
class _Unit:
    serial: str
    lot: str
    passed: bool  # every row this serial reached cleared its own limits


def _load_units(csv_path: Path) -> list[_Unit]:
    """One entry per serial, from every row in the log, not just one measurement: whether it
    cleared every step it reached. A unit that failed step 1 (a short) never reached step 2 and
    is judged on the one row it has, the same partial record a real yield report reads."""
    by_serial: dict[str, list[dict]] = defaultdict(list)
    with csv_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            by_serial[row["serial"]].append(row)
    units = []
    for serial, rows in by_serial.items():
        passed = all(
            within_limits(float(r["value"]), _to_float(r["lower_limit"]), _to_float(r["upper_limit"]))
            for r in rows
        )
        units.append(_Unit(serial=serial, lot=rows[0]["lot"], passed=passed))
    return units


def yield_by(units: list[_Unit], key: Callable[["_Unit"], str]) -> list[GroupYield]:
    groups: dict[str, list[_Unit]] = defaultdict(list)
    for u in units:
        groups[key(u)].append(u)
    out = []
    for name in sorted(groups):
        us = groups[name]
        failed = sum(1 for u in us if not u.passed)
        out.append(GroupYield(key=name, n=len(us), failed=failed, yield_pct=100.0 * (len(us) - failed) / len(us)))
    return out


def run(
    measurement: str,
    model: Model | None,
    tracer: Tracer,
    *,
    csv_path: Path = PRODUCTION_CSV,
    exclude_below: float | None = None,
) -> Report:
    """Check every `measurement` row (`"RIPPLE"`, `"VOUT"`, ...) against its own limits, then
    report yield, Cpk, a control chart, and the same numbers grouped by lot, fixture, day and
    shift. `model` is accepted only to fit the shared `(text, model, tracer)` convention every
    recordable example in this repo follows; level 0 calls no model, so it is never used.

    `exclude_below` drops readings whose magnitude sits under it before any statistic is
    computed, for a measurement where a reading near zero is not a low value but a sign the
    board never powered up: `VOUT` at 24 V in reads about 5 V on a working board and about 0 V
    on a dead one, and a dead board is a different, already-known defect
    (`docs/THE-BENCH.md`'s two `DEAD_UNITS`), not a data point in this measurement's process.
    Mixing the two would make a capability index describe neither: a working population's Cpk
    diluted by values that were never a measurement of the same thing. The two boards are not
    lost, only set aside from this arithmetic: `_load_units` below still counts them as failed
    units for `overall_yield_pct` and `yield_by_lot`, since they still failed to ship.

    A `measurement` that is not one of `MEASUREMENTS` falls back to `DEFAULT_MEASUREMENT` rather
    than raising: a fixed, code-decided default, the same shape as the routing example's own
    "unclear" fallback, so a caller that does not know this recipe's step names (a generic
    driver like `scripts/record_trace.py`, exercising every recordable example with one
    placeholder question) still gets a real report instead of an exception."""
    del model
    normalized = measurement.strip().upper()
    if normalized not in MEASUREMENTS:
        tracer.record(
            kind="code", decided_by="code", title="Unrecognized measurement, using the default",
            detail=f"{measurement!r} is not one of {MEASUREMENTS}; using {DEFAULT_MEASUREMENT}",
        )
        normalized = DEFAULT_MEASUREMENT
    measurement = normalized
    readings = load_readings(csv_path, measurement)
    if not readings:
        raise ValueError(f"no rows for measurement {measurement!r} in {csv_path}")
    tracer.record(
        kind="code", decided_by="code", title="Load readings",
        detail=f"{len(readings)} {measurement} readings from {csv_path.name}",
    )
    if exclude_below is not None:
        before = len(readings)
        readings = [r for r in readings if abs(r.value) >= exclude_below]
        tracer.record(
            kind="code", decided_by="code", title="Set aside boards that never powered up",
            detail=f"dropped {before - len(readings)} reading(s) under {exclude_below} {readings[0].unit if readings else ''}",
        )
        if not readings:
            raise ValueError(f"exclude_below={exclude_below} left no {measurement} readings")

    lower, upper = readings[0].lower, readings[0].upper
    values = [r.value for r in readings]
    failed = sum(1 for r in readings if not r.passed)
    tracer.record(
        kind="code", decided_by="code", title="Check limits",
        detail=f"lower={lower} upper={upper} {readings[0].unit}; {failed} of {len(readings)} outside",
    )

    by_lot = group_stats(readings, lambda r: r.lot)
    tracer.record(kind="code", decided_by="code", title="Group by lot", detail=f"{len(by_lot)} lots")
    by_fixture = group_stats(readings, lambda r: r.fixture)
    tracer.record(kind="code", decided_by="code", title="Group by fixture", detail=f"{len(by_fixture)} fixtures")
    by_day = group_stats(readings, lambda r: r.day)
    tracer.record(kind="code", decided_by="code", title="Group by day", detail=f"{len(by_day)} days")
    by_shift = group_stats(readings, lambda r: r.shift)
    tracer.record(kind="code", decided_by="code", title="Group by shift", detail=f"{len(by_shift)} shifts")

    chart = control_chart(readings)
    top_lot, top_lot_count = "none", 0
    if chart.flagged:
        top_lot, top_lot_count = Counter(r.lot for r in chart.flagged).most_common(1)[0]
    tracer.record(
        kind="code", decided_by="code", title="Individuals control chart",
        detail=(
            f"center={chart.center:.2f} UCL={chart.ucl:.2f} LCL={chart.lcl:.2f}; "
            f"{chart.out_of_control} of {len(readings)} points beyond the limits, "
            f"{top_lot_count} of them lot {top_lot}"
        ),
    )

    units = _load_units(csv_path)
    unit_failed = sum(1 for u in units if not u.passed)
    overall_yield = 100.0 * (len(units) - unit_failed) / len(units)
    tracer.record(
        kind="code", decided_by="code", title="First-pass yield, whole unit",
        detail=f"{len(units) - unit_failed} of {len(units)} units, {overall_yield:.1f}%",
    )
    yield_lot = yield_by(units, lambda u: u.lot)
    tracer.record(kind="code", decided_by="code", title="Yield by lot", detail=f"{len(yield_lot)} lots")

    return Report(
        measurement=measurement,
        unit=readings[0].unit,
        lower=lower,
        upper=upper,
        n=len(readings),
        mean=statistics.fmean(values),
        sd=statistics.stdev(values),
        cpk=cpk(values, lower, upper),
        by_lot=by_lot,
        by_fixture=by_fixture,
        by_day=by_day,
        by_shift=by_shift,
        chart=chart,
        overall_yield_pct=overall_yield,
        yield_by_lot=yield_lot,
    )
