"""The bench data reproduces byte for byte, and every story in it is really there.

`docs/THE-BENCH.md` is the answer key. A page that teaches a reader to find the marginal lot by
grouping ripple by lot is only honest if the marginal lot is in the file, so each of the six
stories gets a test that finds it the same way the page tells a reader to find it: by grouping, by
reading a run chart, or by noticing the magnitude of a number.

The reproducibility test matters for a different reason. The CSVs are committed, and a reader may
reasonably assume the committed bytes are what the script writes. If a Python version, a platform
or an edit to the generator changed a single digit, every number quoted on every engineering page
would quietly stop matching the file the reader downloads.
"""
from __future__ import annotations

import csv
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

from evals.bench import BENCH_DATA_DIR, PRODUCTION_CSV, RETEST_CSV, SOAK_CSV  # noqa: E402
from evals.bench.make_data import (  # noqa: E402
    FIXTURE_OFFSET_V,
    MARGINAL_LOT,
    MIXED_UP_LOT,
    MIXED_UP_SERIAL,
    OFFSET_FIXTURE,
    SOAK_DRIFTER,
    STEPS,
    generate,
)

FILES = ("production-run-2026-08.csv", "soak-2026-08-27.csv", "retest-2026-08-31.csv")


def read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def one_sided_cpk(values: list[float], upper: float) -> float:
    """(USL - mean) / (3 * sigma), the standard one-sided capability index."""
    return (upper - statistics.fmean(values)) / (3.0 * statistics.stdev(values))


class TestReproducible(unittest.TestCase):
    def test_the_script_reproduces_the_committed_files_byte_for_byte(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            generate(Path(tmp))
            for name in FILES:
                self.assertEqual(
                    (Path(tmp) / name).read_bytes(),
                    (BENCH_DATA_DIR / name).read_bytes(),
                    name,
                )

    def test_the_script_reproduces_them_from_a_fresh_interpreter_too(self) -> None:
        """A seed that depends on interpreter state would pass the test above and not this one."""
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, "-m", "evals.bench.make_data", tmp],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            for name in FILES:
                self.assertEqual(
                    (Path(tmp) / name).read_bytes(), (BENCH_DATA_DIR / name).read_bytes(), name
                )

    def test_line_endings_are_lf(self) -> None:
        for name in FILES:
            raw = (BENCH_DATA_DIR / name).read_bytes()
            self.assertNotIn(b"\r", raw, name)
            self.assertTrue(raw.endswith(b"\n"), name)


class TestProductionLogShape(unittest.TestCase):
    def setUp(self) -> None:
        self.rows = read(PRODUCTION_CSV)

    def test_two_hundred_units(self) -> None:
        self.assertEqual(len({r["serial"] for r in self.rows}), 200)

    def test_eight_steps_per_unit_except_the_two_that_aborted(self) -> None:
        per_unit: dict[str, int] = defaultdict(int)
        for row in self.rows:
            per_unit[row["serial"]] += 1
        counts = sorted(set(per_unit.values()))
        self.assertEqual(counts, [1, 8])
        aborted = [s for s, n in per_unit.items() if n == 1]
        self.assertEqual(len(aborted), 2)
        for serial in aborted:
            step_one = [r for r in self.rows if r["serial"] == serial][0]
            self.assertEqual(step_one["measurement"], "R_OUT")
            self.assertEqual(step_one["result"], "FAIL")

    def test_every_row_carries_its_limits_and_its_unit(self) -> None:
        by_name = {name: (unit, low, high, places) for _, name, unit, low, high, places in STEPS}
        for row in self.rows:
            unit, low, high, places = by_name[row["measurement"]]
            self.assertEqual(row["unit"], unit, row["measurement"])
            self.assertEqual(row["lower_limit"], "" if low is None else f"{low:.{places}f}")
            self.assertEqual(row["upper_limit"], "" if high is None else f"{high:.{places}f}")

    def test_the_result_column_is_the_limit_check_and_nothing_else(self) -> None:
        """Recompute every verdict from the value and the limits. No judgment is involved."""
        for row in self.rows:
            value = float(row["value"])
            low = float(row["lower_limit"]) if row["lower_limit"] else None
            high = float(row["upper_limit"]) if row["upper_limit"] else None
            expected = "PASS"
            if low is not None and value < low:
                expected = "FAIL"
            if high is not None and value > high:
                expected = "FAIL"
            self.assertEqual(row["result"], expected, row)

    def test_lot_and_fixture_are_crossed_not_nested(self) -> None:
        """Each lot sees each fixture, so a lot effect and a fixture effect can be told apart."""
        pairs: dict[str, set[str]] = defaultdict(set)
        counts: dict[tuple[str, str], int] = defaultdict(int)
        for row in self.rows:
            if row["measurement"] != "VOUT":
                continue
            pairs[row["lot"]].add(row["fixture"])
            counts[(row["lot"], row["fixture"])] += 1
        self.assertEqual(len(pairs), 4)
        for lot, fixtures in pairs.items():
            self.assertEqual(len(fixtures), 4, lot)
        # Lots are 52, 52, 48 and 48 units, so a cell holds 12 or 13, less the two units that
        # aborted at step 1 and never reached the VOUT step.
        per_cell = list(counts.values())
        self.assertEqual(len(per_cell), 16)
        self.assertLessEqual(max(per_cell) - min(per_cell), 2)

    def test_days_and_shifts_are_recorded(self) -> None:
        days = {r["timestamp"][:10] for r in self.rows}
        self.assertEqual(days, {"2026-08-24", "2026-08-25", "2026-08-26", "2026-08-27"})
        self.assertEqual({r["shift"] for r in self.rows}, {"A", "B"})

    def test_first_pass_yield(self) -> None:
        failed = {r["serial"] for r in self.rows if r["result"] == "FAIL"}
        self.assertEqual(len(failed), 16)
        self.assertAlmostEqual(100.0 * (200 - len(failed)) / 200, 92.0, places=1)


