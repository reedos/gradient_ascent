"""Tests for examples/bench_accuracy_specs_from_the_manual: extract the MDN-6100's DC volts
accuracy table from its programming manual, validate it, hold it for a person's row-by-row check,
and price a reading from the confirmed table.

`GOOD_ROWS` is built from `examples.common.bench.MDN6100_DC_ACCURACY`, the table
`tests/test_bench.py` already proves matches `mdn6100-programming-manual.md` section 2, so the
"clean extraction" fixture here can never drift from that table by hand. `BAD_ROWS` is the same
15 rows with one planted mistake: the 10 V, 1 year row holds the 100 V, 1 year row's numbers
instead of its own. `_validate_table` is expected to accept it, because nothing about shape,
completeness or monotonicity is wrong with it; the tests below prove that, then prove a person's
row-by-row check against the manual is what actually catches it.
"""
from __future__ import annotations

import copy
import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.bench import load_bench_sections  # noqa: E402
from examples.bench_accuracy_specs_from_the_manual.run import (  # noqa: E402
    INTERVALS,
    LEVEL,
    RANGES_V,
    SAMPLE_INPUT,
    SECTION_ID,
    RowsNotConfirmed,
    _rows_to_table,
    _validate_table,
    confirm_table,
    interval_for_calibration,
    price_reading,
    run,
)
from examples.common.bench import MDN6100_DC_ACCURACY, AccuracySpec  # noqa: E402
from examples.common.model import StubModel, StubResponse  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402


def _row_dict(spec: AccuracySpec) -> dict:
    return {
        "range_value": spec.range_value,
        "interval": spec.interval,
        "ppm_of_reading": spec.ppm_of_reading,
        "ppm_of_range": spec.ppm_of_range,
        "tempco_ppm_of_reading_per_c": spec.tempco_ppm_of_reading_per_c,
        "tempco_ppm_of_range_per_c": spec.tempco_ppm_of_range_per_c,
    }


#: The manual's real 15 rows, read out of the table `tests/test_bench.py` already checks against
#: `mdn6100-programming-manual.md` section 2. This is what a correct extraction looks like.
GOOD_ROWS = [
    _row_dict(MDN6100_DC_ACCURACY[interval][range_value])
    for interval in INTERVALS
    for range_value in RANGES_V
]

#: The same 15 rows, except the 10 V, 1 year row has been overwritten with the 100 V, 1 year
#: row's ppm numbers: a plausible one-row slip reading a five-column manual table. The range
#: field still correctly says 10.0; only the two ppm numbers are wrong.
BAD_ROWS = copy.deepcopy(GOOD_ROWS)
_donor = MDN6100_DC_ACCURACY["1 year"][100.0]
for _row in BAD_ROWS:
    if _row["interval"] == "1 year" and _row["range_value"] == 10.0:
        _row["ppm_of_reading"] = _donor.ppm_of_reading
        _row["ppm_of_range"] = _donor.ppm_of_range


def _tracer() -> Tracer:
    return Tracer(example="bench_accuracy_specs_from_the_manual", level=LEVEL, model_id="stub-1")


def _good_model() -> StubModel:
    return StubModel([StubResponse(text=json.dumps(GOOD_ROWS))])


def _bad_model() -> StubModel:
    return StubModel([StubResponse(text=json.dumps(BAD_ROWS))])


