"""Level 0: no model. Read the household's own records, and answer the four questions people
actually have about their paperwork with a sort, a subtraction and a sum.

Every part of this is arithmetic somebody already has the numbers for:

- What renews soon is a date subtraction against a window (`renewals_due`).
- What is owed is a filter on a flag and a date, with anything dated before the report date
  marked overdue (`unpaid_bills`).
- What it all costs a year is a multiplication and a sum per category (`yearly_cents`,
  `yearly_by_category`). This is the one place a unit mistake is easy: a quarterly premium and a
  monthly subscription are not comparable until both are a year.
- What is missing from the folder is a regular expression and a set difference (`misfiled`).

Money is integer cents everywhere. A household budget in floats accumulates a rounding error
that shows up as a total nobody can reconcile against their own statements.

`model` is accepted and never used: `del model` on the first line of `run`, the same way
`examples/order_zero/run.py` does it. The signature is the one every example here shares so
`scripts/record_trace.py` can record this one, not a hint that a model belongs in it. Every step
is `decided_by="code"`, and there is nothing in this file for a model to decide.

The records below are invented. No real insurer, utility, subscription or bank appears here, and
no amount is anybody's actual bill.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

from examples.common.model import Model
from examples.common.trace import Tracer

LEVEL = 0

#: The date the report is run for. Passing a date in rather than reading the clock is what makes
#: this example's output the same in a test today and in a test next year.
AS_OF = date(2026, 9, 19)
RENEWAL_WINDOW_DAYS = 30

#: How many times a year each period is paid. A one-off (a warranty already bought, a repair) is
#: a real cost and not a yearly one, so it is counted nowhere in the yearly totals and the report
#: says so rather than quietly folding it in.
PER_YEAR = {"monthly": 12, "quarterly": 4, "yearly": 1, "one-off": 0}

#: The folder's naming rule: date, provider, kind. A file that does not match is not wrong, it is
#: unfindable, which is the same thing at the moment somebody needs it.
FILE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_[a-z0-9-]+_[a-z0-9-]+\.pdf$")


@dataclass(frozen=True)
class Record:
    """One commitment or bill. `date` is the renewal date for anything that renews and the due
    date for anything owed; `auto_renew` is what turns the first kind into a deadline."""

    id: str
    provider: str
    category: str
    amount_cents: int
    period: str
    due: date
    auto_renew: bool = False
    paid: bool = True
    document: str | None = None


RECORDS: tuple[Record, ...] = (
    Record("r01", "Thornfield Mutual", "insurance", 118_400, "yearly", date(2026, 10, 2), auto_renew=True,
           document="2025-10-02_thornfield-mutual_policy.pdf"),
    Record("r02", "Thornfield Mutual", "insurance", 6_450, "monthly", date(2026, 10, 1), auto_renew=True,
           document="2026-09-01_thornfield-mutual_statement.pdf"),
    Record("r03", "Brackle Water Board", "utilities", 9_120, "quarterly", date(2026, 10, 14), paid=False,
           document="2026-09-14_brackle-water-board_bill.pdf"),
    Record("r04", "Kestrel Power", "utilities", 14_780, "monthly", date(2026, 9, 12), paid=False,
           document="2026-09-01_kestrel-power_bill.pdf"),
    Record("r06", "Larkmoor Fiber", "utilities", 5_500, "monthly", date(2026, 10, 6), auto_renew=True,
           document="2026-09-06_larkmoor-fiber_invoice.pdf"),
    Record("r07", "Pellmore Reading Club", "subscriptions", 1_299, "monthly", date(2026, 10, 18), auto_renew=True,
           document="Pellmore receipt (2).pdf"),
    Record("r08", "Vantry Storage", "subscriptions", 24_000, "yearly", date(2026, 11, 30), auto_renew=True,
           document="2025-11-30_vantry-storage_renewal.pdf"),
    Record("r09", "Sableway Gym", "subscriptions", 3_900, "monthly", date(2026, 10, 9), auto_renew=True,
           document=None),
    Record("r10", "Ambernook Appliance", "warranty", 8_900, "one-off", date(2026, 12, 4),
           document="2024-12-04_ambernook-appliance_warranty.pdf"),
    Record("r11", "Ambernook Appliance", "warranty", 2_400, "yearly", date(2027, 1, 20), auto_renew=True,
           document="2026-01-20_ambernook-appliance_cover.pdf"),
    Record("r12", "Dunmore Council", "utilities", 21_600, "yearly", date(2027, 4, 1), paid=False,
           document="2026-04-01_dunmore-council_charge.pdf"),
)

#: What is actually in the documents folder. Two of these break the naming rule, and one record
#: (r09) has no document at all, which is a different problem with the same consequence. There is
#: one row per commitment, not one per bill: entering this month's power bill and last month's as
#: two records would count the same commitment twice in the yearly total.
FOLDER: tuple[str, ...] = (
    "2025-10-02_thornfield-mutual_policy.pdf",
    "2026-09-01_thornfield-mutual_statement.pdf",
    "2026-09-14_brackle-water-board_bill.pdf",
    "2026-09-01_kestrel-power_bill.pdf",
    "2026-09-06_larkmoor-fiber_invoice.pdf",
    "Pellmore receipt (2).pdf",
    "2025-11-30_vantry-storage_renewal.pdf",
    "2024-12-04_ambernook-appliance_warranty.pdf",
    "2026-01-20_ambernook-appliance_cover.pdf",
    "2026-04-01_dunmore-council_charge.pdf",
    "scan_0043.pdf",
)

SAMPLE_INPUT = "2026-09-19"
_DATE_IN_TEXT = re.compile(r"\d{4}-\d{2}-\d{2}")


def as_of_from(asked: str) -> date:
    """The date this report is run for, read out of the request. Empty text means `AS_OF`; text
    with an ISO date in it means that date; text with something that looks like a date and is not
    one raises, because a report run for the wrong date is wrong everywhere and silently."""
    text = (asked or "").strip()
    if not text:
        return AS_OF
    match = _DATE_IN_TEXT.search(text)
    if match is None:
        raise ValueError(f"no date in {asked!r}; pass one as YYYY-MM-DD")
    return date.fromisoformat(match.group(0))


def money(cents: int) -> str:
    return f"${cents // 100:,}.{cents % 100:02d}"


def yearly_cents(record: Record) -> int:
    """What this record costs in a year. A period nobody priced yearly is zero, not a guess."""
    return record.amount_cents * PER_YEAR.get(record.period, 0)


def renewals_due(records, as_of: date, *, window_days: int = RENEWAL_WINDOW_DAYS) -> list[Record]:
    """Anything that renews itself on or before `as_of + window_days`, soonest first. The window
    is inclusive at both ends: a renewal on the last day of it is the one worth catching."""
    last = as_of + timedelta(days=window_days)
    due = [r for r in records if r.auto_renew and as_of <= r.due <= last]
    return sorted(due, key=lambda r: (r.due, r.id))


def unpaid_bills(records, as_of: date, *, window_days: int = RENEWAL_WINDOW_DAYS) -> list[tuple[Record, bool]]:
    """Every unpaid bill dated on or before the end of the window, with a flag for the ones
    already past their date."""
    last = as_of + timedelta(days=window_days)
    rows = [(r, r.due < as_of) for r in records if not r.paid and r.due <= last]
    return sorted(rows, key=lambda row: (row[0].due, row[0].id))


def yearly_by_category(records) -> dict[str, int]:
    """Yearly cost per category, largest first. One-off amounts are left out: see PER_YEAR."""
    totals: dict[str, int] = {}
    for record in records:
        yearly = yearly_cents(record)
        if yearly:
            totals[record.category] = totals.get(record.category, 0) + yearly
    return dict(sorted(totals.items(), key=lambda kv: (-kv[1], kv[0])))


def largest_yearly(records, *, top: int = 2) -> list[Record]:
    priced = [r for r in records if yearly_cents(r)]
    return sorted(priced, key=lambda r: (-yearly_cents(r), r.id))[:top]


def misfiled(records, folder) -> tuple[list[str], list[Record]]:
    """Two ways a document is not there when it is needed: a file whose name breaks the folder's
    rule, and a record with no document filed against it at all."""
    unreadable = sorted(name for name in folder if not FILE_RE.match(name))
    missing = [r for r in records if r.document is None or r.document not in folder]
    return unreadable, missing


@dataclass(frozen=True)
class Report:
    as_of: date
    renewals: tuple[Record, ...]
    unpaid: tuple[tuple[Record, bool], ...]
    by_category: dict[str, int]
    largest: tuple[Record, ...]
    unreadable_files: tuple[str, ...]
    undocumented: tuple[Record, ...]

    @property
    def yearly_total_cents(self) -> int:
        return sum(self.by_category.values())

    @property
    def citations(self) -> list[str]:
        ids = [r.id for r in self.renewals] + [r.id for r, _ in self.unpaid]
        ids += [r.id for r in self.largest] + [r.id for r in self.undocumented]
        return sorted(set(ids))

    @property
    def text(self) -> str:
        lines = [f"Household paperwork as of {self.as_of.isoformat()}"]
        lines.append(f"Renews within {RENEWAL_WINDOW_DAYS} days:")
        lines += [f"  {r.due.isoformat()}  {r.provider}  {money(r.amount_cents)} {r.period}" for r in self.renewals]
        lines.append("Unpaid:")
        lines += [
            f"  {r.due.isoformat()}  {r.provider}  {money(r.amount_cents)}" + ("  OVERDUE" if late else "")
            for r, late in self.unpaid
        ]
        lines.append("Yearly cost by category:")
        lines += [f"  {cat}  {money(total)}" for cat, total in self.by_category.items()]
        lines.append(f"  total  {money(self.yearly_total_cents)}")
        lines.append("Largest yearly commitments:")
        lines += [f"  {r.provider}  {money(yearly_cents(r))}" for r in self.largest]
        lines.append("Not findable in the folder:")
        lines += [f"  file breaks the naming rule: {name}" for name in self.unreadable_files]
        lines += [f"  no document filed: {r.id} {r.provider}" for r in self.undocumented]
        return "\n".join(lines)


def run(asked: str, model: Model | None, tracer: Tracer, *, records=RECORDS, folder=FOLDER) -> Report:
    del model  # level 0: nothing here calls a model, and the pass or fail of a date is not a judgment
    as_of = as_of_from(asked)
    tracer.record(kind="code", decided_by="code", title="Read the records",
                  detail=f"{len(records)} records, {len(folder)} files, as of {as_of.isoformat()}")

    renewals = renewals_due(records, as_of)
    tracer.record(kind="code", decided_by="code", title=f"Sort by date, keep the next {RENEWAL_WINDOW_DAYS} days",
                  detail=", ".join(f"{r.id} {r.due.isoformat()}" for r in renewals) or "none")

    unpaid = unpaid_bills(records, as_of)
    tracer.record(kind="code", decided_by="code", title="Filter the unpaid rows and flag the late ones",
                  detail=", ".join(f"{r.id}{' late' if late else ''}" for r, late in unpaid) or "none")

    by_category = yearly_by_category(records)
    tracer.record(kind="code", decided_by="code", title="Normalize every amount to a year and sum by category",
                  detail=", ".join(f"{cat} {money(total)}" for cat, total in by_category.items()))

    unreadable, undocumented = misfiled(records, folder)
    tracer.record(kind="code", decided_by="code", title="Check the folder against its naming rule",
                  detail=f"{len(unreadable)} unreadable name(s), {len(undocumented)} record(s) with no document")

    return Report(
        as_of=as_of,
        renewals=tuple(renewals),
        unpaid=tuple(unpaid),
        by_category=by_category,
        largest=tuple(largest_yearly(records)),
        unreadable_files=tuple(unreadable),
        undocumented=tuple(undocumented),
    )
