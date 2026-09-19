"""The characterization data reproduces byte for byte, and every story in it is really there.

`docs/THE-BENCH.md` is the answer key. Each of the four stories gets a test that finds it the way
the answer key tells a reader to find it: by grouping, by comparing a margin against an
uncertainty, or by noticing that a current does not fit the voltage it is filed under.

Half of these tests are about what is NOT in the file. An engineering-test data set earns its
keep by supporting the sentence "it is not the boards", and that sentence is only worth saying if
somebody has checked it. So: no board is outside the datasheet window at any corner, the extra
scatter follows the meter range and not any board or any corner, and exactly one point is
recorded at a condition it was not taken at.
"""
from __future__ import annotations

import csv
import math
import statistics
import subprocess
import sys
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.bench import BENCH_DATA_DIR, CHARACTERIZATION_CSV  # noqa: E402
from evals.bench.make_characterization import (  # noqa: E402
    AMBIENTS_C,
    BOARDS,
    IOUT_A,
    MARGINAL_LINE_SERIAL,
    NOMINAL_RANGE_V,
    REPEATS,
    SLIPPED_RANGE_V,
    THIN_MARGIN_SERIAL,
    VIN_V,
    WRONG_CONDITION,
    WRONG_CONDITION_ACTUAL_VIN_V,
    generate,
)
from examples.common.bench import (  # noqa: E402
    VERDICT_FAIL,
    VERDICT_PASS,
    VERDICT_UNKNOWN,
    Contribution,
    combined_uncertainty,
    dc_voltage_budget,
    expanded_uncertainty,
    guarded_verdict,
    margin_to_limit,
)

NAME = "characterization-2026-09.csv"

#: The datasheet's own output voltage window over the full line, load and temperature range,
#: srb5030-datasheet.md section 4, and the line regulation maximum from the same table.
VOUT_MIN_V = 4.900
VOUT_MAX_V = 5.100
LINE_REG_MAX_PCT = 0.300
LOAD_REG_MAX_PCT = 0.800

#: The expanded uncertainty this session quotes, from characterization-notebook.md section 6:
#: 351.6 uV on one output voltage, and 0.0075 percentage points on a regulation figure, which is
#: a difference of two readings through the same leads. `tests/test_bench.py` recomputes both
#: from the budget functions; here they are the numbers a margin is compared against.
U_VOUT_V = 351.6e-6
U_REG_PCT = 0.0075


def read() -> list[dict[str, str]]:
    with CHARACTERIZATION_CSV.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def mean_at(rows: list[dict[str, str]], serial: str, tamb: str, vin: str, iout: str) -> float:
    values = [
        float(r["vout_v"])
        for r in rows
        if r["serial"] == serial
        and r["tamb_c"] == tamb
        and r["vin_v"] == vin
        and r["iout_a"] == iout
    ]
    return statistics.fmean(values)


def line_regulation_pct(rows: list[dict[str, str]], serial: str, tamb: str) -> float:
    """(VOUT at 32.0 V - VOUT at 9.0 V) / 5.000, as a percentage, at 1.000 A."""
    high = mean_at(rows, serial, tamb, "32.0", "1.000")
    low = mean_at(rows, serial, tamb, "9.0", "1.000")
    return 100.0 * (high - low) / 5.000


def load_regulation_pct(rows: list[dict[str, str]], serial: str, tamb: str) -> float:
    """(VOUT at 0.100 A - VOUT at 3.000 A) / 5.000, as a percentage, at 24.0 V."""
    light = mean_at(rows, serial, tamb, "24.0", "0.100")
    heavy = mean_at(rows, serial, tamb, "24.0", "3.000")
    return 100.0 * (light - heavy) / 5.000


def by_point(rows: list[dict[str, str]]) -> dict[tuple[str, ...], list[dict[str, str]]]:
    points: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        points[(row["serial"], row["tamb_c"], row["vin_v"], row["iout_a"])].append(row)
    return points