class ValidateTableTests(unittest.TestCase):
    def test_the_real_table_validates(self) -> None:
        self.assertEqual(_validate_table(GOOD_ROWS), [])

    def test_the_planted_row_also_validates(self) -> None:
        # The whole point of the recipe: a row copied from the next range up is still shaped
        # right, still the only row for its (interval, range) slot, and still increases from the
        # 24 hour row to the 1 year row, because a range's own numbers usually increase with the
        # range too -- the same direction monotonicity already expects.
        self.assertEqual(_validate_table(BAD_ROWS), [])

    def test_not_a_list_is_rejected(self) -> None:
        self.assertEqual(_validate_table({"not": "a list"}), ["the extraction must be a JSON array of rows"])

    def test_a_missing_row_is_reported(self) -> None:
        problems = _validate_table(GOOD_ROWS[1:])  # drop the first row
        self.assertTrue(any("missing rows" in p for p in problems))

    def test_a_duplicate_row_is_reported(self) -> None:
        problems = _validate_table(GOOD_ROWS + [GOOD_ROWS[0]])
        self.assertTrue(any("duplicate row" in p for p in problems))

    def test_an_unknown_interval_is_reported(self) -> None:
        bad = copy.deepcopy(GOOD_ROWS)
        bad[0]["interval"] = "6 month"
        problems = _validate_table(bad)
        self.assertTrue(any("interval must be one of" in p for p in problems))

    def test_an_unknown_range_is_reported(self) -> None:
        bad = copy.deepcopy(GOOD_ROWS)
        bad[0]["range_value"] = 5.0
        problems = _validate_table(bad)
        self.assertTrue(any("range_value must be one of" in p for p in problems))

    def test_a_negative_ppm_is_reported(self) -> None:
        bad = copy.deepcopy(GOOD_ROWS)
        bad[0]["ppm_of_reading"] = -1.0
        problems = _validate_table(bad)
        self.assertTrue(any("ppm_of_reading must be a non-negative number" in p for p in problems))

    def test_a_non_numeric_field_is_reported(self) -> None:
        bad = copy.deepcopy(GOOD_ROWS)
        bad[0]["ppm_of_range"] = "3"
        problems = _validate_table(bad)
        self.assertTrue(any("ppm_of_range must be a non-negative number" in p for p in problems))

    def test_a_row_that_gets_tighter_with_a_longer_interval_is_reported(self) -> None:
        # Unlike the planted row above, swapping two intervals' worth of data for the SAME range
        # does break the increasing sequence, and this is the check that catches it.
        bad = copy.deepcopy(GOOD_ROWS)
        by_key = {(r["interval"], r["range_value"]): r for r in bad}
        hour24, year1 = by_key[("24 hour", 10.0)], by_key[("1 year", 10.0)]
        hour24["ppm_of_reading"], year1["ppm_of_reading"] = year1["ppm_of_reading"], hour24["ppm_of_reading"]
        problems = _validate_table(bad)
        self.assertTrue(any("does not increase from 24 hour through 1 year" in p for p in problems))


class RowsToTableTests(unittest.TestCase):
    def test_builds_a_real_accuracy_spec_per_row(self) -> None:
        table = _rows_to_table(GOOD_ROWS)
        self.assertEqual(len(table), 15)
        spec = table[("1 year", 10.0)]
        self.assertIsInstance(spec, AccuracySpec)
        self.assertEqual((spec.ppm_of_reading, spec.ppm_of_range), (35.0, 5.0))

    def test_a_24_hour_row_gets_the_narrow_calibration_band(self) -> None:
        from examples.common.bench import CAL_BAND_24H_C

        table = _rows_to_table(GOOD_ROWS)
        self.assertEqual(table[("24 hour", 10.0)].band_c, CAL_BAND_24H_C)


