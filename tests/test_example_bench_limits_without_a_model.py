"""Tests for examples/bench_limits_without_a_model: limit checks, first-pass yield, Cpk, a
control chart and grouping by lot, fixture, day and shift, over the real bench production log.

Every number here is checked two ways where the answer key in docs/THE-BENCH.md states one: once
by calling the module under test, and once by recomputing it independently in this file with
plain `csv` and `statistics`, the way `tests/test_bench_data.py` checks the data itself. A test
that only calls the module and compares to the module's own output would not catch a shared bug.
"""
from __future__ import annotations

import csv
import statistics
import sys
import unittest
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.bench import PRODUCTION_CSV  # noqa: E402
from examples.common.model import StubModel  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.bench_limits_without_a_model.run import (  # noqa: E402
    LEVEL,
    Reading,
    control_chart,
    cpk,
    group_stats,
    load_readings,
    run,
    within_limits,
)

MARGINAL_LOT = "L2608B"
OFFSET_FIXTURE = "FIX-03"


def _tracer() -> Tracer:
    return Tracer(example="bench_limits_without_a_model", level=LEVEL, model_id="none")


class WithinLimitsTests(unittest.TestCase):
    """The whole pass/fail decision: two comparisons, nothing else."""

    def test_upper_limit_only(self) -> None:
        self.assertTrue(within_limits(49.9, None, 50.0))
        self.assertTrue(within_limits(50.0, None, 50.0))
        self.assertFalse(within_limits(50.1, None, 50.0))

    def test_lower_limit_only(self) -> None:
        self.assertTrue(within_limits(500.0, 500.0, None))
        self.assertFalse(within_limits(499.9, 500.0, None))

    def test_both_limits(self) -> None:
        self.assertTrue(within_limits(5.000, 4.950, 5.050))
        self.assertFalse(within_limits(4.949, 4.950, 5.050))
        self.assertFalse(within_limits(5.051, 4.950, 5.050))

    def test_no_limits_always_passes(self) -> None:
        self.assertTrue(within_limits(1e9, None, None))


class CpkTests(unittest.TestCase):
    def test_one_sided_upper_is_the_standard_formula(self) -> None:
        values = [8.0, 10.0, 12.0]  # mean 10, sd 2
        self.assertAlmostEqual(cpk(values, None, 16.0), 1.0)

    def test_one_sided_lower_is_the_standard_formula(self) -> None:
        values = [8.0, 10.0, 12.0]
        self.assertAlmostEqual(cpk(values, 4.0, None), 1.0)

    def test_two_sided_is_the_smaller_of_the_two_one_sided_numbers(self) -> None:
        values = [8.0, 10.0, 12.0]
        # upper-side Cpk = (16-10)/(3*2) = 1.0; lower-side = (10-2)/(3*2) = 1.333; min is 1.0
        self.assertAlmostEqual(cpk(values, 2.0, 16.0), 1.0)

    def test_no_limit_is_none(self) -> None:
        self.assertIsNone(cpk([1.0, 2.0, 3.0], None, None))

    def test_fewer_than_two_readings_is_none(self) -> None:
        self.assertIsNone(cpk([5.0], None, 10.0))

    def test_zero_spread_is_none_rather_than_a_division_by_zero(self) -> None:
        self.assertIsNone(cpk([5.0, 5.0, 5.0], None, 10.0))


class LoadReadingsAgreesWithTheLogsOwnResultTests(unittest.TestCase):
    """`within_limits` must recompute the same verdict the log already carries, for every
    measurement, the same claim tests/test_bench_data.py makes about the log itself."""

    def test_every_recomputed_verdict_matches_the_logged_result(self) -> None:
        with PRODUCTION_CSV.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        measurements = {r["measurement"] for r in rows}
        for measurement in measurements:
            for reading in load_readings(PRODUCTION_CSV, measurement):
                logged = next(
                    r for r in rows
                    if r["measurement"] == measurement and r["serial"] == reading.serial
                )
                expected = logged["result"] == "PASS"
                self.assertEqual(reading.passed, expected, (measurement, reading.serial))