class TestReproducible(unittest.TestCase):
    def test_the_script_reproduces_the_committed_file_byte_for_byte(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            generate(Path(tmp))
            self.assertEqual(
                (Path(tmp) / NAME).read_bytes(), (BENCH_DATA_DIR / NAME).read_bytes()
            )

    def test_the_script_reproduces_it_from_a_fresh_interpreter_too(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, "-m", "evals.bench.make_characterization", tmp],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                (Path(tmp) / NAME).read_bytes(), (BENCH_DATA_DIR / NAME).read_bytes()
            )

    def test_generating_this_file_does_not_touch_the_production_files(self) -> None:
        """The three production CSVs are pinned byte for byte by `tests/test_bench_data.py`.

        A second generator that drew from the same random stream would move them, and the wave
        that added this one would have rewritten every number quoted on four recipe pages.
        """
        with tempfile.TemporaryDirectory() as tmp:
            generate(Path(tmp))
            written = sorted(p.name for p in Path(tmp).iterdir())
            self.assertEqual(written, [NAME])

    def test_line_endings_are_lf(self) -> None:
        raw = CHARACTERIZATION_CSV.read_bytes()
        self.assertNotIn(b"\r", raw)
        self.assertTrue(raw.endswith(b"\n"))


class TestSweepShape(unittest.TestCase):
    def setUp(self) -> None:
        self.rows = read()

    def test_five_boards_swept_over_every_corner_five_times(self) -> None:
        self.assertEqual(len({r["serial"] for r in self.rows}), len(BOARDS))
        self.assertEqual(len(self.rows), len(BOARDS) * len(VIN_V) * len(IOUT_A) * len(AMBIENTS_C) * REPEATS)
        for point, readings in by_point(self.rows).items():
            self.assertEqual(len(readings), REPEATS, point)
            self.assertEqual([r["reading_n"] for r in readings], ["1", "2", "3", "4", "5"], point)

    def test_a_row_is_a_reading_and_not_a_verdict(self) -> None:
        """The production log carries limits and a result column. This one carries neither.

        That is the difference between the two settings, and it is in the schema rather than in
        the prose: engineering test reports margins, and a margin needs the limit the reader is
        holding it against, which is the datasheet's, not the file's.
        """
        header = set(self.rows[0])
        self.assertEqual(
            header,
            {
                "serial",
                "revision",
                "tamb_c",
                "vin_v",
                "iout_a",
                "reading_n",
                "timestamp",
                "meter_range_v",
                "vout_v",
                "iin_a",
            },
        )
        self.assertNotIn("result", header)
        self.assertNotIn("lower_limit", header)

    def test_every_board_is_a_revision_c_prototype(self) -> None:
        self.assertEqual({r["revision"] for r in self.rows}, {"C"})
        for serial in {r["serial"] for r in self.rows}:
            self.assertRegex(serial, r"^SRB5030-2609-000[1-5]$")

    def test_one_chamber_setting_a_day_in_session_order(self) -> None:
        days: dict[str, set[str]] = defaultdict(set)
        for row in self.rows:
            days[row["timestamp"][:10]].add(row["tamb_c"])
        self.assertEqual(
            {day: sorted(temps) for day, temps in sorted(days.items())},
            {
                "2026-09-14": ["25.0"],
                "2026-09-15": ["70.0"],
                "2026-09-16": ["0.0"],
            },
        )

    def test_the_readings_are_quantized_to_the_range_they_were_taken_on(self) -> None:
        """A reading on the 100 V range lands on 100 uV steps, and it shows in the file."""
        for row in self.rows:
            digits = row["vout_v"].split(".")[1]
            self.assertEqual(len(digits), 5, row)
            if row["meter_range_v"] == f"{SLIPPED_RANGE_V:.1f}":
                self.assertEqual(digits[-1], "0", row)


