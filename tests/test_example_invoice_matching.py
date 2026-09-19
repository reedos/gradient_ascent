"""Tests for examples/invoice_matching: one model call to read the invoice, then a lookup and
three subtractions, all `decided_by="code"`.

The tolerance is zero, so the tests that matter most are the ones that prove it is exact: a
one-cent price difference pauses the same as a hundred-dollar one, and a line that matches the
purchase order perfectly still gets caught when the invoice's own total disagrees with its own
lines. Two more tests attack the example directly, the way a bad extraction actually would: a
line item that sounds plausible but the purchase order never ordered, and a currency that quietly
does not match the order it is billed against.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.common.model import StubModel, StubResponse  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.invoice_matching.run import (  # noqa: E402
    GOODS_RECEIVED,
    LEVEL,
    PURCHASE_ORDERS,
    SAMPLE_INPUT,
    TOLERANCE_CENTS,
    PendingMatch,
    PostedInvoice,
    RejectedInvoice,
    resume,
    run,
)

RUN_PY = ROOT / "examples" / "invoice_matching" / "run.py"

CLEAN_INVOICE = {
    "supplier": "Corrigan Fasteners",
    "po_number": "PO-4410",
    "invoice_number": "INV-77012",
    "currency": "USD",
    "line_items": [
        {"code": "FST-2201", "quantity": 40, "unit_price_cents": 1_250},
        {"code": "FST-2209", "quantity": 40, "unit_price_cents": 640},
    ],
    "total_cents": 75_600,
}


def _invoice(**overrides) -> str:
    record = json.loads(json.dumps(CLEAN_INVOICE))  # a deep copy, so overrides never mutate CLEAN_INVOICE
    record.update(overrides)
    return json.dumps(record)


def _tracer() -> Tracer:
    return Tracer(example="invoice_matching", level=LEVEL, model_id="stub-1")


class CleanMatchTests(unittest.TestCase):
    def test_a_clean_match_posts_without_a_pause(self) -> None:
        model = StubModel([StubResponse(text=_invoice())])
        tracer = _tracer()
        result = run(SAMPLE_INPUT, model, tracer)
        self.assertIsInstance(result, PostedInvoice)
        self.assertEqual(result.po_number, "PO-4410")
        self.assertEqual(result.posted_cents, 75_600)
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 1, "should not have retried")

    def test_every_step_is_the_codes_and_no_model_is_ever_called_to_decide(self) -> None:
        model = StubModel([StubResponse(text=_invoice())])
        tracer = _tracer()
        run(SAMPLE_INPUT, model, tracer)
        self.assertTrue(tracer.steps)
        self.assertEqual(tracer.model_decided_count(), 0)
        self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))

    def test_the_source_records_no_model_decision_anywhere(self) -> None:
        # scripts/validate.py reads examples for this string; the example must not carry one.
        self.assertNotIn('decided_by="model"', RUN_PY.read_text(encoding="utf-8"))

    def test_declares_its_level_and_a_run_and_resume_function(self) -> None:
        self.assertEqual(LEVEL, 3)
        self.assertTrue(callable(run))
        self.assertTrue(callable(resume))

    def test_the_token_counts_the_page_quotes(self) -> None:
        """The recipe page's cost strip quotes these two totals for one clean, unretried run;
        pin them so the page cannot drift from the prompt the code actually builds."""
        model = StubModel([StubResponse(text=_invoice())])
        tracer = _tracer()
        run(SAMPLE_INPUT, model, tracer)
        self.assertEqual(tracer.tokens_in_total(), 236)
        self.assertEqual(tracer.tokens_out_total(), 68)


class ToleranceTests(unittest.TestCase):
    """The tolerance is zero cents; these two prove it is exact rather than a rounded-off
    approximation of exact."""

    def test_the_tolerance_is_zero_cents(self) -> None:
        self.assertEqual(TOLERANCE_CENTS, 0)

    def test_a_one_cent_unit_price_difference_pauses(self) -> None:
        invoice = _invoice(
            po_number="PO-4412", invoice_number="INV-9001",
            line_items=[{"code": "FST-2201", "quantity": 25, "unit_price_cents": 1_251}],
            total_cents=25 * 1_251,
        )
        model = StubModel([StubResponse(text=invoice)])
        tracer = _tracer()
        result = run(SAMPLE_INPUT, model, tracer)
        self.assertIsInstance(result, PendingMatch)
        self.assertEqual(result.stage, "mismatch")
        self.assertTrue(any("1251" in r and "1250" in r for r in result.reasons), result.reasons)

    def test_the_same_line_at_the_ordered_price_does_not_pause(self) -> None:
        invoice = _invoice(
            po_number="PO-4412", invoice_number="INV-9002",
            line_items=[{"code": "FST-2201", "quantity": 25, "unit_price_cents": 1_250}],
            total_cents=25 * 1_250,
        )
        model = StubModel([StubResponse(text=invoice)])
        result = run(SAMPLE_INPUT, model, _tracer())
        self.assertIsInstance(result, PostedInvoice)


class ThreeWayMatchTests(unittest.TestCase):
    def test_an_invoice_quantity_above_what_was_received_pauses_with_that_reason(self) -> None:
        # PO-4411 ordered 500 mailers; the dock only logged 480.
        invoice = _invoice(
            supplier="Bellwether Packaging", po_number="PO-4411", invoice_number="INV-6120",
            line_items=[
                {"code": "PKG-1180", "quantity": 500, "unit_price_cents": 38},
                {"code": "PKG-1190", "quantity": 20, "unit_price_cents": 1_150},
            ],
            total_cents=500 * 38 + 20 * 1_150,
        )
        model = StubModel([StubResponse(text=invoice)])
        result = run(SAMPLE_INPUT, model, _tracer())
        self.assertIsInstance(result, PendingMatch)
        self.assertEqual(result.stage, "mismatch")
        self.assertTrue(any("PKG-1180" in r and "500" in r and "480" in r for r in result.reasons), result.reasons)
        # The other line matched exactly and must not itself have produced a reason.
        self.assertFalse(any("PKG-1190" in r for r in result.reasons))

    def test_an_unknown_purchase_order_pauses_rather_than_posting(self) -> None:
        invoice = _invoice(po_number="PO-9999", invoice_number="INV-0001")
        model = StubModel([StubResponse(text=invoice)])
        result = run(SAMPLE_INPUT, model, _tracer())
        self.assertIsInstance(result, PendingMatch)
        self.assertEqual(result.stage, "unknown_po")
        self.assertEqual(result.po_number, "PO-9999")

    def test_the_total_is_recomputed_and_catches_a_bad_total_even_when_every_line_matches(self) -> None:
        # ADH-330: 60 at 875 cents is 52,500 cents. The invoice claims 52,600, a hundred cents
        # nobody's line items can account for, even though the single line matches the order and
        # the receiving record exactly.
        invoice = _invoice(
            supplier="Thornwell Adhesives", po_number="PO-4413", invoice_number="INV-3390",
            line_items=[{"code": "ADH-330", "quantity": 60, "unit_price_cents": 875}],
            total_cents=52_600,
        )
        model = StubModel([StubResponse(text=invoice)])
        result = run(SAMPLE_INPUT, model, _tracer())
        self.assertIsInstance(result, PendingMatch)
        self.assertEqual(result.stage, "mismatch")
        self.assertTrue(any("52600" in r and "52500" in r for r in result.reasons), result.reasons)

    def test_a_purchase_order_with_no_discrepancy_recomputes_the_same_total_it_was_given(self) -> None:
        po = PURCHASE_ORDERS["PO-4413"]
        received = {line.code: line.quantity_received for line in GOODS_RECEIVED["PO-4413"]}
        self.assertEqual(received["ADH-330"], po.lines[0].quantity)
        self.assertEqual(po.lines[0].quantity * po.lines[0].unit_price_cents, 52_500)


class RetryTests(unittest.TestCase):
    def test_the_retry_path_when_the_first_reply_is_not_valid_json(self) -> None:
        model = StubModel([StubResponse(text="not json at all"), StubResponse(text=_invoice())])
        tracer = _tracer()
        result = run(SAMPLE_INPUT, model, tracer)
        self.assertIsInstance(result, PostedInvoice)
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 2)
        self.assertEqual(tracer.model_decided_count(), 0)

    def test_still_invalid_after_the_retry_pauses_rather_than_guessing(self) -> None:
        bad = json.dumps({"supplier": "Corrigan Fasteners"})  # missing everything else, twice
        model = StubModel([StubResponse(text=bad), StubResponse(text=bad)])
        result = run(SAMPLE_INPUT, model, _tracer())
        self.assertIsInstance(result, PendingMatch)
        self.assertEqual(result.stage, "extraction_failed")
        self.assertIsNone(result.invoice)


class AttackTests(unittest.TestCase):
    """Attacking the example: a reply that is well formed and still wrong."""

    def test_a_plausible_but_absent_line_item_is_not_posted(self) -> None:
        invoice = _invoice(
            invoice_number="INV-7777",
            line_items=[
                {"code": "FST-2201", "quantity": 40, "unit_price_cents": 1_250},
                {"code": "FST-2209", "quantity": 40, "unit_price_cents": 640},
                {"code": "FST-2299", "quantity": 5, "unit_price_cents": 500},  # never ordered
            ],
            total_cents=75_600 + 5 * 500,
        )
        model = StubModel([StubResponse(text=invoice)])
        result = run(SAMPLE_INPUT, model, _tracer())
        self.assertIsInstance(result, PendingMatch)
        self.assertEqual(result.stage, "mismatch")
        self.assertTrue(any("FST-2299" in r for r in result.reasons), result.reasons)

    def test_a_currency_that_does_not_match_the_purchase_order_is_not_posted(self) -> None:
        invoice = _invoice(
            supplier="Thornwell Adhesives", po_number="PO-4413", invoice_number="INV-3391",
            currency="EUR",
            line_items=[{"code": "ADH-330", "quantity": 60, "unit_price_cents": 875}],
            total_cents=52_500,
        )
        model = StubModel([StubResponse(text=invoice)])
        result = run(SAMPLE_INPUT, model, _tracer())
        self.assertIsInstance(result, PendingMatch)
        self.assertEqual(result.stage, "mismatch")
        self.assertTrue(any("EUR" in r and "USD" in r for r in result.reasons), result.reasons)


class MoneyIsIntegerCentsTests(unittest.TestCase):
    def test_every_purchase_order_line_is_an_integer_number_of_cents(self) -> None:
        for po in PURCHASE_ORDERS.values():
            for line in po.lines:
                self.assertIsInstance(line.unit_price_cents, int)
                self.assertNotIsInstance(line.unit_price_cents, float)

    def test_a_posted_amount_is_an_integer_number_of_cents(self) -> None:
        model = StubModel([StubResponse(text=_invoice())])
        result = run(SAMPLE_INPUT, model, _tracer())
        self.assertIsInstance(result, PostedInvoice)
        self.assertIsInstance(result.posted_cents, int)
        self.assertNotIsInstance(result.posted_cents, float)


class ResumeTests(unittest.TestCase):
    def test_resume_approve_posts_the_pending_invoice(self) -> None:
        invoice = _invoice(
            po_number="PO-4412", invoice_number="INV-9001",
            line_items=[{"code": "FST-2201", "quantity": 25, "unit_price_cents": 1_251}],
            total_cents=25 * 1_251,
        )
        model = StubModel([StubResponse(text=invoice)])
        tracer = _tracer()
        pending = run(SAMPLE_INPUT, model, tracer)
        self.assertIsInstance(pending, PendingMatch)
        posted = resume(pending, "approve", tracer, note="checked against the supplier's confirmation")
        self.assertIsInstance(posted, PostedInvoice)
        self.assertEqual(posted.posted_cents, 25 * 1_251)

    def test_resume_reject_does_not_post(self) -> None:
        invoice = _invoice(po_number="PO-9999", invoice_number="INV-0001")
        model = StubModel([StubResponse(text=invoice)])
        tracer = _tracer()
        pending = run(SAMPLE_INPUT, model, tracer)
        rejected = resume(pending, "reject", tracer, note="no such purchase order")
        self.assertIsInstance(rejected, RejectedInvoice)
        self.assertEqual(rejected.reason, "no such purchase order")

    def test_resume_on_a_failed_extraction_refuses_to_post(self) -> None:
        bad = json.dumps({"supplier": "Corrigan Fasteners"})
        model = StubModel([StubResponse(text=bad), StubResponse(text=bad)])
        tracer = _tracer()
        pending = run(SAMPLE_INPUT, model, tracer)
        with self.assertRaises(ValueError):
            resume(pending, "approve", tracer)

    def test_resume_itself_is_decided_by_code(self) -> None:
        invoice = _invoice(po_number="PO-9999", invoice_number="INV-0001")
        model = StubModel([StubResponse(text=invoice)])
        tracer = _tracer()
        pending = run(SAMPLE_INPUT, model, tracer)
        before = len(tracer.steps)
        resume(pending, "reject", tracer)
        after_steps = tracer.steps[before:]
        self.assertTrue(after_steps)
        self.assertTrue(all(s.decided_by == "code" for s in after_steps))


if __name__ == "__main__":
    unittest.main()
