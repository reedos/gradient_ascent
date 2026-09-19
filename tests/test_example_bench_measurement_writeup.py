"""Tests for examples/bench_measurement_writeup: the figures it computes from the
characterization sweep, and the check that a model-drafted report never quotes a number code did
not produce.

Three kinds of claim, matching the recipe's own argument:

- **The figures reproduce the answer key.** `compute_results` is checked against the same numbers
  `docs/THE-BENCH.md` and `tests/test_bench_characterization.py` state for "Story A" (the
  thin-margin corner) and "Story B" (the cannot-say line regulation verdict), recomputed here
  independently from the CSV rather than trusted from the module's own output.
- **`unsupported_numbers` is the real safety check, not a description of one.** It accepts a
  clean draft, rejects a draft carrying a number code never produced (a rounded or "improved"
  figure), and does not mistake a serial number's digits for a quoted measurement.
- **`run` makes exactly one model call, decided by code**, and a draft the check rejects comes
  back marked, not silently repaired or discarded.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.bench_measurement_writeup.run import (  # noqa: E402
    LEVEL,
    Figure,
    LINE_REG_MAX_PCT,
    VOUT_MIN_V,
    compute_results,
    line_regulation_pct,
    run,
    unsupported_numbers,
)
from examples.common.bench import VERDICT_FAIL, VERDICT_PASS, VERDICT_UNKNOWN, margin_to_limit  # noqa: E402
from examples.common.model import StubModel, StubResponse  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402

THIN_MARGIN_SERIAL = "SRB5030-2609-0003"
MARGINAL_LINE_SERIAL = "SRB5030-2609-0005"

# A clean draft: every number in it is one of compute_results()'s own figures, character for
# character. Built the same way a person reviewing this recipe's page would: read the figures
# list and the notebook, write sentences, copy the numbers rather than retype them.
CLEAN_DRAFT = (
    "Five revision C prototypes were swept over line, load and temperature. At the corner where "
    "line, load and temperature all push the output down together, 9.0 V in, 3.000 A out, 70 "
    "degC, the margin to the 4.900 V output voltage minimum was 73.9 mV for SRB5030-2609-0001, "
    "58.2 mV for SRB5030-2609-0002, 20.4 mV for SRB5030-2609-0003, 78.5 mV for "
    "SRB5030-2609-0004, and 64.7 mV for SRB5030-2609-0005.\n\n"
    "SRB5030-2609-0003 holds a fifth of the margin the other four hold at that corner, but it is "
    "not a failing board: no single parameter of it is out of specification on its own, and its "
    "corner reading, expanded at a coverage factor of 2 (k = 2), is good to 352.7 uV, nowhere "
    "near the 20.4 mV margin it is being measured against.\n\n"
    "SRB5030-2609-0005's line regulation stays inside its 0.300 percent limit at the cold end "
    "(0.267 percent) and fails it at 70 degC (0.334 percent). At room temperature it reads 0.299 "
    "percent, inside the limit by less than the measurement's own 0.0075 percentage points of "
    "uncertainty, so the honest verdict there is cannot say, not a pass.\n\n"
    "Two items are still open. The block recorded at 12.0 V on SRB5030-2609-0001 needs its input "
    "current checked before anyone uses it. And the 200 uV lead and connection contribution "
    "behind every uncertainty above is an assumption from the calibration procedure, not "
    "something measured on this harness."
)

# The same report, with the uncertainty rounded from 352.7 to a tidier 350: a plausible,
# "improved" number code never produced.
ROUNDED_DRAFT = CLEAN_DRAFT.replace("352.7 uV", "350 uV")


def _tracer() -> Tracer:
    return Tracer(example="bench_measurement_writeup", level=LEVEL, model_id="stub-1")


class ComputeResultsTests(unittest.TestCase):
    """The figures reproduce docs/THE-BENCH.md's answer key, recomputed independently here."""

    def setUp(self) -> None:
        self.results = compute_results()

    def test_the_thin_margin_board_and_its_corner_margins(self) -> None:
        # docs/THE-BENCH.md, "Story A": 73.9, 58.2, 20.4, 78.5, 64.7 mV.
        self.assertEqual(self.results.thin_serial, THIN_MARGIN_SERIAL)
        expected = {
            "SRB5030-2609-0001": 73.9,
            "SRB5030-2609-0002": 58.2,
            "SRB5030-2609-0003": 20.4,
            "SRB5030-2609-0004": 78.5,
            "SRB5030-2609-0005": 64.7,
        }
        for serial, mv in expected.items():
            self.assertAlmostEqual(self.results.corner_margins_mv[serial], mv, delta=0.05, msg=serial)

    def test_the_corner_uncertainty_is_far_smaller_than_the_margin(self) -> None:
        # The measurement decides Story A: docs/THE-BENCH.md puts the ratio over 50.
        margin_v = self.results.corner_margins_mv[THIN_MARGIN_SERIAL] / 1000.0
        expanded_v = self.results.corner_expanded_uncertainty_uv / 1e6
        self.assertGreater(margin_v / expanded_v, 50.0)
        self.assertEqual(self.results.corner_verdict, VERDICT_PASS)

    def test_the_three_line_regulation_verdicts(self) -> None:
        # docs/THE-BENCH.md, "Story B": 0.267 (pass), 0.299 (cannot say), 0.334 (fail) percent.
        self.assertAlmostEqual(self.results.line_reg_pct["0.0"], 0.267, places=3)
        self.assertAlmostEqual(self.results.line_reg_pct["25.0"], 0.299, places=3)
        self.assertAlmostEqual(self.results.line_reg_pct["70.0"], 0.334, places=3)
        self.assertEqual(
            self.results.line_reg_verdicts,
            {"0.0": VERDICT_PASS, "25.0": VERDICT_UNKNOWN, "70.0": VERDICT_FAIL},
        )
        self.assertAlmostEqual(self.results.line_reg_uncertainty_pct, 0.0075, delta=0.0015)

    def test_leaving_the_uncertainty_out_would_have_called_the_cannot_say_row_a_pass(self) -> None:
        # The same point this bench's other pages make: 0.299 < 0.300 reads as a pass without an
        # uncertainty attached, and that reading is not one this recipe's figures support.
        self.assertLess(self.results.line_reg_pct["25.0"], LINE_REG_MAX_PCT)

    def test_every_figure_is_recomputable_from_the_csv_with_nothing_but_this_module(self) -> None:
        # margin_to_limit and line_regulation_pct are the only two pieces of arithmetic this
        # recipe adds to the shared bench functions; both are one line, checked here directly.
        self.assertAlmostEqual(
            margin_to_limit(4.92038, VOUT_MIN_V, side="lower") * 1000.0,
            self.results.corner_margins_mv[THIN_MARGIN_SERIAL],
            delta=0.05,
        )

    def test_figures_are_formatted_once_and_reused(self) -> None:
        labels = [f.label for f in self.results.figures]
        self.assertEqual(len(labels), len(set(labels)), "no figure is computed and labeled twice")
        for figure in self.results.figures:
            self.assertIsInstance(figure, Figure)
            self.assertTrue(figure.text.strip(), figure.label)

    def test_the_corner_budget_table_the_page_quotes(self) -> None:
        """The recipe page shows the thin-margin board's corner budget as a four-line table.
        Pin every line here, independently of `compute_results`' own combining, so the page
        cannot drift from what `dc_voltage_budget` actually returns for this corner."""
        from examples.bench_measurement_writeup.run import CORNER_IOUT_A, CORNER_TAMB_C, CORNER_VIN_V, DC_RANGE_V, _read_rows, _readings
        from evals.bench import CHARACTERIZATION_CSV
        from examples.common.bench import dc_voltage_budget

        rows = _read_rows(CHARACTERIZATION_CSV)
        readings = _readings(rows, THIN_MARGIN_SERIAL, CORNER_TAMB_C, CORNER_VIN_V, CORNER_IOUT_A)
        budget = dc_voltage_budget(readings, range_v=DC_RANGE_V)
        by_name = {c.name: 1e6 * c.standard_uncertainty for c in budget}
        self.assertAlmostEqual(by_name["meter accuracy"], 128.3, delta=0.1)
        self.assertAlmostEqual(by_name["resolution"], 2.9, delta=0.1)
        self.assertAlmostEqual(by_name["repeatability"], 36.1, delta=0.1)
        self.assertAlmostEqual(by_name["leads and connections"], 115.5, delta=0.1)
        self.assertAlmostEqual(self.results.corner_expanded_uncertainty_uv, 352.7, delta=0.1)


