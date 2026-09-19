"""Tests for examples/household_paperwork: the level-0 household report.

Nothing here calls a model, and one of the tests proves it by handing `run` a model that raises
if it is ever asked for a completion. The rest are the arithmetic: the renewal window's two
boundaries, the normalization of three billing periods to a year, a category total recomputed in
the test rather than read back from the code, the folder's naming rule, and the money formatter,
which is where an off-by-a-factor-of-ten bug would live.
"""
from __future__ import annotations

import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.common.model import StubModel  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.household_paperwork.run import (  # noqa: E402
    AS_OF,
    FILE_RE,
    LEVEL,
    PER_YEAR,
    RECORDS,
    RENEWAL_WINDOW_DAYS,
    SAMPLE_INPUT,
    Record,
    as_of_from,
    largest_yearly,
    misfiled,
    money,
    renewals_due,
    run,
    unpaid_bills,
    yearly_by_category,
    yearly_cents,
)

RUN_PY = ROOT / "examples" / "household_paperwork" / "run.py"


def tracer() -> Tracer:
    return Tracer(example="household_paperwork", level=LEVEL, model_id="none")


def record(rid: str, **kw) -> Record:
    base = dict(provider="Provider", category="subscriptions", amount_cents=1_000,
                period="monthly", due=AS_OF, document=None)
    base.update(kw)
    return Record(id=rid, **base)


class ReportTests(unittest.TestCase):
    def test_the_sample_run_reports_the_renewals_the_bills_and_the_gaps(self) -> None:
        report = run(SAMPLE_INPUT, None, tracer())
        self.assertEqual(report.as_of, date(2026, 9, 19))
        self.assertEqual([r.id for r in report.renewals], ["r02", "r01", "r06", "r09", "r07"])
        self.assertEqual([(r.id, late) for r, late in report.unpaid], [("r04", True), ("r03", False)])
        self.assertEqual(report.unreadable_files, ("Pellmore receipt (2).pdf", "scan_0043.pdf"))
        self.assertEqual([r.id for r in report.undocumented], ["r09"])

    def test_every_step_is_the_codes_and_no_model_is_ever_called(self) -> None:
        def explode(messages, tools):
            raise AssertionError("a level-0 recipe called a model")

        trace = tracer()
        run(SAMPLE_INPUT, StubModel(explode, model_id="stub-forbidden"), trace)
        self.assertTrue(trace.steps)
        self.assertEqual(trace.model_decided_count(), 0)
        self.assertTrue(all(s.decided_by == "code" and s.kind == "code" for s in trace.steps))

    def test_the_source_records_no_model_decision_anywhere(self) -> None:
        # scripts/validate.py reads examples for this string; the example must not carry one.
        self.assertNotIn('decided_by="model"', RUN_PY.read_text(encoding="utf-8"))


class RenewalWindowTests(unittest.TestCase):
    """The window is inclusive at both ends, and a renewal that has already passed is not a
    warning about the future. Both boundaries are one `<=` away from being wrong."""

    def test_the_last_day_of_the_window_is_inside_it_and_the_next_day_is_not(self) -> None:
        inside = record("in", auto_renew=True, due=AS_OF + timedelta(days=RENEWAL_WINDOW_DAYS))
        outside = record("out", auto_renew=True, due=AS_OF + timedelta(days=RENEWAL_WINDOW_DAYS + 1))
        found = renewals_due([inside, outside], AS_OF)
        self.assertEqual([r.id for r in found], ["in"])

    def test_a_renewal_today_is_reported_and_one_yesterday_is_not(self) -> None:
        today = record("today", auto_renew=True, due=AS_OF)
        gone = record("gone", auto_renew=True, due=AS_OF - timedelta(days=1))
        self.assertEqual([r.id for r in renewals_due([today, gone], AS_OF)], ["today"])

    def test_a_bill_that_does_not_renew_itself_is_not_a_renewal(self) -> None:
        self.assertEqual(renewals_due([record("r", auto_renew=False, due=AS_OF)], AS_OF), [])

    def test_an_unpaid_bill_is_overdue_only_once_its_date_has_passed(self) -> None:
        late = record("late", paid=False, due=AS_OF - timedelta(days=1))
        today = record("today", paid=False, due=AS_OF)
        paid = record("paid", paid=True, due=AS_OF - timedelta(days=9))
        rows = unpaid_bills([late, today, paid], AS_OF)
        self.assertEqual([(r.id, flag) for r, flag in rows], [("late", True), ("today", False)])