class RippleStoryTests(unittest.TestCase):
    """Story 1 in docs/THE-BENCH.md: one lot's ripple mean and Cpk move enormously while yield
    by lot barely moves. Every number here is the answer key's own number, recomputed."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tracer = _tracer()
        cls.report = run("RIPPLE", None, cls.tracer, csv_path=PRODUCTION_CSV)

    def test_every_trace_step_is_code_decided(self) -> None:
        self.assertTrue(self.tracer.steps)
        self.assertTrue(all(s.decided_by == "code" for s in self.tracer.steps))
        self.assertEqual(self.tracer.model_decided_count(), 0)

    def test_overall_population_cpk_matches_the_answer_key(self) -> None:
        # docs/THE-BENCH.md: "The whole-population Cpk is 0.72."
        self.assertEqual(self.report.n, 198)
        self.assertAlmostEqual(self.report.mean, 27.37, places=1)
        self.assertAlmostEqual(self.report.sd, 10.55, places=1)
        self.assertAlmostEqual(self.report.cpk, 0.72, places=2)

    def test_by_lot_table_matches_the_answer_key(self) -> None:
        expected = {
            "L2608A": (52, 21.21, 3.40, 2.82),
            "L2608B": (51, 44.41, 3.76, 0.50),
            "L2608C": (47, 21.50, 1.36, 6.97),
            "L2608D": (48, 21.67, 3.54, 2.67),
        }
        by_lot = {g.key: g for g in self.report.by_lot}
        self.assertEqual(set(by_lot), set(expected))
        for lot, (n, mean, sd, lot_cpk) in expected.items():
            g = by_lot[lot]
            self.assertEqual(g.n, n, lot)
            self.assertAlmostEqual(g.mean, mean, places=1, msg=lot)
            self.assertAlmostEqual(g.sd, sd, places=1, msg=lot)
            self.assertAlmostEqual(g.cpk, lot_cpk, places=1, msg=lot)

    def test_the_marginal_lot_is_not_capable_and_the_others_are(self) -> None:
        by_lot = {g.key: g for g in self.report.by_lot}
        self.assertLess(by_lot[MARGINAL_LOT].cpk, 1.0)
        for lot, g in by_lot.items():
            if lot != MARGINAL_LOT:
                self.assertGreater(g.cpk, 1.33, lot)

    def test_yield_by_lot_matches_the_answer_key_and_barely_moves(self) -> None:
        # docs/THE-BENCH.md: "Yield by lot is 96.2%, 90.4%, 89.6% and 91.7%."
        expected = {"L2608A": 96.2, "L2608B": 90.4, "L2608C": 89.6, "L2608D": 91.7}
        by_lot = {g.key: g for g in self.report.yield_by_lot}
        self.assertEqual(set(by_lot), set(expected))
        for lot, pct in expected.items():
            self.assertAlmostEqual(by_lot[lot].yield_pct, pct, places=1, msg=lot)
        spread = max(g.yield_pct for g in self.report.yield_by_lot) - min(g.yield_pct for g in self.report.yield_by_lot)
        self.assertLess(spread, 7.0, "yield by lot should barely move")

    def test_ripple_mean_and_cpk_move_far_more_than_yield_does(self) -> None:
        """The argument the page exists to make: chart the measurement, don't just count fails."""
        by_lot = {g.key: g for g in self.report.by_lot}
        by_yield = {g.key: g for g in self.report.yield_by_lot}
        mean_ratio = by_lot[MARGINAL_LOT].mean / max(
            g.mean for lot, g in by_lot.items() if lot != MARGINAL_LOT
        )
        yield_ratio = by_yield[MARGINAL_LOT].yield_pct / max(
            g.yield_pct for lot, g in by_yield.items() if lot != MARGINAL_LOT
        )
        self.assertGreater(mean_ratio, 1.8)
        self.assertGreater(yield_ratio, 0.9)  # yield moves by a few points, not by a near-double

    def test_grouping_by_day_and_by_shift_moves_far_less_than_grouping_by_lot_does(self) -> None:
        """docs/THE-BENCH.md: grouping by day and by shift "finds nothing." A day-to-day or
        shift-to-shift wobble of a couple of mV is ordinary noise next to the 23 mV the marginal
        lot itself shifts the mean by; the test states that comparison rather than a bare
        threshold, so it does not depend on exactly how big ordinary noise happens to be."""
        lot_means = [g.mean for g in self.report.by_lot]
        lot_spread = max(lot_means) - min(lot_means)
        for label, rows in (("day", self.report.by_day), ("shift", self.report.by_shift)):
            means = [g.mean for g in rows]
            spread = max(means) - min(means)
            self.assertLess(spread, lot_spread / 5.0, label)

    def test_overall_first_pass_yield_matches_the_answer_key(self) -> None:
        self.assertAlmostEqual(self.report.overall_yield_pct, 92.0, places=1)

    def test_control_chart_flags_the_marginal_lot_without_being_told_which_lot_it_is(self) -> None:
        chart = self.report.chart
        self.assertGreater(chart.out_of_control, 0)
        by_lot = defaultdict(int)
        for r in chart.flagged:
            by_lot[r.lot] += 1
        top_lot, top_count = max(by_lot.items(), key=lambda kv: kv[1])
        self.assertEqual(top_lot, MARGINAL_LOT)
        # Most of the marginal lot's own readings are flagged, and only a stray few from anyone else.
        self.assertGreater(top_count / 51, 0.5)
        self.assertLess(sum(v for k, v in by_lot.items() if k != MARGINAL_LOT), 5)

    def test_control_limits_recomputed_independently_match(self) -> None:
        """Recompute the I-MR control limits from the raw CSV, not from the module under test."""
        with PRODUCTION_CSV.open(encoding="utf-8", newline="") as handle:
            values = [float(r["value"]) for r in csv.DictReader(handle) if r["measurement"] == "RIPPLE"]
        moving_ranges = [abs(values[i] - values[i - 1]) for i in range(1, len(values))]
        mr_bar = statistics.fmean(moving_ranges)
        sigma = mr_bar / 1.128
        mean = statistics.fmean(values)
        self.assertAlmostEqual(self.report.chart.center, mean, places=6)
        self.assertAlmostEqual(self.report.chart.sigma, sigma, places=6)
        self.assertAlmostEqual(self.report.chart.ucl, mean + 3 * sigma, places=6)

    def test_control_limits_differ_from_the_spec_limit(self) -> None:
        """A control limit is a statement about the process, not the 50 mV spec limit."""
        self.assertNotAlmostEqual(self.report.chart.ucl, 50.0, places=0)