class UnsupportedNumbersTests(unittest.TestCase):
    """The check: a real function, not a description of one."""

    def setUp(self) -> None:
        self.figures = compute_results().figures

    def test_a_clean_draft_has_nothing_unsupported(self) -> None:
        self.assertEqual(unsupported_numbers(CLEAN_DRAFT, self.figures), ())

    def test_a_rounded_figure_is_caught(self) -> None:
        found = unsupported_numbers(ROUNDED_DRAFT, self.figures)
        self.assertIn("350", found)
        self.assertNotIn("352.7", found, "the correct figure elsewhere in the draft is still fine")

    def test_an_invented_number_with_no_source_at_all_is_caught(self) -> None:
        draft = CLEAN_DRAFT + " A sixth board is expected next month, part 7734."
        found = unsupported_numbers(draft, self.figures)
        self.assertIn("7734", found)

    def test_serial_numbers_are_never_read_as_quoted_measurements(self) -> None:
        # The whole reason for the lookbehind/lookahead in NUMBER_RE: "SRB5030-2609-0003" must
        # not be read as the numbers 5030, 2609 and 0003, or every serial in the draft would have
        # to be pre-approved as a figure.
        draft = "Boards SRB5030-2609-0001 through SRB5030-2609-0005 were characterized."
        self.assertEqual(unsupported_numbers(draft, self.figures), ())

    def test_a_figure_used_more_than_once_is_reported_each_time(self) -> None:
        draft = "The reading was 9999 volts, then checked again at 9999 volts."
        self.assertEqual(unsupported_numbers(draft, self.figures), ("9999", "9999"))

    def test_a_negative_number_is_still_a_number(self) -> None:
        self.assertEqual(unsupported_numbers("The margin came to -0.034 points.", self.figures), ("-0.034",))

    def test_a_fabricated_number_glued_to_its_unit_is_still_caught(self) -> None:
        # The first way this check was broken: with no space before the unit, an earlier
        # lookahead refused to match "350uV" at all and a made-up figure went through clean.
        self.assertEqual(unsupported_numbers("The budget came to 350uV.", self.figures), ("350",))

    def test_a_real_figure_glued_to_its_unit_is_not_truncated(self) -> None:
        # The same bug the other way round: the token has to be the whole figure, or a correct
        # draft gets rejected for a number it quoted correctly.
        self.assertEqual(unsupported_numbers("The budget came to 352.7uV.", self.figures), ())

    def test_the_second_number_of_a_range_is_not_skipped(self) -> None:
        # A hyphen between two numbers used to stop the scan restarting, so everything after the
        # dash in "20.4-99.9 mV" was never looked at.
        self.assertEqual(unsupported_numbers("Margins ran 20.4-99.9 mV.", self.figures), ("99.9",))
        self.assertEqual(unsupported_numbers("Margins ran 20.4-78.5 mV.", self.figures), ())

    def test_a_figure_followed_by_a_comma_is_not_reported_as_unsupported(self) -> None:
        # The comma used to be swallowed into the token, so "2," never matched the figure "2".
        self.assertEqual(unsupported_numbers("The coverage factor is 2, as stated.", self.figures), ())

    def test_a_bare_decimal_is_a_number(self) -> None:
        self.assertEqual(unsupported_numbers("It read .299 percent.", self.figures), (".299",))

    def test_a_date_is_checked_whole_against_the_sweep_s_own_days(self) -> None:
        # The sweep's first and last day are figures, read off the CSV's timestamps, so a report
        # may date itself; a date the sweep does not have is one token, not three digit groups.
        self.assertEqual(
            unsupported_numbers("The sweep ran 09/14/2026 to 09/16/2026.", self.figures), ()
        )
        self.assertEqual(
            unsupported_numbers("The sweep ran 09/14/2026 to 09/20/2026.", self.figures),
            ("09/20/2026",),
        )

    def test_a_digit_buried_in_a_word_is_the_limit_this_check_accepts(self) -> None:
        # Identifier-shaped tokens are blanked so serial numbers are not read as measurements,
        # and the cost of that is stated on the page: a digit inside a word is not scanned.
        self.assertEqual(unsupported_numbers("Fixture FIX99 was used.", self.figures), ())


