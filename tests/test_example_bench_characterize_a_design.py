"""Tests for examples/bench_characterize_a_design: the margin at every corner, an uncertainty
budget from the meter's accuracy specification, a guardbanded line-regulation verdict, and the
repeatability problem that belongs to the meter's range and not to any board.

Every figure the answer key states in docs/THE-BENCH.md and evals/bench/corpus/characterization-
notebook.md is checked two ways here where one exists: once by calling the module under test, and
once by recomputing it independently in this file with plain `csv`, `statistics` and `math`, the
way tests/test_example_bench_limits_without_a_model.py checks the production log. A test that only
calls the module and compares to the module's own output would not catch a shared bug.
"""
from __future__ import annotations

import csv
import math
import statistics
import sys
import unittest
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.bench import CHARACTERIZATION_CSV  # noqa: E402
from examples.common.bench import (  # noqa: E402
    VERDICT_FAIL,
    VERDICT_PASS,
    VERDICT_UNKNOWN,
    combined_uncertainty,
    dc_voltage_budget,
    expanded_uncertainty,
    margin_to_limit,
)
from examples.common.model import StubModel  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.bench_characterize_a_design.run import (  # noqa: E402
    LEVEL,
    LINE_REG_MAX_PCT,
    NOMINAL_RANGE_V,
    VOUT_MAX_V,
    VOUT_MIN_V,
    Reading,
    budget_for_point,
    by_point,
    line_regulation_pct,
    load_readings,
    range_cost,
    regulation_uncertainty_pct,
    run,
    scan_line_regulation,
    spread_by_meter_range,
    window_margin,
    worst_corner_per_board,
)

# docs/THE-BENCH.md: "Board SRB5030-2609-0003 holds 20.4 mV of margin at 9 V in, 3 A out, 70 degC
# where the others hold 58 to 79 mV." The five serials are typed here once, only to state the
# answer key this file checks the module's own discovery against; run() never sees them.
THIN_MARGIN_SERIAL = "SRB5030-2609-0003"
MARGINAL_LINE_SERIAL = "SRB5030-2609-0005"
ALL_SERIALS = {
    "SRB5030-2609-0001",
    "SRB5030-2609-0002",
    THIN_MARGIN_SERIAL,
    "SRB5030-2609-0004",
    MARGINAL_LINE_SERIAL,
}


def _tracer() -> Tracer:
    return Tracer(example="bench_characterize_a_design", level=LEVEL, model_id="none")


def _rows() -> list[dict[str, str]]:
    with CHARACTERIZATION_CSV.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class WindowMarginTests(unittest.TestCase):
    def test_margin_to_the_lower_edge(self) -> None:
        margin, side = window_margin(4.920)
        self.assertAlmostEqual(margin, 0.020, places=6)
        self.assertEqual(side, "lower")

    def test_margin_to_the_upper_edge(self) -> None:
        margin, side = window_margin(5.090)
        self.assertAlmostEqual(margin, 0.010, places=6)
        self.assertEqual(side, "upper")

    def test_the_nominal_output_is_comfortably_inside_both_edges(self) -> None:
        margin, side = window_margin(5.000)
        self.assertAlmostEqual(margin, 0.100, places=6)
        self.assertEqual(side, "lower")  # tied; the function picks lower on a tie, arbitrarily


class LoadReadingsTests(unittest.TestCase):
    def test_every_row_becomes_a_reading(self) -> None:
        readings = load_readings(CHARACTERIZATION_CSV)
        self.assertEqual(len(readings), 900)
        self.assertEqual({r.serial for r in readings}, ALL_SERIALS)

    def test_by_point_groups_into_five_readings_a_corner(self) -> None:
        readings = load_readings(CHARACTERIZATION_CSV)
        points = by_point(readings)
        # 5 boards * 4 input voltages * 3 load currents * 3 ambients = 180 corners.
        self.assertEqual(len(points), 180)
        for key, group in points.items():
            self.assertEqual(len(group), 5, key)


