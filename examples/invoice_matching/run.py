"""Level 3: read an invoice into fixed fields, then let code do the whole match. The model is
called exactly once (twice on a retry): it turns the text a supplier sent into a supplier name,
a purchase order number, an invoice number, a currency and a set of line items. Everything after
that is a lookup and three subtractions, run by code:

- Look up the purchase order the invoice names. No number, or a number nothing on file matches,
  waits for a person rather than getting posted against a guess (`_lookup_po` failing).
- Quantity invoiced against quantity received, per line.
- Unit price invoiced against the price the purchase order was placed at, per line.
- The invoice's own stated total against the sum of its own lines, recomputed independently. A
  line can match the purchase order exactly and the invoice can still misstate its own total; the
  recompute is what catches that.

`TOLERANCE_CENTS` is zero: this join is exact by construction (a quantity is a count, a unit
price and a total are both printed on the document), so a cent of drift is not rounding, it is a
transcription error, and it is cheap for a person to glance at before money moves. A model never
sees any of these four checks: `decided_by="code"` on every step, because the amount that gets
paid is a subtraction, never a judgment.

Nothing here posts an invoice that names a line the purchase order does not have, even when the
invoice's own total is internally consistent: a plausible-looking part number that nobody ordered
is exactly the kind of read a scanned document produces, and the join across the purchase order
is what catches it, not the arithmetic on the invoice alone.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal

from examples.common.model import Message, Model
from examples.common.trace import Tracer

LEVEL = 3
MAX_RETRIES = 1

#: The match is exact: a quantity is a count, and a unit price and a total are both printed on
#: the invoice itself. A cent of drift is a transcription error, not rounding, and it is cheap
#: for a person to glance at, so the tolerance is zero rather than a guessed-at cushion.
TOLERANCE_CENTS = 0

REQUIRED_FIELDS = ("supplier", "po_number", "invoice_number", "currency", "line_items", "total_cents")
SCHEMA = {
    "type": "object",
    "properties": {
        "supplier": {"type": "string"},
        "po_number": {"type": "string"},
        "invoice_number": {"type": "string"},
        "currency": {"type": "string"},
        "line_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "quantity": {"type": "integer"},
                    "unit_price_cents": {"type": "integer"},
                },
                "required": ["code", "quantity", "unit_price_cents"],
            },
        },
        "total_cents": {"type": "integer"},
    },
    "required": list(REQUIRED_FIELDS),
}
SYSTEM_PROMPT = (
    "Extract an invoice from the text as JSON matching this schema, with no other text and no "
    f"markdown fences. Amounts are whole cents, never a decimal. Schema: {json.dumps(SCHEMA)}"
)


# ---------------------------------------------------------------------------
# The world: invented purchase orders and what was actually received against each.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class POLine:
    code: str
    description: str
    quantity: int
    unit_price_cents: int


@dataclass(frozen=True)
class PurchaseOrder:
    po_number: str
    supplier: str
    currency: str
    lines: tuple[POLine, ...]


@dataclass(frozen=True)
class ReceivedLine:
    code: str
    quantity_received: int


PURCHASE_ORDERS: dict[str, PurchaseOrder] = {
    "PO-4410": PurchaseOrder(
        po_number="PO-4410", supplier="Corrigan Fasteners", currency="USD",
        lines=(
            POLine("FST-2201", "M6 hex bolt, zinc-plated, 100-pack", 40, 1_250),
            POLine("FST-2209", "M6 flat washer, zinc-plated, 200-pack", 40, 640),
        ),
    ),
    "PO-4411": PurchaseOrder(
        po_number="PO-4411", supplier="Bellwether Packaging", currency="USD",
        lines=(
            POLine("PKG-1180", "Corrugated mailer, 10x8x4 in", 500, 38),
            POLine("PKG-1190", "Void fill, 100 L roll", 20, 1_150),
        ),
    ),
    "PO-4412": PurchaseOrder(
        po_number="PO-4412", supplier="Corrigan Fasteners", currency="USD",
        lines=(POLine("FST-2201", "M6 hex bolt, zinc-plated, 100-pack", 25, 1_250),),
    ),
    "PO-4413": PurchaseOrder(
        po_number="PO-4413", supplier="Thornwell Adhesives", currency="USD",
        lines=(POLine("ADH-330", "Two-part epoxy, 50 ml twin pack", 60, 875),),
    ),
}

#: What the receiving dock actually logged against each purchase order. PO-4411's mailers are
#: short by 20: the rest of the warehouse got 480 of the 500 ordered, and the eighty-forty-fourth
#: PO exists so a clean-looking line item can still fail on receipt rather than on price.
GOODS_RECEIVED: dict[str, tuple[ReceivedLine, ...]] = {
    "PO-4410": (ReceivedLine("FST-2201", 40), ReceivedLine("FST-2209", 40)),
    "PO-4411": (ReceivedLine("PKG-1180", 480), ReceivedLine("PKG-1190", 20)),
    "PO-4412": (ReceivedLine("FST-2201", 25),),
    "PO-4413": (ReceivedLine("ADH-330", 60),),
}

#: An invoice that matches PO-4410 exactly: 40 bolts at $12.50, 40 washers at $6.40, both fully
#: received, total $756.00. The clean path, so a recorded run shows one that posts.
SAMPLE_INPUT = """INVOICE
Corrigan Fasteners
Invoice #: INV-77012
PO Number: PO-4410
Currency: USD