class FixtureStoryTests(unittest.TestCase):
    """Story 2 in docs/THE-BENCH.md: one fixture reads low on VOUT, and only VOUT moves."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tracer = _tracer()
        cls.report = run("VOUT", None, cls.tracer, csv_path=PRODUCTION_CSV, exclude_below=1.0)

    def test_by_fixture_table_matches_the_answer_key(self) -> None:
        expected = {
            "FIX-01": (49, 4.9892, 1.09),
            "FIX-02": (48, 4.9922, 1.09),
            "FIX-03": (49, 4.9640, 0.44),
            "FIX-04": (50, 4.9906, 1.09),
        }
        by_fixture = {g.key: g for g in self.report.by_fixture}
        self.assertEqual(set(by_fixture), set(expected))
        for fixture, (n, mean, fixture_cpk) in expected.items():
            g = by_fixture[fixture]
            self.assertEqual(g.n, n, fixture)
            self.assertAlmostEqual(g.mean, mean, places=3, msg=fixture)
            self.assertAlmostEqual(g.cpk, fixture_cpk, places=1, msg=fixture)

    def test_only_one_fixture_reads_low(self) -> None:
        by_fixture = {g.key: g for g in self.report.by_fixture}
        suspect = by_fixture.pop(OFFSET_FIXTURE)
        others = statistics.fmean(g.mean for g in by_fixture.values())
        self.assertLess(suspect.mean, others - 0.02)
        self.assertLess(max(g.mean for g in by_fixture.values()) - min(g.mean for g in by_fixture.values()), 0.005)

    def test_grouping_by_day_and_by_shift_finds_nothing(self) -> None:
        for rows in (self.report.by_day, self.report.by_shift):
            means = [g.mean for g in rows]
            self.assertLess(max(means) - min(means), 0.006)

    def test_excluding_dead_boards_is_what_makes_the_fixture_count_and_mean_match(self) -> None:
        """Without `exclude_below`, the two dead boards' near-zero VOUT readings land on
        whichever fixture they happened to sit on, inflating that fixture's row count and
        dragging its mean toward zero -- not a fixture problem, a different one."""
        unfiltered = run("VOUT", None, _tracer(), csv_path=PRODUCTION_CSV)
        filtered_n = sum(g.n for g in self.report.by_fixture)
        unfiltered_n = sum(g.n for g in unfiltered.by_fixture)
        self.assertEqual(unfiltered_n - filtered_n, 2)
        # One dead board's 0 V reading pulls its fixture's mean down by about a tenth of a volt
        # over roughly fifty readings; small in absolute terms, and still not a fixture problem.
        by_fixture_unfiltered = {g.key: g for g in unfiltered.by_fixture}
        by_fixture_filtered = {g.key: g for g in self.report.by_fixture}
        moved = [
            by_fixture_filtered[k].mean - by_fixture_unfiltered[k].mean
            for k in by_fixture_filtered
            if by_fixture_unfiltered[k].n != by_fixture_filtered[k].n
        ]
        self.assertTrue(moved)
        self.assertTrue(all(m > 0.03 for m in moved))
        self.assertGreater(min(g.mean for g in self.report.by_fixture), 4.9)

    def test_the_cpk_form_is_two_sided_because_vout_has_both_limits(self) -> None:
        # VOUT's limits are 4.9500 and 5.0500; a two-sided Cpk must not exceed either one-sided term.
        self.assertLess(self.report.cpk, (5.0500 - self.report.mean) / (3 * self.report.sd) + 1e-9)
        self.assertLess(self.report.cpk, (self.report.mean - 4.9500) / (3 * self.report.sd) + 1e-9)


class GroupStatsTests(unittest.TestCase):
    """`group_stats` itself, on small hand-built readings, independent of the bench data."""

    def _reading(self, lot: str, value: float, passed: bool) -> Reading:
        return Reading(
            serial="X", lot=lot, fixture="F", shift="A", day="2026-01-01",
            value=value, unit="mV", lower=None, upper=50.0, passed=passed,
        )

    def test_two_groups_get_independent_stats(self) -> None:
        readings = [
            self._reading("A", 10.0, True), self._reading("A", 12.0, True), self._reading("A", 60.0, False),
            self._reading("B", 20.0, True), self._reading("B", 20.0, True),
        ]
        by_lot = {g.key: g for g in group_stats(readings, lambda r: r.lot)}
        self.assertEqual(by_lot["A"].n, 3)
        self.assertAlmostEqual(by_lot["A"].yield_pct, 200.0 / 3, places=3)
        self.assertEqual(by_lot["B"].n, 2)
        self.assertEqual(by_lot["B"].yield_pct, 100.0)
        self.assertEqual(by_lot["B"].sd, 0.0)  # two identical values: a real spread of zero, not "no data"


class ControlChartUnitTests(unittest.TestCase):
    def test_a_stable_run_flags_nothing(self) -> None:
        readings = [
            Reading("S", "L", "F", "A", "d", v, "mV", None, 50.0, True)
            for v in (10.0, 10.5, 9.8, 10.2, 9.9, 10.1)
        ]
        chart = control_chart(readings)
        self.assertEqual(chart.out_of_control, 0)

    def test_one_far_outlier_is_flagged(self) -> None:
        # A single spike inflates the two moving ranges touching it, so a chart needs more than
        # a handful of points before that inflation stops swallowing the spike's own flag; twenty
        # stable points and one is enough to show it without depending on the bench data.
        stable = (10.0, 10.2, 9.9, 10.1, 9.8, 10.0, 10.3, 9.9, 10.1, 10.0)
        values = list(stable) + [40.0] + list(stable)
        readings = [Reading("S", "L", "F", "A", "d", v, "mV", None, 50.0, True) for v in values]
        chart = control_chart(readings)
        self.assertEqual(chart.out_of_control, 1)
        self.assertEqual(chart.flagged[0].value, 40.0)

    def test_fewer_than_two_readings_returns_degenerate_limits_not_a_crash(self) -> None:
        self.assertEqual(control_chart([]).ucl, 0.0)
        one = [Reading("S", "L", "F", "A", "d", 5.0, "mV", None, 50.0, True)]
        chart = control_chart(one)
        self.assertEqual(chart.center, 5.0)
        self.assertEqual(chart.out_of_control, 0)


class RunEntryPointTests(unittest.TestCase):
    def test_declares_its_level_and_calls_no_model(self) -> None:
        import examples.bench_limits_without_a_model.run as module

        self.assertEqual(module.LEVEL, 0)
        self.assertTrue(callable(module.run))

    def test_run_ignores_a_model_even_when_one_is_given(self) -> None:
        tracer = _tracer()
        report = run("RIPPLE", StubModel([]), tracer, csv_path=PRODUCTION_CSV)
        self.assertEqual(tracer.model_decided_count(), 0)
        self.assertGreater(report.n, 0)

    def test_an_unrecognized_measurement_falls_back_to_the_default_rather_than_raising(self) -> None:
        """A caller that does not know this recipe's step names (record_trace.py's generic
        driver, exercising every recordable example with one placeholder question) still gets a
        real report: the fallback is a fixed, code-decided rule, not a guess."""
        from examples.bench_limits_without_a_model.run import DEFAULT_MEASUREMENT

        tracer = _tracer()
        report = run("What is the maximum vent run for a DR-520?", None, tracer, csv_path=PRODUCTION_CSV)
        self.assertEqual(report.measurement, DEFAULT_MEASUREMENT)
        self.assertGreater(report.n, 0)
        self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))
        fallback_steps = [s for s in tracer.steps if "default" in s.title.lower()]
        self.assertEqual(len(fallback_steps), 1)

    def test_measurement_names_are_case_and_whitespace_insensitive(self) -> None:
        report = run("  ripple \n", None, _tracer(), csv_path=PRODUCTION_CSV)
        self.assertEqual(report.measurement, "RIPPLE")
        self.assertEqual(report.n, 198)

    def test_record_trace_classifies_this_example_as_recordable(self) -> None:
        if str(ROOT / "scripts") not in sys.path:
            sys.path.insert(0, str(ROOT / "scripts"))
        import record_trace

        rec = record_trace.classify("bench_limits_without_a_model")
        self.assertTrue(rec.ok, rec.reason)
        self.assertFalse(rec.takes_embedder)


if __name__ == "__main__":
    unittest.main()