class TestStoryOneThinMarginAtOneCorner(unittest.TestCase):
    """One board holds a fifth of the margin the others hold, at one corner, and passes anyway."""

    def setUp(self) -> None:
        self.rows = read()
        self.corner_margins = {
            serial: margin_to_limit(
                mean_at(self.rows, serial, "70.0", "9.0", "3.000"), VOUT_MIN_V, side="lower"
            )
            for serial in sorted({r["serial"] for r in self.rows})
        }

    def test_the_worst_corner_is_hot_low_line_and_full_load(self) -> None:
        worst = min(
            (
                (mean_at(self.rows, THIN_MARGIN_SERIAL, tamb, vin, iout), tamb, vin, iout)
                for tamb in ("0.0", "25.0", "70.0")
                for vin in ("9.0", "12.0", "24.0", "32.0")
                for iout in ("0.100", "1.000", "3.000")
            )
        )
        self.assertEqual(worst[1:], ("70.0", "9.0", "3.000"))

    def test_one_board_holds_about_twenty_millivolts_where_the_others_hold_sixty_to_eighty(self) -> None:
        thin = self.corner_margins.pop(THIN_MARGIN_SERIAL)
        self.assertAlmostEqual(1000.0 * thin, 20.4, delta=0.2)
        for serial, margin in self.corner_margins.items():
            self.assertGreater(1000.0 * margin, 58.0, serial)
            self.assertLess(1000.0 * margin, 79.0, serial)
        self.assertLess(thin / min(self.corner_margins.values()), 0.36)

    def test_it_passes_everywhere_all_the_same(self) -> None:
        """Every board, every corner, inside the datasheet's own window, by more than the
        measurement is worth. Nothing in this file is a failing board."""
        for point, readings in by_point(self.rows).items():
            value = statistics.fmean(float(r["vout_v"]) for r in readings)
            self.assertEqual(
                guarded_verdict(value, U_VOUT_V, lower=VOUT_MIN_V, upper=VOUT_MAX_V),
                VERDICT_PASS,
                point,
            )

    def test_no_single_parameter_of_that_board_is_out_of_specification(self) -> None:
        """The lesson: three parameters each inside its own limit, stacked at one corner."""
        for tamb in ("0.0", "25.0", "70.0"):
            self.assertLess(line_regulation_pct(self.rows, THIN_MARGIN_SERIAL, tamb), LINE_REG_MAX_PCT)
            self.assertLess(load_regulation_pct(self.rows, THIN_MARGIN_SERIAL, tamb), LOAD_REG_MAX_PCT)
        # and it is the worst of the five on both, without being over on either
        for measure in (line_regulation_pct, load_regulation_pct):
            worst = max(
                {r["serial"] for r in self.rows},
                key=lambda serial: measure(self.rows, serial, "70.0"),
            )
            self.assertIn(worst, (THIN_MARGIN_SERIAL, MARGINAL_LINE_SERIAL))
        self.assertGreater(
            load_regulation_pct(self.rows, THIN_MARGIN_SERIAL, "70.0"),
            max(
                load_regulation_pct(self.rows, serial, "70.0")
                for serial in {r["serial"] for r in self.rows}
                if serial != THIN_MARGIN_SERIAL
            ),
        )

    def test_the_margin_is_a_finding_and_not_a_measurement_artifact(self) -> None:
        """20 mV against an expanded uncertainty of 0.35 mV: the measurement decides this one."""
        thin = margin_to_limit(
            mean_at(self.rows, THIN_MARGIN_SERIAL, "70.0", "9.0", "3.000"),
            VOUT_MIN_V,
            side="lower",
        )
        self.assertGreater(thin / U_VOUT_V, 50.0)

    def test_a_sample_of_one_typical_board_would_have_missed_it(self) -> None:
        """The argument for characterizing five boards instead of the golden one."""
        typical = [
            1000.0 * margin
            for serial, margin in self.corner_margins.items()
            if serial != THIN_MARGIN_SERIAL
        ]
        self.assertGreater(statistics.fmean(typical), 60.0)