FST-2201  M6 hex bolt, zinc-plated, 100-pack    qty 40   unit price $12.50
FST-2209  M6 flat washer, zinc-plated, 200-pack qty 40   unit price $6.40

Total due: $756.00
"""


# ---------------------------------------------------------------------------
# What the invoice text becomes, once it has been read.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InvoiceLine:
    code: str
    quantity: int
    unit_price_cents: int


@dataclass(frozen=True)
class ExtractedInvoice:
    supplier: str
    po_number: str
    invoice_number: str
    currency: str
    lines: tuple[InvoiceLine, ...]
    stated_total_cents: int


DiscrepancyKind = Literal["currency", "unknown_line", "quantity", "unit_price", "total"]


@dataclass(frozen=True)
class Discrepancy:
    kind: DiscrepancyKind
    code: str | None
    detail: str


Stage = Literal["extraction_failed", "unknown_po", "mismatch"]
Decision = Literal["approve", "reject"]


@dataclass(frozen=True)
class PendingMatch:
    """A paused match. `invoice` is the extracted record when extraction validated, and `None`
    when it never did, in which case there is nothing yet for a person to approve, only a
    supplier to ask for a corrected invoice."""

    invoice: ExtractedInvoice | None
    po_number: str
    reasons: tuple[str, ...]
    stage: Stage


@dataclass(frozen=True)
class PostedInvoice:
    po_number: str
    invoice_number: str
    supplier: str
    posted_cents: int


@dataclass(frozen=True)
class RejectedInvoice:
    po_number: str
    invoice_number: str
    reason: str


def _validate(record: dict) -> list[str]:
    problems = [f"missing field: {f}" for f in REQUIRED_FIELDS if f not in record]
    if problems:
        return problems
    for field in ("supplier", "po_number", "invoice_number", "currency"):
        if not isinstance(record[field], str) or not record[field].strip():
            problems.append(f"{field} must be a non-empty string")
    if not isinstance(record["total_cents"], int) or isinstance(record["total_cents"], bool):
        problems.append("total_cents must be an integer number of cents")
    items = record["line_items"]
    if not isinstance(items, list) or not items:
        problems.append("line_items must be a non-empty list")
        return problems
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            problems.append(f"line_items[{i}] is not an object")
            continue
        for f in ("code", "quantity", "unit_price_cents"):
            if f not in item:
                problems.append(f"line_items[{i}] missing field: {f}")
        if isinstance(item.get("code"), str):
            if not item["code"].strip():
                problems.append(f"line_items[{i}].code must be a non-empty string")
        elif "code" in item:
            problems.append(f"line_items[{i}].code must be a string")
        for f in ("quantity", "unit_price_cents"):
            if f in item and (not isinstance(item[f], int) or isinstance(item[f], bool)):
                problems.append(f"line_items[{i}].{f} must be an integer")
    return problems


def _record_to_invoice(record: dict) -> ExtractedInvoice:
    lines = tuple(
        InvoiceLine(code=i["code"], quantity=i["quantity"], unit_price_cents=i["unit_price_cents"])
        for i in record["line_items"]
    )
    return ExtractedInvoice(
        supplier=record["supplier"], po_number=record["po_number"], invoice_number=record["invoice_number"],
        currency=record["currency"], lines=lines, stated_total_cents=record["total_cents"],
    )


def _extract_invoice(text: str, model: Model, tracer: Tracer) -> tuple[ExtractedInvoice | None, list[str]]:
    """Ask the model for the fixed fields, validate the reply, and retry once with the
    validation error appended if it fails. The only model call in this recipe."""
    messages = [Message(role="system", content=SYSTEM_PROMPT), Message(role="user", content=text)]
    problems: list[str] = []
    for attempt in range(MAX_RETRIES + 1):
        completion = model.complete(messages, schema=SCHEMA, max_tokens=300)
        tracer.record(
            kind="model", decided_by="code",
            title="Read the invoice into fixed fields" if attempt == 0 else "Ask again with the validation error",
            detail=completion.text[:200],
            tokens_in=completion.tokens_in, tokens_out=completion.tokens_out, ms=completion.ms,
        )
        try:
            record = json.loads(completion.text)
            problems = _validate(record)
        except json.JSONDecodeError as exc:
            record, problems = {}, [f"invalid JSON: {exc}"]
        tracer.record(kind="code", decided_by="code", title="Validate against the schema", detail="; ".join(problems) or "valid")
        if not problems:
            return _record_to_invoice(record), []
        if attempt < MAX_RETRIES:
            messages.append(Message(
                role="user",
                content=f"That did not validate: {'; '.join(problems)}. Reply again with corrected JSON only.",
            ))
    return None, problems


def _three_way_match(invoice: ExtractedInvoice, po: PurchaseOrder, received: dict[str, int]) -> list[Discrepancy]:
    """The join and its three subtractions: quantity against goods received, unit price against
    the order, and the invoice's own stated total against its own lines, recomputed. A line the
    purchase order does not carry is flagged on its own, before any of the three subtractions run
    against it."""
    discrepancies: list[Discrepancy] = []
    if invoice.currency != po.currency:
        discrepancies.append(Discrepancy(
            kind="currency", code=None,
            detail=f"invoice is in {invoice.currency}, {po.po_number} was placed in {po.currency}",
        ))
    po_lines = {line.code: line for line in po.lines}
    for line in invoice.lines:
        po_line = po_lines.get(line.code)
        if po_line is None:
            discrepancies.append(Discrepancy(
                kind="unknown_line", code=line.code,
                detail=f"{line.code} is not a line on {po.po_number}",
            ))
            continue
        received_qty = received.get(line.code, 0)
        if line.quantity != received_qty:
            discrepancies.append(Discrepancy(
                kind="quantity", code=line.code,
                detail=f"{line.code}: invoiced {line.quantity}, received {received_qty} ({line.quantity - received_qty:+d})",
            ))
        price_diff = line.unit_price_cents - po_line.unit_price_cents
        if abs(price_diff) > TOLERANCE_CENTS:
            discrepancies.append(Discrepancy(
                kind="unit_price", code=line.code,
                detail=f"{line.code}: invoiced at {line.unit_price_cents} cents, ordered at "
                       f"{po_line.unit_price_cents} cents ({price_diff:+d} cents)",
            ))
    recomputed = sum(line.quantity * line.unit_price_cents for line in invoice.lines)
    total_diff = invoice.stated_total_cents - recomputed
    if abs(total_diff) > TOLERANCE_CENTS:
        discrepancies.append(Discrepancy(
            kind="total", code=None,
            detail=f"invoice states {invoice.stated_total_cents} cents but its own "
                   f"{len(invoice.lines)} line(s) sum to {recomputed} cents ({total_diff:+d} cents)",
        ))
    return discrepancies


def _pause(tracer: Tracer, invoice: ExtractedInvoice | None, po_number: str, reasons: tuple[str, ...], stage: Stage) -> PendingMatch:
    tracer.record(kind="code", decided_by="code", title="Pause for accounts payable review", detail="; ".join(reasons))
    return PendingMatch(invoice=invoice, po_number=po_number, reasons=reasons, stage=stage)


def run(
    invoice_text: str,
    model: Model,
    tracer: Tracer,
    *,
    purchase_orders: dict[str, PurchaseOrder] = PURCHASE_ORDERS,
    goods_received: dict[str, tuple[ReceivedLine, ...]] = GOODS_RECEIVED,
) -> PostedInvoice | PendingMatch:
    invoice, problems = _extract_invoice(invoice_text, model, tracer)
    if invoice is None:
        return _pause(tracer, None, "", tuple(problems), "extraction_failed")

    po = purchase_orders.get(invoice.po_number)
    tracer.record(kind="code", decided_by="code", title="Look up the purchase order",
                  detail=f"{invoice.po_number}: found" if po else f"{invoice.po_number}: not on file")
    if po is None:
        return _pause(tracer, invoice, invoice.po_number, (f"no purchase order {invoice.po_number!r} on file",), "unknown_po")

    received = {line.code: line.quantity_received for line in goods_received.get(po.po_number, ())}
    discrepancies = _three_way_match(invoice, po, received)
    tracer.record(kind="code", decided_by="code", title="Compare invoiced, ordered and received",
                  detail="; ".join(d.detail for d in discrepancies) or "no discrepancies")
    if discrepancies:
        return _pause(tracer, invoice, po.po_number, tuple(d.detail for d in discrepancies), "mismatch")

    tracer.record(kind="code", decided_by="code", title="Post to accounts payable",
                  detail=f"{po.po_number} {invoice.invoice_number}: {invoice.stated_total_cents} cents")
    return PostedInvoice(
        po_number=po.po_number, invoice_number=invoice.invoice_number,
        supplier=invoice.supplier, posted_cents=invoice.stated_total_cents,
    )


def resume(pending: PendingMatch, decision: Decision, tracer: Tracer, *, note: str = "") -> PostedInvoice | RejectedInvoice:
    """A second, separate call: a person's decision on a paused match becomes the final
    disposition. `approve` posts the invoice as the supplier stated it, on the reviewer's own
    authority, which is why the trace records the decision rather than the code re-deciding
    anything. `reject` sends it back unposted."""
    tracer.record(
        kind="code", decided_by="code", title="Resume from checkpoint with the reviewer's decision",
        detail=f"decision={decision}" + (f" note={note!r}" if note else ""),
    )
    if decision == "approve":
        if pending.invoice is None:
            raise ValueError("cannot post a match that never extracted valid fields; ask the supplier to resend")
        return PostedInvoice(
            po_number=pending.invoice.po_number, invoice_number=pending.invoice.invoice_number,
            supplier=pending.invoice.supplier, posted_cents=pending.invoice.stated_total_cents,
        )
    invoice_number = pending.invoice.invoice_number if pending.invoice else "(none extracted)"
    return RejectedInvoice(po_number=pending.po_number, invoice_number=invoice_number, reason=note or "rejected by accounts payable")