class StoryOneWorstCornerTests(unittest.TestCase):
    """docs/THE-BENCH.md story A: one board's corner is a fifth of the others', and the worst
    corner is the same one, hot, low line, full load, for every board in the file."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = _rows()
        cls.points = by_point(load_readings(CHARACTERIZATION_CSV))
        cls.corners = worst_corner_per_board(cls.points)

    def test_one_corner_per_board_and_sorted_worst_first(self) -> None:
        self.assertEqual(len(self.corners), 5)
        margins = [c.margin_v for c in self.corners]
        self.assertEqual(margins, sorted(margins))

    def test_every_board_s_worst_corner_is_hot_low_line_full_load(self) -> None:
        for c in self.corners:
            self.assertEqual((c.tamb_c, c.vin_v, c.iout_a), (70.0, 9.0, 3.000), c.serial)
            self.assertEqual(c.side, "lower")

    def test_the_thinnest_margin_matches_the_answer_key(self) -> None:
        by_serial = {c.serial: c for c in self.corners}
        thin = by_serial[THIN_MARGIN_SERIAL]
        self.assertAlmostEqual(1000.0 * thin.margin_v, 20.4, delta=0.2)
        for serial, c in by_serial.items():
            if serial == THIN_MARGIN_SERIAL:
                continue
            self.assertGreater(1000.0 * c.margin_v, 58.0, serial)
            self.assertLess(1000.0 * c.margin_v, 79.0, serial)
        self.assertEqual(self.corners[0].serial, THIN_MARGIN_SERIAL)

    def test_margins_recomputed_independently_from_the_raw_csv_agree(self) -> None:
        values = defaultdict(list)
        for r in self.rows:
            if (r["tamb_c"], r["vin_v"], r["iout_a"]) == ("70.0", "9.0", "3.000"):
                values[r["serial"]].append(float(r["vout_v"]))
        by_serial = {c.serial: c for c in self.corners}
        for serial, vals in values.items():
            expected_mean = statistics.fmean(vals)
            self.assertAlmostEqual(by_serial[serial].mean_v, expected_mean, places=6, msg=serial)
            expected_margin = expected_mean - VOUT_MIN_V
            self.assertAlmostEqual(by_serial[serial].margin_v, expected_margin, places=6, msg=serial)

    def test_it_passes_everywhere_nothing_here_is_a_failing_board(self) -> None:
        for c in self.corners:
            self.assertGreater(c.mean_v, VOUT_MIN_V)
            self.assertLess(c.mean_v, VOUT_MAX_V)

    def test_the_margin_is_a_finding_and_not_a_measurement_artifact(self) -> None:
        """20.4 mV against an expanded uncertainty of about 0.35 mV: the measurement decides this."""
        thin = next(c for c in self.corners if c.serial == THIN_MARGIN_SERIAL)
        budget = budget_for_point(self.points[(thin.serial, thin.tamb_c, thin.vin_v, thin.iout_a)])
        self.assertGreater(thin.margin_v / budget.expanded_v, 50.0)


class UncertaintyBudgetTests(unittest.TestCase):
    """The budget is four named lines, combined by root sum of squares, expanded at k=2, and it
    is examples.common.bench doing the arithmetic, checked here against an independent RSS."""

    def setUp(self) -> None:
        self.points = by_point(load_readings(CHARACTERIZATION_CSV))
        thin = worst_corner_per_board(self.points)[0]
        self.readings = self.points[(thin.serial, thin.tamb_c, thin.vin_v, thin.iout_a)]

    def test_four_named_contributions_in_the_manual_s_order(self) -> None:
        budget = budget_for_point(self.readings, range_v=NOMINAL_RANGE_V)
        names = [c.name for c in budget.contributions]
        self.assertEqual(names, ["meter accuracy", "resolution", "repeatability", "leads and connections"])
        for c in budget.contributions:
            self.assertGreater(c.standard_uncertainty, 0.0, c.name)

    def test_combined_is_the_root_sum_of_squares_of_the_four_lines(self) -> None:
        budget = budget_for_point(self.readings, range_v=NOMINAL_RANGE_V)
        expected = math.sqrt(sum(c.standard_uncertainty**2 for c in budget.contributions))
        self.assertAlmostEqual(budget.combined_v, expected, places=12)

    def test_expanded_is_the_combined_uncertainty_times_two(self) -> None:
        budget = budget_for_point(self.readings, range_v=NOMINAL_RANGE_V)
        self.assertAlmostEqual(budget.expanded_v, 2.0 * budget.combined_v, places=12)

    def test_matches_the_value_this_page_reports(self) -> None:
        """352.7 uV expanded, for this corner's own five readings. Two nearby figures belong to
        other readings and neither is this one: characterization-notebook.md section 6 gets
        351.6 uV for a generic reading of this session, and mdn6100-programming-manual.md section
        8 gets 349.5 uV for ten readings of a different rail. The differences are the
        repeatability line, which is this block's own spread rather than a looked-up one."""
        budget = budget_for_point(self.readings)
        self.assertAlmostEqual(1e6 * budget.expanded_v, 352.7, delta=0.1)

    def test_the_range_defaults_to_the_one_the_readings_were_actually_taken_on(self) -> None:
        """A budget that has to be told the range can be told the wrong one. The file carries it
        per reading, so the default reads it there, and every reading of this corner is on the
        10 V range the sweep script selected."""
        self.assertEqual({r.meter_range_v for r in self.readings}, {NOMINAL_RANGE_V})
        by_default = budget_for_point(self.readings)
        told = budget_for_point(self.readings, range_v=NOMINAL_RANGE_V)
        self.assertAlmostEqual(by_default.expanded_v, told.expanded_v, places=12)

    def test_meter_accuracy_is_named_and_priced_at_the_range_it_was_read_on(self) -> None:
        wrong_range = budget_for_point(self.readings, range_v=100.0)
        right_range = budget_for_point(self.readings, range_v=NOMINAL_RANGE_V)
        meter_wrong = next(c for c in wrong_range.contributions if c.name == "meter accuracy")
        meter_right = next(c for c in right_range.contributions if c.name == "meter accuracy")
        self.assertGreater(meter_wrong.standard_uncertainty, meter_right.standard_uncertainty)