class TestStoryTwoAMarginSmallerThanTheUncertainty(unittest.TestCase):
    """One figure inside its limit by less than the measurement is worth: cannot say."""

    def setUp(self) -> None:
        self.rows = read()
        self.line_reg = {
            tamb: line_regulation_pct(self.rows, MARGINAL_LINE_SERIAL, tamb)
            for tamb in ("0.0", "25.0", "70.0")
        }

    def test_the_three_verdicts_at_the_three_ambients(self) -> None:
        verdicts = {
            tamb: guarded_verdict(value, U_REG_PCT, upper=LINE_REG_MAX_PCT)
            for tamb, value in self.line_reg.items()
        }
        self.assertEqual(
            verdicts, {"0.0": VERDICT_PASS, "25.0": VERDICT_UNKNOWN, "70.0": VERDICT_FAIL}
        )

    def test_the_figures_the_notebook_quotes(self) -> None:
        # characterization-notebook.md section 5: 0.267, 0.299 and 0.334 percent.
        self.assertAlmostEqual(self.line_reg["0.0"], 0.267, places=3)
        self.assertAlmostEqual(self.line_reg["25.0"], 0.299, places=3)
        self.assertAlmostEqual(self.line_reg["70.0"], 0.334, places=3)

    def test_the_margin_at_twenty_five_degrees_is_smaller_than_the_uncertainty(self) -> None:
        margin = margin_to_limit(self.line_reg["25.0"], LINE_REG_MAX_PCT, side="upper")
        self.assertGreater(margin, 0.0)  # inside the limit
        self.assertLess(margin, U_REG_PCT)  # and not shown to be inside it
        self.assertAlmostEqual(margin, 0.0006, places=4)

    def test_the_uncertainty_on_a_regulation_figure_is_the_one_the_notebook_derives(self) -> None:
        """A difference of two readings through the same leads: the lead line drops out."""
        readings = [
            float(r["vout_v"])
            for r in self.rows
            if r["serial"] == MARGINAL_LINE_SERIAL
            and r["tamb_c"] == "25.0"
            and r["vin_v"] == "32.0"
            and r["iout_a"] == "1.000"
        ]
        per_reading = combined_uncertainty(
            dc_voltage_budget(readings, range_v=NOMINAL_RANGE_V, lead_half_width_v=None)
        )
        difference = expanded_uncertainty(per_reading * math.sqrt(2.0))
        self.assertAlmostEqual(100.0 * difference / 5.000, U_REG_PCT, delta=0.0015)

    def test_leaving_the_uncertainty_out_would_have_called_it_a_pass(self) -> None:
        """What a production-style limit check does with the same number, and why it is wrong
        here: 0.299 is under 0.300, so the comparison passes and says nothing true."""
        self.assertLess(self.line_reg["25.0"], LINE_REG_MAX_PCT)
        self.assertEqual(
            guarded_verdict(self.line_reg["25.0"], 0.0, upper=LINE_REG_MAX_PCT), VERDICT_PASS
        )

    def test_it_is_one_board_and_not_a_property_of_the_design(self) -> None:
        for serial in sorted({r["serial"] for r in self.rows}):
            if serial == MARGINAL_LINE_SERIAL:
                continue
            for tamb in ("0.0", "25.0", "70.0"):
                value = line_regulation_pct(self.rows, serial, tamb)
                self.assertEqual(
                    guarded_verdict(value, U_REG_PCT, upper=LINE_REG_MAX_PCT),
                    VERDICT_PASS,
                    f"{serial} at {tamb}",
                )