class TestStoryOneMarginalLot(unittest.TestCase):
    """Grouping ripple by lot finds one lot with a shifted mean and a bad capability index."""

    def setUp(self) -> None:
        self.by_lot: dict[str, list[float]] = defaultdict(list)
        for row in read(PRODUCTION_CSV):
            if row["measurement"] == "RIPPLE":
                self.by_lot[row["lot"]].append(float(row["value"]))

    def test_one_lot_has_a_shifted_mean(self) -> None:
        means = {lot: statistics.fmean(v) for lot, v in self.by_lot.items()}
        marginal = means.pop(MARGINAL_LOT)
        self.assertGreater(marginal, 40.0)
        for lot, mean in means.items():
            self.assertLess(mean, 25.0, lot)
        self.assertGreater(marginal / max(means.values()), 1.8)

    def test_the_marginal_lot_is_not_capable_and_the_others_are(self) -> None:
        cpks = {lot: one_sided_cpk(v, 50.0) for lot, v in self.by_lot.items()}
        self.assertLess(cpks[MARGINAL_LOT], 1.0)
        for lot, cpk in cpks.items():
            if lot != MARGINAL_LOT:
                self.assertGreater(cpk, 1.33, lot)

    def test_it_is_mostly_passing(self) -> None:
        values = self.by_lot[MARGINAL_LOT]
        failures = [v for v in values if v > 50.0]
        self.assertGreaterEqual(len(failures), 2)
        self.assertLess(len(failures) / len(values), 0.15)

    def test_every_ripple_failure_is_in_that_lot(self) -> None:
        for lot, values in self.by_lot.items():
            if lot != MARGINAL_LOT:
                self.assertEqual([v for v in values if v > 50.0], [], lot)

    def test_yield_alone_would_not_have_found_it(self) -> None:
        """The argument for charting measurements rather than counting failures."""
        rows = read(PRODUCTION_CSV)
        passed: dict[str, set[str]] = defaultdict(set)
        failed: dict[str, set[str]] = defaultdict(set)
        for row in rows:
            (failed if row["result"] == "FAIL" else passed)[row["lot"]].add(row["serial"])
        yields = {}
        for lot in passed:
            units = passed[lot] | failed[lot]
            yields[lot] = 100.0 * (len(units) - len(failed[lot])) / len(units)
        self.assertGreater(yields[MARGINAL_LOT], min(yields.values()))