class YearlyArithmeticTests(unittest.TestCase):
    def test_each_period_is_multiplied_by_its_own_number_of_payments(self) -> None:
        for period, times in PER_YEAR.items():
            with self.subTest(period=period):
                self.assertEqual(yearly_cents(record("x", period=period, amount_cents=2_500)), 2_500 * times)

    def test_a_one_off_is_a_real_cost_and_not_a_yearly_one(self) -> None:
        self.assertEqual(yearly_cents(record("x", period="one-off", amount_cents=8_900)), 0)
        self.assertNotIn("x", yearly_by_category([record("x", period="one-off", category="warranty")]))

    def test_a_period_nobody_priced_counts_as_nothing_rather_than_as_a_guess(self) -> None:
        self.assertEqual(yearly_cents(record("x", period="fortnightly")), 0)

    def test_the_category_totals_are_what_the_records_add_up_to(self) -> None:
        """Recomputed here from RECORDS rather than copied out of the report: a total the code
        and the test both got from the same call proves nothing."""
        expected: dict[str, int] = {}
        for r in RECORDS:
            times = PER_YEAR.get(r.period, 0)
            if times:
                expected[r.category] = expected.get(r.category, 0) + r.amount_cents * times
        totals = yearly_by_category(RECORDS)
        self.assertEqual(totals, dict(sorted(expected.items(), key=lambda kv: (-kv[1], kv[0]))))
        self.assertEqual(sum(totals.values()), 586_028)  # $5,860.28 a year, from the records above

    def test_the_categories_come_back_largest_first(self) -> None:
        totals = list(yearly_by_category(RECORDS).values())
        self.assertEqual(totals, sorted(totals, reverse=True))

    def test_the_largest_commitments_are_ranked_by_the_yearly_figure_not_the_bill(self) -> None:
        biggest = largest_yearly(RECORDS, top=3)
        self.assertEqual([r.id for r in biggest], ["r04", "r01", "r02"])
        self.assertGreater(yearly_cents(biggest[0]), yearly_cents(biggest[1]))
        # r06 is $55.00 a month and r12 is $216.00 once a year: the smaller bill is the larger
        # commitment, which is the whole reason for normalizing before ranking anything.
        ranked = [r.id for r in largest_yearly(RECORDS, top=len(RECORDS))]
        self.assertLess(ranked.index("r06"), ranked.index("r12"))

    def test_money_formats_cents_as_cents(self) -> None:
        self.assertEqual(money(5), "$0.05")
        self.assertEqual(money(5_005), "$50.05")
        self.assertEqual(money(118_400), "$1,184.00")


class FolderTests(unittest.TestCase):
    def test_the_naming_rule_accepts_a_dated_file_and_rejects_the_two_shapes_that_break_it(self) -> None:
        self.assertTrue(FILE_RE.match("2026-09-14_brackle-water-board_bill.pdf"))
        self.assertFalse(FILE_RE.match("Pellmore receipt (2).pdf"))
        self.assertFalse(FILE_RE.match("scan_0043.pdf"))
        self.assertFalse(FILE_RE.match("2026-09-14_brackle-water-board.pdf"))

    def test_a_record_pointing_at_a_file_that_is_not_in_the_folder_is_reported(self) -> None:
        ghost = record("ghost", document="2026-01-01_nobody_bill.pdf")
        _, missing = misfiled([ghost], ("2026-01-02_somebody_bill.pdf",))
        self.assertEqual([r.id for r in missing], ["ghost"])


class AsOfTests(unittest.TestCase):
    def test_an_empty_request_uses_the_modules_own_date(self) -> None:
        self.assertEqual(as_of_from(""), AS_OF)
        self.assertEqual(as_of_from("   "), AS_OF)

    def test_a_date_inside_a_sentence_is_the_date_the_report_runs_for(self) -> None:
        self.assertEqual(as_of_from("what renews after 2026-11-15?"), date(2026, 11, 15))

    def test_text_with_no_date_is_refused_rather_than_answered_for_today(self) -> None:
        with self.assertRaises(ValueError):
            as_of_from("what renews soon?")

    def test_a_date_that_does_not_exist_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            as_of_from("2026-02-31")


if __name__ == "__main__":
    unittest.main()