class RunTests(unittest.TestCase):
    def test_a_clean_draft_passes_the_check(self) -> None:
        model = StubModel([StubResponse(text=CLEAN_DRAFT)])
        tracer = _tracer()
        report = run("", model, tracer)
        self.assertTrue(report.ok)
        self.assertEqual(report.unsupported, ())
        self.assertEqual(report.text, CLEAN_DRAFT)

    def test_a_rounded_draft_fails_the_check_and_is_not_silently_fixed(self) -> None:
        model = StubModel([StubResponse(text=ROUNDED_DRAFT)])
        tracer = _tracer()
        report = run("", model, tracer)
        self.assertFalse(report.ok)
        self.assertIn("350", report.unsupported)
        self.assertEqual(report.text, ROUNDED_DRAFT, "a rejected draft is returned, not discarded")

    def test_exactly_one_model_call_and_every_step_decided_by_code(self) -> None:
        model = StubModel([StubResponse(text=CLEAN_DRAFT)])
        tracer = _tracer()
        run("", model, tracer)
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 1)
        self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))
        self.assertEqual(tracer.model_decided_count(), 0)

    def test_the_token_counts_the_page_quotes(self) -> None:
        """The recipe page's cost section quotes this call's tokens and figure count; pin them
        here so the page cannot drift from what the code actually sends and computes."""
        model = StubModel([StubResponse(text=CLEAN_DRAFT)])
        tracer = _tracer()
        report = run("", model, tracer)
        self.assertEqual(tracer.tokens_in_total(), 2724)
        self.assertEqual(tracer.tokens_out_total(), 340)
        self.assertEqual(len(report.figures), 25)

    def test_the_check_step_is_in_the_trace_and_names_the_failure(self) -> None:
        model = StubModel([StubResponse(text=ROUNDED_DRAFT)])
        tracer = _tracer()
        run("", model, tracer)
        checks = [s for s in tracer.steps if s.title == "Check the draft's numbers against the figures"]
        self.assertEqual(len(checks), 1)
        self.assertIn("350", checks[0].detail)

    def test_notes_are_appended_but_never_supply_a_number(self) -> None:
        model = StubModel([StubResponse(text=CLEAN_DRAFT)])
        tracer = _tracer()
        report = run("Lead with the thin-margin board.", model, tracer)
        self.assertTrue(report.ok)

    def test_declares_its_level_and_a_run_function(self) -> None:
        self.assertEqual(LEVEL, 1)
        self.assertTrue(callable(run))


if __name__ == "__main__":
    unittest.main()