class StoryTwoGuardbandedVerdictTests(unittest.TestCase):
    """docs/THE-BENCH.md story B: one board's line regulation is inside its limit by less than
    the measurement is worth at one ambient, and the honest verdict is cannot say."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.points = by_point(load_readings(CHARACTERIZATION_CSV))
        cls.checks = scan_line_regulation(cls.points)

    def test_every_board_at_every_ambient_is_checked(self) -> None:
        # 5 boards * 3 ambients = 15 checks.
        self.assertEqual(len(self.checks), 15)
        self.assertEqual({(c.serial, c.tamb_c) for c in self.checks}, {
            (serial, tamb) for serial in ALL_SERIALS for tamb in (0.0, 25.0, 70.0)
        })

    def test_the_three_outcome_verdict_is_used_and_found_where_the_answer_key_says(self) -> None:
        by_key = {(c.serial, c.tamb_c): c for c in self.checks}
        self.assertEqual(by_key[(MARGINAL_LINE_SERIAL, 0.0)].verdict, VERDICT_PASS)
        self.assertEqual(by_key[(MARGINAL_LINE_SERIAL, 25.0)].verdict, VERDICT_UNKNOWN)
        self.assertEqual(by_key[(MARGINAL_LINE_SERIAL, 70.0)].verdict, VERDICT_FAIL)

    def test_the_figures_the_notebook_quotes(self) -> None:
        by_key = {(c.serial, c.tamb_c): c for c in self.checks}
        self.assertAlmostEqual(by_key[(MARGINAL_LINE_SERIAL, 0.0)].value_pct, 0.267, places=3)
        self.assertAlmostEqual(by_key[(MARGINAL_LINE_SERIAL, 25.0)].value_pct, 0.299, places=3)
        self.assertAlmostEqual(by_key[(MARGINAL_LINE_SERIAL, 70.0)].value_pct, 0.334, places=3)

    def test_only_that_one_board_is_ever_not_a_clean_pass(self) -> None:
        not_pass = [c for c in self.checks if c.verdict != VERDICT_PASS]
        self.assertEqual({c.serial for c in not_pass}, {MARGINAL_LINE_SERIAL})

    def test_leaving_the_uncertainty_out_would_have_called_the_middle_row_a_pass(self) -> None:
        """What a production-style limit check does with the same number: 0.299 is under 0.300,
        so a bare comparison passes and says nothing true about whether the board meets its
        limit. Reusing the same guardbanding machinery with expanded=0.0 makes that comparison,
        deliberately, to show what the uncertainty is actually buying."""
        from examples.common.bench import guarded_verdict

        by_key = {(c.serial, c.tamb_c): c for c in self.checks}
        value = by_key[(MARGINAL_LINE_SERIAL, 25.0)].value_pct
        self.assertLess(value, LINE_REG_MAX_PCT)
        self.assertEqual(guarded_verdict(value, 0.0, upper=LINE_REG_MAX_PCT), VERDICT_PASS)

    def test_the_regulation_uncertainty_is_about_the_notebook_s_own_figure(self) -> None:
        u = regulation_uncertainty_pct(
            self.points[(MARGINAL_LINE_SERIAL, 25.0, 32.0, 1.000)],
            self.points[(MARGINAL_LINE_SERIAL, 25.0, 9.0, 1.000)],
        )
        # characterization-notebook.md section 6: 0.0075 percentage points.
        self.assertAlmostEqual(u, 0.0075, delta=0.0015)

    def test_a_regulation_figure_whose_two_ends_used_different_ranges_is_priced_on_the_worse(self) -> None:
        """Board 3's 32 V block at 25 degC was read on the 100 V range and its 9 V block on the
        10 V range, because the slipped-range window crosses one end of that sweep. A difference
        is no better than the weaker half of it, so the pair is priced on the 100 V row: about
        four times the uncertainty of an ordinary regulation figure on this bench. It is still a
        pass, and pricing it on the 10 V range it was half taken on would have understated it."""
        by_key = {(c.serial, c.tamb_c): c for c in self.checks}
        crossed = by_key[(THIN_MARGIN_SERIAL, 25.0)]
        ordinary = by_key[(THIN_MARGIN_SERIAL, 70.0)]
        self.assertGreater(crossed.uncertainty_pct, 3.0 * ordinary.uncertainty_pct)
        self.assertEqual(crossed.verdict, VERDICT_PASS)

    def test_regulation_uncertainty_recomputed_independently_from_the_raw_csv_agrees(self) -> None:
        rows = _rows()

        def per_reading_at(vin: str) -> float:
            block = [
                r for r in rows
                if r["serial"] == MARGINAL_LINE_SERIAL and r["tamb_c"] == "25.0"
                and r["vin_v"] == vin and r["iout_a"] == "1.000"
            ]
            range_v = max(float(r["meter_range_v"]) for r in block)
            return combined_uncertainty(
                dc_voltage_budget(
                    [float(r["vout_v"]) for r in block], range_v=range_v, lead_half_width_v=None
                )
            )

        per_reading = max(per_reading_at("32.0"), per_reading_at("9.0"))
        expected = 100.0 * expanded_uncertainty(per_reading * math.sqrt(2.0)) / 5.000
        by_key = {(c.serial, c.tamb_c): c for c in self.checks}
        self.assertAlmostEqual(by_key[(MARGINAL_LINE_SERIAL, 25.0)].uncertainty_pct, expected, places=6)

    def test_line_regulation_pct_matches_an_independent_reading_of_the_csv(self) -> None:
        rows = _rows()

        def mean_at(serial: str, tamb: str, vin: str, iout: str) -> float:
            values = [
                float(r["vout_v"]) for r in rows
                if r["serial"] == serial and r["tamb_c"] == tamb and r["vin_v"] == vin and r["iout_a"] == iout
            ]
            return statistics.fmean(values)

        expected = 100.0 * (mean_at(MARGINAL_LINE_SERIAL, "25.0", "32.0", "1.000") - mean_at(MARGINAL_LINE_SERIAL, "25.0", "9.0", "1.000")) / 5.000
        self.assertAlmostEqual(line_regulation_pct(self.points, MARGINAL_LINE_SERIAL, 25.0), expected, places=9)


class StoryThreeMeterRangeTests(unittest.TestCase):
    """docs/THE-BENCH.md story C: sixty readings scatter more because the meter was left on the
    100 V range, and that follows the range column, not any board and not any corner."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.points = by_point(load_readings(CHARACTERIZATION_CSV))
        cls.spreads = spread_by_meter_range(cls.points)

    def test_two_ranges_are_present_and_the_nominal_one_dominates(self) -> None:
        self.assertEqual(len(self.spreads), 2)
        self.assertEqual(self.spreads[0].range_v, NOMINAL_RANGE_V)
        self.assertEqual(self.spreads[0].n_points, 168)
        self.assertEqual(self.spreads[1].range_v, 100.0)
        self.assertEqual(self.spreads[1].n_points, 12)

    def test_the_slipped_range_is_seven_times_noisier_and_does_not_overlap_the_other(self) -> None:
        nominal, slipped = self.spreads[0], self.spreads[1]
        self.assertGreater(slipped.mean_stdev_v / nominal.mean_stdev_v, 5.0)

    def test_it_is_two_boards_not_one_and_not_all_five(self) -> None:
        slipped = self.spreads[1]
        self.assertEqual(len(slipped.boards), 2)
        self.assertLess(len(slipped.boards), 5)

    def test_range_cost_matches_the_notebook_s_quarter_of_the_others(self) -> None:
        ratio = range_cost(self.points, minority_range_v=100.0, majority_range_v=NOMINAL_RANGE_V)
        self.assertGreater(ratio, 2.3)
        self.assertLess(ratio, 2.5)

    def test_range_cost_recomputed_independently_agrees(self) -> None:
        rows = _rows()
        first_slipped_point = None
        seen = set()
        for r in rows:
            key = (r["serial"], r["tamb_c"], r["vin_v"], r["iout_a"])
            if r["meter_range_v"] == "100.0" and key not in seen:
                first_slipped_point = key
                break
            seen.add(key)
        self.assertIsNotNone(first_slipped_point)
        serial, tamb, vin, iout = first_slipped_point
        values = [
            float(r["vout_v"]) for r in rows
            if (r["serial"], r["tamb_c"], r["vin_v"], r["iout_a"]) == first_slipped_point
        ]
        wrong = expanded_uncertainty(combined_uncertainty(dc_voltage_budget(values, range_v=100.0)))
        right = expanded_uncertainty(combined_uncertainty(dc_voltage_budget(values, range_v=NOMINAL_RANGE_V)))
        ratio = range_cost(self.points, minority_range_v=100.0, majority_range_v=NOMINAL_RANGE_V)
        # Both computations pick "a" slipped point (dict ordering is not the same as CSV row
        # order), so this checks the two independent methods land in the same narrow band rather
        # than pinning them to one specific point's exact ratio.
        self.assertAlmostEqual(wrong / right, ratio, delta=0.05)