class TestStoryTwoFixtureOffset(unittest.TestCase):
    """One fixture reads low on one step, and only on that step."""

    def setUp(self) -> None:
        self.rows = read(PRODUCTION_CSV)

    def vout_by_fixture(self) -> dict[str, list[float]]:
        out: dict[str, list[float]] = defaultdict(list)
        for row in self.rows:
            if row["measurement"] == "VOUT" and float(row["value"]) > 1.0:
                out[row["fixture"]].append(float(row["value"]))
        return out

    def test_one_fixture_reads_low_by_the_offset(self) -> None:
        means = {f: statistics.fmean(v) for f, v in self.vout_by_fixture().items()}
        suspect = means.pop(OFFSET_FIXTURE)
        others = statistics.fmean(list(means.values()))
        self.assertAlmostEqual(suspect - others, FIXTURE_OFFSET_V, delta=0.006)
        self.assertLess(max(means.values()) - min(means.values()), abs(FIXTURE_OFFSET_V) / 5)

    def test_the_spread_did_not_change_only_the_mean(self) -> None:
        spreads = {f: statistics.stdev(v) for f, v in self.vout_by_fixture().items()}
        self.assertLess(max(spreads.values()) / min(spreads.values()), 1.5)

    def test_most_of_the_vout_failures_are_on_that_fixture(self) -> None:
        failures = [
            r for r in self.rows
            if r["measurement"] == "VOUT" and r["result"] == "FAIL" and float(r["value"]) > 1.0
        ]
        on_fixture = [r for r in failures if r["fixture"] == OFFSET_FIXTURE]
        self.assertGreaterEqual(len(on_fixture), 4)
        self.assertGreater(len(on_fixture) / len(failures), 0.6)

    def test_the_offset_does_not_move_the_regulation_steps(self) -> None:
        """A fixed offset cancels in a difference, which is why exactly one step moved.

        Each threshold is a tenth of what a 30 mV offset would do to that measurement if it did
        not cancel: 0.6 percentage points on either regulation figure (30 mV over the 5.000 V the
        percentage is taken against) and about 0.55 on efficiency.
        """
        for measurement, would_be in (("LINE_REG", 0.60), ("LOAD_REG", 0.60), ("EFF_FL", 0.55)):
            by_fixture: dict[str, list[float]] = defaultdict(list)
            for row in self.rows:
                if row["measurement"] == measurement and float(row["value"]) > 0.05:
                    by_fixture[row["fixture"]].append(float(row["value"]))
            # The median, not the mean: one genuinely defective board reads 79.6% efficiency,
            # and a mean would report that one unit as a property of the fixture it sat on.
            centers = {f: statistics.median(v) for f, v in by_fixture.items()}
            suspect = centers.pop(OFFSET_FIXTURE)
            moved = abs(suspect - statistics.median(list(centers.values())))
            self.assertLess(moved, would_be / 5.0, f"{measurement}: {suspect} vs {centers}")

    def test_grouping_by_day_and_by_shift_finds_nothing(self) -> None:
        """Being able to rule a grouping out is half of what the grouping is for."""
        for key in ("shift", "day"):
            groups: dict[str, list[float]] = defaultdict(list)
            for row in self.rows:
                if row["measurement"] == "VOUT" and float(row["value"]) > 1.0:
                    label = row["timestamp"][:10] if key == "day" else row["shift"]
                    groups[label].append(float(row["value"]))
            means = [statistics.fmean(v) for v in groups.values()]
            self.assertLess(max(means) - min(means), 0.006, key)


class TestStoryThreeSoakDrift(unittest.TestCase):
    def setUp(self) -> None:
        self.rows = read(SOAK_CSV)

    def test_three_units_sampled_every_five_minutes_for_ninety(self) -> None:
        serials = {r["serial"] for r in self.rows}
        self.assertEqual(len(serials), 3)
        for serial in serials:
            minutes = [int(r["elapsed_min"]) for r in self.rows if r["serial"] == serial]
            self.assertEqual(minutes, list(range(0, 95, 5)))

    def test_one_unit_drifts_and_the_others_do_not(self) -> None:
        drops = {}
        for serial in sorted({r["serial"] for r in self.rows}):
            points = [r for r in self.rows if r["serial"] == serial]
            drops[serial] = float(points[0]["vout_v"]) - float(points[-1]["vout_v"])
        drifter = drops.pop(SOAK_DRIFTER)
        self.assertGreater(drifter, 0.050)
        for serial, drop in drops.items():
            self.assertLess(drop, 0.005, serial)

    def test_the_drifting_unit_never_settles_thermally(self) -> None:
        for serial in sorted({r["serial"] for r in self.rows}):
            points = [r for r in self.rows if r["serial"] == serial]
            last_half_hour = float(points[-1]["tcase_c"]) - float(points[-7]["tcase_c"])
            if serial == SOAK_DRIFTER:
                self.assertGreater(last_half_hour, 4.0)
                self.assertGreater(float(points[-1]["tcase_c"]), 85.0)
            else:
                self.assertLess(last_half_hour, 1.0, serial)

    def test_the_drifting_unit_is_the_one_that_failed_efficiency(self) -> None:
        """One defect, two symptoms: a resistive joint heats, and a hot joint is more resistive."""
        failures = [
            r for r in read(PRODUCTION_CSV)
            if r["measurement"] == "EFF_FL" and r["result"] == "FAIL" and float(r["value"]) > 1.0
        ]
        self.assertEqual([r["serial"] for r in failures], [SOAK_DRIFTER])