class TestStoryThreeScatterFollowsTheRange(unittest.TestCase):
    """Sixty noisy readings that belong to the meter's range and to nothing else."""

    def setUp(self) -> None:
        self.rows = read()
        self.spreads = {
            point: statistics.stdev([float(r["vout_v"]) for r in readings])
            for point, readings in by_point(self.rows).items()
        }
        self.range_of = {
            point: {r["meter_range_v"] for r in readings}
            for point, readings in by_point(self.rows).items()
        }

    def slipped(self) -> list[dict[str, str]]:
        return [r for r in self.rows if r["meter_range_v"] == f"{SLIPPED_RANGE_V:.1f}"]

    def test_sixty_readings_were_taken_on_the_wrong_range(self) -> None:
        self.assertEqual(len(self.slipped()), 60)
        self.assertEqual(
            {r["meter_range_v"] for r in self.rows},
            {f"{NOMINAL_RANGE_V:.1f}", f"{SLIPPED_RANGE_V:.1f}"},
        )

    def test_every_point_was_taken_entirely_on_one_range(self) -> None:
        for point, ranges in self.range_of.items():
            self.assertEqual(len(ranges), 1, point)

    def test_the_scatter_is_seven_times_larger_and_does_not_overlap(self) -> None:
        slipped = [s for p, s in self.spreads.items() if self.range_of[p] == {"100.0"}]
        normal = [s for p, s in self.spreads.items() if self.range_of[p] == {"10.0"}]
        self.assertGreater(statistics.fmean(slipped) / statistics.fmean(normal), 5.0)
        self.assertGreater(min(slipped), max(normal))

    def test_it_is_not_a_board(self) -> None:
        """Two boards are affected and each only partly, which is what rules the boards out."""
        affected = {r["serial"] for r in self.slipped()}
        self.assertEqual(len(affected), 2)
        for serial in affected:
            on_ten = [
                r
                for r in self.rows
                if r["serial"] == serial and r["meter_range_v"] == f"{NOMINAL_RANGE_V:.1f}"
            ]
            self.assertTrue(on_ten, serial)
        # and with the slipped rows removed, no board is noisier than any other
        per_board: dict[str, list[float]] = defaultdict(list)
        for point, spread in self.spreads.items():
            if self.range_of[point] == {"10.0"}:
                per_board[point[0]].append(spread)
        means = {serial: statistics.fmean(v) for serial, v in per_board.items()}
        self.assertLess(max(means.values()) / min(means.values()), 1.3)

    def test_it_is_not_a_corner_and_not_a_temperature(self) -> None:
        affected_corners = {(r["vin_v"], r["iout_a"]) for r in self.slipped()}
        self.assertEqual(len(affected_corners), 12)  # every corner of two boards, not one corner
        self.assertEqual({r["tamb_c"] for r in self.slipped()}, {"25.0"})
        per_ambient: dict[str, list[float]] = defaultdict(list)
        for point, spread in self.spreads.items():
            if self.range_of[point] == {"10.0"}:
                per_ambient[point[1]].append(spread)
        means = {tamb: statistics.fmean(v) for tamb, v in per_ambient.items()}
        self.assertLess(max(means.values()) / min(means.values()), 1.3)

    def test_it_is_not_settling_either(self) -> None:
        """A settling problem walks: the first reading of a point sits apart from the last. This
        does not, so a longer delay was never going to fix it."""
        firsts, lasts = [], []
        for readings in by_point(self.rows).values():
            if readings[0]["meter_range_v"] != f"{SLIPPED_RANGE_V:.1f}":
                continue
            firsts.append(float(readings[0]["vout_v"]))
            lasts.append(float(readings[-1]["vout_v"]))
        walk = statistics.fmean(lasts) - statistics.fmean(firsts)
        scatter = statistics.fmean(
            spread for point, spread in self.spreads.items() if self.range_of[point] == {"100.0"}
        )
        self.assertLess(abs(walk), scatter)

    def test_the_wrong_range_costs_what_the_meter_s_own_table_says(self) -> None:
        """The scatter is the visible half. The specification is the other half, and it is
        bigger: a reading on the 100 V range is worth about a third of one on the 10 V range."""
        readings = [float(r["vout_v"]) for r in self.slipped()[:REPEATS]]
        wrong = expanded_uncertainty(
            combined_uncertainty(dc_voltage_budget(readings, range_v=SLIPPED_RANGE_V))
        )
        right = expanded_uncertainty(
            combined_uncertainty(dc_voltage_budget(readings, range_v=NOMINAL_RANGE_V))
        )
        # 2.4 with these readings. Not the 3.7 of the accuracy rows alone, because the
        # repeatability and lead lines are the same in both budgets and only the meter and
        # resolution lines move.
        self.assertGreater(wrong / right, 2.3)
        self.assertLess(wrong / right, 2.5)