class RunTests(unittest.TestCase):
    def test_an_unknown_section_raises(self) -> None:
        with self.assertRaises(ValueError):
            run("not-a-real-section#1", _good_model(), _tracer())

    def test_a_clean_extraction_returns_all_15_rows(self) -> None:
        tracer = _tracer()
        result = run(SECTION_ID, _good_model(), tracer)
        self.assertEqual(result.section, SECTION_ID)
        self.assertEqual(len(result.rows), 15)
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 1)

    def test_an_invalid_reply_retries_once_then_succeeds(self) -> None:
        model = StubModel([StubResponse(text="not json"), StubResponse(text=json.dumps(GOOD_ROWS))])
        tracer = _tracer()
        result = run(SECTION_ID, model, tracer)
        self.assertEqual(len(result.rows), 15)
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 2)

    def test_still_invalid_after_the_retry_returns_an_empty_proposal(self) -> None:
        # No exception: `record_trace.py`'s generic stub never answers with valid JSON either,
        # and this is the graceful outcome that lets it still record a trace. Nothing downstream
        # may guess at a missing or malformed row, so the proposal it gets back has none.
        model = StubModel([StubResponse(text="not json"), StubResponse(text="still not json")])
        tracer = _tracer()
        result = run(SECTION_ID, model, tracer)
        self.assertEqual(result.rows, {})
        self.assertTrue(any("never validated" in s.title.lower() for s in tracer.steps))

    def test_the_planted_row_extracts_cleanly_with_no_error_raised(self) -> None:
        # Validation cannot tell this apart from a correct table -- see
        # ValidateTableTests.test_the_planted_row_also_validates -- so `run` has no problems to
        # report and returns it as a proposal, same as a genuinely correct table would be.
        tracer = _tracer()
        result = run(SECTION_ID, _bad_model(), tracer)
        bad_row = result.rows[("1 year", 10.0)]
        self.assertEqual((bad_row.ppm_of_reading, bad_row.ppm_of_range), (45.0, 6.0))
        self.assertNotEqual((bad_row.ppm_of_reading, bad_row.ppm_of_range), (35.0, 5.0))

    def test_every_step_is_decided_by_code(self) -> None:
        tracer = _tracer()
        run(SECTION_ID, _good_model(), tracer)
        self.assertTrue(tracer.steps)
        self.assertTrue(all(s.decided_by == "code" for s in tracer.steps), "level 3 must record no model-decided steps")
        self.assertEqual(tracer.model_decided_count(), 0)

    def test_declares_its_level_and_a_run_function(self) -> None:
        self.assertEqual(LEVEL, 3)
        self.assertTrue(callable(run))

    def test_the_recorder_sample_is_a_real_section(self) -> None:
        self.assertEqual(SAMPLE_INPUT, SECTION_ID)
        self.assertIn(SECTION_ID, load_bench_sections())


class ConfirmTableTests(unittest.TestCase):
    def test_an_approved_table_is_returned_for_use(self) -> None:
        tracer = _tracer()
        result = run(SECTION_ID, _good_model(), tracer)
        table = confirm_table(result, True, tracer)
        self.assertEqual(len(table), 15)

    def test_a_rejected_table_raises_and_is_never_returned(self) -> None:
        tracer = _tracer()
        result = run(SECTION_ID, _good_model(), tracer)
        with self.assertRaises(RowsNotConfirmed):
            confirm_table(result, False, tracer, note="did not match the manual")

    def test_a_person_rejects_the_planted_row_after_reading_the_manual(self) -> None:
        # evals/bench/corpus/mdn6100-programming-manual.md section 2 prints 35 + 5 ppm for the
        # 10 V, 1 year row. This table says 45 + 6. Code found nothing wrong with it; this is the
        # check that does.
        tracer = _tracer()
        result = run(SECTION_ID, _bad_model(), tracer)
        bad_row = result.rows[("1 year", 10.0)]
        manual_row = MDN6100_DC_ACCURACY["1 year"][10.0]
        self.assertNotEqual(
            (bad_row.ppm_of_reading, bad_row.ppm_of_range),
            (manual_row.ppm_of_reading, manual_row.ppm_of_range),
        )
        with self.assertRaises(RowsNotConfirmed):
            confirm_table(result, False, tracer, note="10 V/1 year row reads 45+6 ppm; manual says 35+5")

    def test_confirmation_is_recorded_on_the_tracer(self) -> None:
        tracer = _tracer()
        result = run(SECTION_ID, _good_model(), tracer)
        confirm_table(result, True, tracer)
        self.assertTrue(any("confirms" in s.title.lower() for s in tracer.steps))


class IntervalForCalibrationTests(unittest.TestCase):
    def test_just_calibrated_uses_the_24_hour_row(self) -> None:
        self.assertEqual(interval_for_calibration(0.5), "24 hour")

    def test_six_weeks_uses_the_90_day_row(self) -> None:
        self.assertEqual(interval_for_calibration(45.0), "90 day")

    def test_eleven_months_uses_the_1_year_row(self) -> None:
        self.assertEqual(interval_for_calibration(335.0), "1 year")

    def test_a_negative_age_raises(self) -> None:
        with self.assertRaises(ValueError):
            interval_for_calibration(-1.0)