class TestStoryFourMillivoltsUnderAVoltHeader(unittest.TestCase):
    def setUp(self) -> None:
        self.rows = read(RETEST_CSV)

    def test_the_column_says_volts(self) -> None:
        self.assertIn("value_v", self.rows[0])

    def test_the_values_are_millivolts(self) -> None:
        live = [float(r["value_v"]) for r in self.rows if abs(float(r["value_v"])) > 100.0]
        self.assertGreater(len(live), 10)
        for value in live:
            self.assertGreater(value, 4000.0)
            self.assertLess(value, 6000.0)

    def test_read_literally_the_file_is_absurd(self) -> None:
        """The trap: as volts, every retested unit clears a 4.95 V lower limit a thousand-fold."""
        as_volts = [float(r["value_v"]) for r in self.rows if float(r["value_v"]) > 100.0]
        self.assertTrue(all(v > 4.950 for v in as_volts))
        as_millivolts = [v / 1000.0 for v in as_volts]
        self.assertTrue(all(4.90 < v < 5.10 for v in as_millivolts))

    def test_the_retest_clears_the_units_the_fixture_failed(self) -> None:
        production = {
            r["serial"]: r for r in read(PRODUCTION_CSV)
            if r["measurement"] == "VOUT" and r["result"] == "FAIL"
        }
        cleared = 0
        for row in self.rows:
            original = production.get(row["serial"])
            if original and original["fixture"] == OFFSET_FIXTURE and row["result"] == "PASS":
                cleared += 1
        self.assertGreaterEqual(cleared, 4)


class TestStoryFiveUnitMixUp(unittest.TestCase):
    def test_one_serial_is_filed_under_a_lot_it_is_not_in(self) -> None:
        production = {
            r["serial"]: r["lot"] for r in read(PRODUCTION_CSV) if r["measurement"] == "VOUT"
        }
        wrong = [
            r for r in read(RETEST_CSV)
            if r["serial"] in production and production[r["serial"]] != r["lot"]
        ]
        self.assertEqual(len(wrong), 1)
        self.assertEqual(wrong[0]["serial"], MIXED_UP_SERIAL)
        self.assertEqual(wrong[0]["lot"], MIXED_UP_LOT)
        self.assertNotEqual(production[MIXED_UP_SERIAL], MIXED_UP_LOT)


class TestStorySixOperatorNotes(unittest.TestCase):
    def setUp(self) -> None:
        self.rows = read(PRODUCTION_CSV)
        self.notes = [r for r in self.rows if r["notes"]]

    def test_there_are_some_notes_and_most_failures_have_none(self) -> None:
        self.assertGreaterEqual(len(self.notes), 12)
        failures = [r for r in self.rows if r["result"] == "FAIL"]
        annotated = [r for r in failures if r["notes"]]
        self.assertLess(len(annotated) / len(failures), 1.0)

    def test_notes_vary_in_quality(self) -> None:
        texts = [r["notes"] for r in self.notes]
        self.assertTrue(any(len(t) > 40 for t in texts), "no detailed note")
        self.assertTrue(any(len(t) <= 8 for t in texts), "no near-empty note")
        self.assertIn("?", texts)

    def test_some_notes_sit_on_passing_rows(self) -> None:
        self.assertTrue(any(r["result"] == "PASS" for r in self.notes))

    def test_a_note_names_a_fixture_informally(self) -> None:
        texts = " | ".join(r["notes"].lower() for r in self.notes)
        self.assertIn("fix3", texts)
        self.assertNotIn("fix-03", texts)

    def test_a_note_on_a_passing_row_is_about_another_measurement(self) -> None:
        stray = [r for r in self.notes if r["result"] == "PASS" and "ripple" in r["notes"]]
        self.assertTrue(stray)
        self.assertNotEqual(stray[0]["measurement"], "RIPPLE")


if __name__ == "__main__":
    unittest.main()