class TestStoryFourAPointRecordedAtTheWrongCondition(unittest.TestCase):
    """One block says 12.0 V. The input current says 24.0 V."""

    def setUp(self) -> None:
        self.rows = read()
        _, self.serial, self.vin, self.iout = WRONG_CONDITION
        self.suspect = [
            r
            for r in self.rows
            if r["serial"] == self.serial
            and r["tamb_c"] == "25.0"
            and r["vin_v"] == f"{self.vin:.1f}"
            and r["iout_a"] == f"{self.iout:.3f}"
        ]

    def peers(self) -> list[dict[str, str]]:
        return [
            r
            for r in self.rows
            if r["serial"] != self.serial
            and r["vin_v"] == f"{self.vin:.1f}"
            and r["iout_a"] == f"{self.iout:.3f}"
            and r["tamb_c"] == "25.0"
        ]

    def test_the_output_voltage_gives_nothing_away(self) -> None:
        """Holding the output steady while the input moves is the entire job of the part.

        Two comparisons, on the same board so no board-to-board difference muddies them. The
        suspect block sits within a few tenths of a millivolt of this board's own 24.0 V block,
        which is what it really is. And a genuine 12.0 V reading would have differed from a
        24.0 V one by about 3 mV anyway, so even a correct block would not have looked obviously
        different. The output voltage cannot find this. The input current can.
        """
        suspect = statistics.fmean(float(r["vout_v"]) for r in self.suspect)
        same_board_24 = mean_at(self.rows, self.serial, "25.0", "24.0", "3.000")
        self.assertLess(abs(suspect - same_board_24), 0.0006)
        genuine_step = statistics.fmean(
            mean_at(self.rows, serial, "25.0", "24.0", "3.000")
            - mean_at(self.rows, serial, "25.0", "12.0", "3.000")
            for serial in sorted({r["serial"] for r in self.rows})
            if serial != self.serial
        )
        self.assertLess(abs(genuine_step), 0.005)

    def test_the_input_current_halves(self) -> None:
        suspect = statistics.fmean(float(r["iin_a"]) for r in self.suspect)
        peers = statistics.fmean(float(r["iin_a"]) for r in self.peers())
        self.assertAlmostEqual(suspect, 0.673, places=2)
        self.assertAlmostEqual(peers, 1.312, places=2)
        self.assertAlmostEqual(peers / suspect, WRONG_CONDITION_ACTUAL_VIN_V / self.vin, delta=0.05)

    def test_the_power_balance_is_what_finds_it(self) -> None:
        """Input power should be a little more than output power. Read at the labeled 12.0 V it
        is less, which is the check: a board cannot put out more than it takes in."""
        pin = self.vin * statistics.fmean(float(r["iin_a"]) for r in self.suspect)
        pout = self.iout * statistics.fmean(float(r["vout_v"]) for r in self.suspect)
        self.assertLess(pin, pout)
        # and at the voltage it was really taken at, the balance is ordinary again
        real_pin = WRONG_CONDITION_ACTUAL_VIN_V * statistics.fmean(
            float(r["iin_a"]) for r in self.suspect
        )
        self.assertGreater(real_pin, pout)
        self.assertLess(100.0 * pout / real_pin, 100.0)
        self.assertGreater(100.0 * pout / real_pin, 88.0)

    def test_it_is_exactly_one_point_and_the_rest_of_the_file_is_sound(self) -> None:
        odd = []
        for point, readings in by_point(self.rows).items():
            vin = float(point[2])
            iout = float(point[3])
            pin = vin * statistics.fmean(float(r["iin_a"]) for r in readings)
            pout = iout * statistics.fmean(float(r["vout_v"]) for r in readings)
            if pin <= pout:
                odd.append(point)
        self.assertEqual(len(odd), 1)
        self.assertEqual(odd[0][0], self.serial)
        self.assertEqual(odd[0][2], f"{self.vin:.1f}")

    def test_a_budget_would_not_have_caught_it(self) -> None:
        """The wrong condition is not an uncertainty problem. Every reading in that block is a
        good reading of something nobody asked for, and no amount of averaging finds it."""
        readings = [float(r["vout_v"]) for r in self.suspect]
        budget = dc_voltage_budget(readings, range_v=NOMINAL_RANGE_V)
        self.assertLess(expanded_uncertainty(combined_uncertainty(budget)), 500e-6)
        self.assertIsInstance(budget[0], Contribution)


if __name__ == "__main__":
    unittest.main()