class AccuracyLimitTests(unittest.TestCase):
    """The manual's own two worked mistakes (`mdn6100-programming-manual.md` sections 2 and 8),
    reproduced directly from `AccuracySpec.limit`, with no extraction and no retrieval involved:
    just the right row against the wrong one."""

    def setUp(self) -> None:
        self.table = _rows_to_table(GOOD_ROWS)

    def test_the_true_row_prices_a_4_9930_v_reading_at_224_8_uv(self) -> None:
        limit = self.table[("1 year", 10.0)].limit(4.9930, 23.0)
        self.assertEqual(round(limit * 1e6, 1), 224.8)

    def test_the_24_hour_row_understates_it_at_79_9_uv(self) -> None:
        limit = self.table[("24 hour", 10.0)].limit(4.9930, 23.0)
        self.assertEqual(round(limit * 1e6, 1), 79.9)

    def test_the_100_v_row_overstates_it_at_824_7_uv(self) -> None:
        limit = self.table[("1 year", 100.0)].limit(4.9930, 23.0)
        self.assertEqual(round(limit * 1e6, 1), 824.7)


class PriceReadingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.table = _rows_to_table(GOOD_ROWS)

    def test_matches_the_manuals_worked_budget_line_for_line(self) -> None:
        # mdn6100-programming-manual.md section 8: meter accuracy 129.8 uV, resolution 2.9 uV,
        # for a single reading on the 10 V range, 1 year specification.
        priced = price_reading(self.table, [4.9930], range_v=10.0, days_since_cal=335.0)
        self.assertEqual(priced.interval, "1 year")
        by_name = {c.name: c.standard_uncertainty for c in priced.contributions}
        self.assertEqual(round(by_name["meter accuracy"] * 1e6, 1), 129.8)
        self.assertEqual(round(by_name["resolution"] * 1e6, 1), 2.9)

    def test_repeatability_and_leads_add_their_own_lines(self) -> None:
        readings = [4.9930, 4.9931, 4.9929, 4.9930, 4.9932]
        priced = price_reading(
            self.table, readings, range_v=10.0, days_since_cal=335.0, lead_half_width_v=200e-6,
        )
        names = {c.name for c in priced.contributions}
        self.assertEqual(names, {"meter accuracy", "resolution", "repeatability", "leads and connections"})

    def test_a_table_with_no_row_for_the_key_raises(self) -> None:
        sparse = {k: v for k, v in self.table.items() if k != ("1 year", 10.0)}
        with self.assertRaises(ValueError):
            price_reading(sparse, [4.9930], range_v=10.0, days_since_cal=335.0)

    def test_assuming_a_meter_was_just_calibrated_understates_the_uncertainty(self) -> None:
        # The correct row for a meter calibrated eleven months ago is the 1 year row; assuming
        # the meter was just calibrated instead reaches for the 24 hour row, a real row of a
        # perfectly good table, and reports too small a number for it.
        honest = price_reading(self.table, [4.9930], range_v=10.0, days_since_cal=335.0)
        optimistic = price_reading(self.table, [4.9930], range_v=10.0, days_since_cal=0.5)
        self.assertEqual(optimistic.interval, "24 hour")
        self.assertLess(optimistic.expanded_v, honest.expanded_v)

    def test_naming_the_wrong_range_overstates_the_uncertainty(self) -> None:
        # A 10 V reading priced as though it were taken on the 100 V range reaches for a real
        # row of the same good table and reports too large a number for it.
        honest = price_reading(self.table, [4.9930], range_v=10.0, days_since_cal=335.0)
        pessimistic = price_reading(self.table, [4.9930], range_v=100.0, days_since_cal=335.0)
        self.assertGreater(pessimistic.expanded_v, honest.expanded_v)

    def test_the_planted_row_silently_overstates_a_confirmed_but_wrong_table(self) -> None:
        # Even with every fact right (correct range, correct interval), a table that passed
        # validation but not a person's check still prices this reading wrong: 284.7 uV instead
        # of the true 224.8 uV, from the 45 + 6 ppm the 10 V/1 year slot was not supposed to hold.
        bad_table = _rows_to_table(BAD_ROWS)
        priced = price_reading(bad_table, [4.9930], range_v=10.0, days_since_cal=335.0)
        by_name = {c.name: c.standard_uncertainty for c in priced.contributions}
        limit = by_name["meter accuracy"] * math.sqrt(3.0)
        self.assertEqual(round(limit * 1e6, 1), 284.7)


if __name__ == "__main__":
    unittest.main()