class RunEntryPointTests(unittest.TestCase):
    def test_declares_its_level_and_calls_no_model(self) -> None:
        import examples.bench_characterize_a_design.run as module

        self.assertEqual(module.LEVEL, 0)
        self.assertTrue(callable(module.run))

    def test_run_ignores_a_model_even_when_one_is_given(self) -> None:
        tracer = _tracer()
        report = run(THIN_MARGIN_SERIAL, StubModel([]), tracer)
        self.assertEqual(tracer.model_decided_count(), 0)
        self.assertGreater(report.n_readings, 0)

    def test_every_trace_step_is_code_decided(self) -> None:
        tracer = _tracer()
        run(THIN_MARGIN_SERIAL, None, tracer)
        self.assertTrue(tracer.steps)
        self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))
        self.assertEqual(tracer.model_decided_count(), 0)

    def test_an_unrecognized_serial_falls_back_to_the_thinnest_margin_rather_than_raising(self) -> None:
        """A caller that does not know this recipe's serials (record_trace.py's generic driver,
        exercising every recordable example with one placeholder question) still gets a real
        report, and the fallback is discovered from this run's own arithmetic, not a name typed
        in advance."""
        tracer = _tracer()
        report = run("What is the maximum vent run for a DR-520?", None, tracer)
        self.assertEqual(report.focus_serial, THIN_MARGIN_SERIAL)
        self.assertGreater(report.n_readings, 0)
        self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))
        fallback_steps = [s for s in tracer.steps if "unrecognized" in s.title.lower()]
        self.assertEqual(len(fallback_steps), 1)

    def test_serial_is_case_and_whitespace_insensitive(self) -> None:
        report = run(f"  {THIN_MARGIN_SERIAL.lower()} \n", None, _tracer())
        self.assertEqual(report.focus_serial, THIN_MARGIN_SERIAL)

    def test_report_holds_every_number_this_page_states(self) -> None:
        report = run(THIN_MARGIN_SERIAL, None, _tracer())
        self.assertEqual(len(report.corners), 5)
        self.assertEqual(report.corners[0].serial, THIN_MARGIN_SERIAL)
        self.assertEqual(report.thin_verdict, VERDICT_PASS)
        self.assertEqual(len(report.line_regulation), 15)
        self.assertEqual(len(report.spread_by_range), 2)
        self.assertIsNotNone(report.range_cost_ratio)

    def test_record_trace_classifies_this_example_as_recordable(self) -> None:
        if str(ROOT / "scripts") not in sys.path:
            sys.path.insert(0, str(ROOT / "scripts"))
        import record_trace

        rec = record_trace.classify("bench_characterize_a_design")
        self.assertTrue(rec.ok, rec.reason)
        self.assertFalse(rec.takes_embedder)


class CommandLineTests(unittest.TestCase):
    """This example calls no model, so it has no `SCRIPTED` sequence; `tests/test_scripted_stub.py`
    is where that is declared, in `NO_SCRIPT`. What belongs here is that the command's own
    `--model` flag, added only so this command runs the same way every other example's does,
    never changes what gets printed and never fails whatever it is given."""

    def test_no_scripted_sequence_is_exported(self) -> None:
        import examples.bench_characterize_a_design.__main__ as module

        self.assertIsNone(getattr(module, "SCRIPTED", None))

    def test_the_command_runs_the_same_regardless_of_model_spec(self) -> None:
        import io
        from contextlib import redirect_stdout

        import examples.bench_characterize_a_design.__main__ as module

        outputs = []
        for model_spec in ("stub", "stub:scripted", "ollama:some-tag"):
            out = io.StringIO()
            with redirect_stdout(out):
                code = module.main(["--model", model_spec, "--serial", THIN_MARGIN_SERIAL])
            self.assertEqual(code, 0)
            outputs.append(out.getvalue())
        self.assertTrue(all(o == outputs[0] for o in outputs))


if __name__ == "__main__":
    unittest.main()
