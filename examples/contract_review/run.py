"""Level 3: check an agreement against a checklist a team wrote down in advance, one call per
rule, over the same agreement, in parallel. Every call sees exactly one rule and the whole
agreement; it never sees the other rules and never sees what another call answered.

The schema each call must fill is fixed: which rule, a status from a closed set (`breach`,
`meets`, `missing` or `unclear`), the clause number the answer relies on, and a verbatim quote
from that clause. Code, not the model, decides whether a returned finding actually ships as
drafted: a quote that is not a substring of the clause it names is not the clause supporting the
finding, and a clause number the agreement does not have is not a citation at all. Either downgrades
the finding to `unclear` with the reason recorded, rather than shipping a citation nobody checked.
`missing` is a different answer from all three others and is never downgraded for lacking a
clause: it is what a rule with no clause addressing it at all looks like, and code has to keep it
distinct from `unclear` (a clause exists but does not say enough) and from `meets` (a person
reading a "no action needed" list should not have to notice that a required protection was never
mentioned).

Every step here is `decided_by="code"`: the number of calls, which rule each one gets and how the
results are checked and merged are all fixed before the first call goes out, the same shape as
`examples/parallelization/run.py`. What comes back from `run` is a checkpoint, never a final
verdict: every `breach`, `missing` and `unclear` finding needs a person before anything happens to
it, and `resume` is where that person's decision is recorded, the same shape as
`examples/human_in_the_loop/run.py`.
"""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Literal

from examples.common.model import Completion, Message, Model
from examples.common.trace import Tracer

LEVEL = 3

Status = Literal["breach", "meets", "missing", "unclear"]
Decision = Literal["acknowledged", "sent_back"]
_STATUSES = frozenset({"breach", "meets", "missing", "unclear"})

#: An invented fifteen-clause services agreement. Every clause is one line (no embedded newline),
#: which is what lets `_parse_clauses` find clause boundaries with one regex and lets a finding's
#: quote be checked as a plain substring of the clause it names. No real company, product or
#: amount appears here.
AGREEMENT_CLAUSES: dict[int, str] = {
    1: "Parties. This Agreement is between Lucerne Outfitters LLC, a Vermont limited liability "
       "company (\"Client\"), and Marrow Fulfillment Co., a Delaware corporation (\"Vendor\").",
    2: "Purpose. Vendor will provide order fulfillment and warehousing services for Client's "
       "retail products as described in Exhibit A.",
    3: "Term. This Agreement begins on the Effective Date and continues for twenty-four (24) "
       "months unless terminated earlier under Section 7 or Section 8.",
    4: "Services. Vendor will receive, store, pick, pack and ship Client's inventory in "
       "accordance with the service levels in Exhibit A.",
    5: "Payment Terms. Client shall pay each Vendor invoice within forty-five (45) days of the "
       "invoice date. Amounts unpaid after that period accrue interest at 1% per month.",
    6: "Fees. The monthly service fee is $4,200, plus the per-order fulfillment fees set out in "
       "Exhibit A.",
    7: "Termination for Convenience. Either party may terminate this Agreement for convenience "
       "upon sixty (60) days' prior written notice to the other party.",
    8: "Termination for Cause. Either party may terminate this Agreement immediately upon "
       "written notice if the other party materially breaches this Agreement and fails to cure "
       "within fifteen (15) days.",
    9: "Limitation of Liability. Except for breaches of Section 11 (Confidentiality), Vendor's "
       "total liability arising under this Agreement shall not exceed the fees paid by Client in "
       "the twelve (12) months preceding the event giving rise to the claim.",
    10: "Indemnification. Each party will indemnify the other against third-party claims arising "
        "from its own negligence or willful misconduct in performing this Agreement.",
    11: "Confidentiality. Each party will hold the other's confidential information in "
        "confidence and use it only to perform this Agreement, for five (5) years after "
        "disclosure.",
    12: "Assignment. Either party may assign this Agreement, in whole or in part, to any third "
        "party without the other party's consent, provided the assigning party remains liable "
        "for its own obligations.",
    13: "Governing Law. This Agreement is governed by the laws of the state in which Vendor "
        "maintains its principal place of business, without regard to conflict of laws "
        "principles.",
    14: "Notices. Notices under this Agreement must be in writing and delivered by email with "
        "confirmation of receipt, or by certified mail.",
    15: "Entire Agreement. This Agreement, with its Exhibits, is the entire agreement between "
        "the parties and supersedes all prior agreements on the subject.",
}
AGREEMENT_TEXT = "\n".join(f"{n}. {AGREEMENT_CLAUSES[n]}" for n in sorted(AGREEMENT_CLAUSES))

SAMPLE_INPUT = AGREEMENT_TEXT
_CLAUSE_LINE_RE = re.compile(r"^(\d+)\.\s+(.+)$", re.MULTILINE)


@dataclass(frozen=True)
class Rule:
    id: str
    text: str


#: The checklist. Written down once, in advance, and run unchanged against any agreement: that
#: fixed list is what keeps this recipe at level 3 rather than needing a model to decide what to
#: check. payment_terms is clearly breached by clause 5 (45 days against a 30-day limit),
#: liability_cap is clearly met by clause 9, and data_deletion has no clause about it anywhere in
#: the agreement, which is a `missing` finding rather than a `meets` or a `breach`.
CHECKLIST: tuple[Rule, ...] = (
    Rule("payment_terms", "Invoices must be payable within 30 days of receipt."),
    Rule(
        "liability_cap",
        "Vendor's total liability must be capped at no more than the fees Client paid in the "
        "twelve months before the claim.",
    ),
    Rule(
        "notice_period",
        "Either party must be able to terminate for convenience on at least 30 days' written "
        "notice.",
    ),
    Rule(
        "assignment",
        "Neither party may assign the agreement to a third party without the other party's "
        "prior written consent.",
    ),
    Rule(
        "governing_law",
        "The agreement must name one specific state's law as governing, not a formula that "
        "depends on where a party happens to be.",
    ),
    Rule("data_deletion", "Vendor must delete or return all of Client's data within 30 days of termination."),
)

FINDING_SCHEMA = {
    "type": "object",
    "properties": {
        "rule": {"type": "string"},
        "status": {"type": "string", "enum": ["breach", "meets", "missing", "unclear"]},
        "clause": {"type": ["integer", "null"]},
        "quote": {"type": "string"},
    },
    "required": ["rule", "status", "clause", "quote"],
}
RULE_SYSTEM = (
    "You are checking a contract against exactly one checklist rule. You do not see any other "
    "rule and must not invent facts the agreement does not state. Decide whether the agreement "
    "meets the rule, breaches it, is missing (no clause addresses it at all), or is unclear from "
    "the text given. Cite the single clause number your answer relies on and quote the exact "
    "words from that clause that support it, copied verbatim. If no clause addresses the rule, "
    "use status 'missing' with clause null and an empty quote. Reply as JSON matching the schema "
    "and nothing else."
)


@dataclass(frozen=True)
class Finding:
    """One rule's outcome. `note` is set only when code downgraded what the model returned, and
    says why; a finding the model's own reply supports as drafted carries no note."""

    rule: str
    status: Status
    clause: int | None
    quote: str
    checked_by: Literal["code", "model"]
    note: str = ""


@dataclass(frozen=True)
class ReviewCheckpoint:
    """What `run` hands back: every finding, split into the ones a person has to look at and the
    ones that need no action. Nothing here is a decision to sign the agreement or not; it is the
    list a person reads before they make one."""

    agreement: str
    findings: tuple[Finding, ...]
    needs_review: tuple[Finding, ...]
    cleared: tuple[Finding, ...]


@dataclass(frozen=True)
class ReviewRecord:
    agreement: str
    findings: tuple[Finding, ...]
    reviewer_decision: Decision
    note: str


def _parse_clauses(text: str) -> dict[int, str]:
    """The agreement's own numbered clauses, keyed by number. Only `_CLAUSE_LINE_RE` decides
    where a clause starts; nothing here re-derives a clause's meaning."""
    return {int(n): body.strip() for n, body in _CLAUSE_LINE_RE.findall(text)}


def _prompt_for_rule(rule: Rule, agreement_text: str) -> str:
    """The whole of what one call sees: this rule, alone, and the agreement. No other rule's id
    or text appears here, which is what a test can check directly against this function's output
    without running a model at all."""
    return f"Checklist rule {rule.id}: {rule.text}\n\nAgreement:\n{agreement_text}"


def _check_rule(rule: Rule, agreement_text: str, model: Model) -> Completion:
    prompt = _prompt_for_rule(rule, agreement_text)
    return model.complete(
        [Message(role="system", content=RULE_SYSTEM), Message(role="user", content=prompt)],
        schema=FINDING_SCHEMA,
        max_tokens=300,
    )


def _merge_finding(rule: Rule, completion: Completion, clauses: dict[int, str]) -> Finding:
    """The check this recipe teaches. A finding ships as drafted only if its status is one of the
    four allowed, and, for anything but `missing`, only if the clause it names exists in this
    agreement and the quote is an exact substring of that clause's own text -- not of the
    agreement as a whole, so a real sentence lifted from a different clause than the one cited
    still fails this check."""
    try:
        raw = json.loads(completion.text)
    except (json.JSONDecodeError, TypeError):
        return Finding(rule=rule.id, status="unclear", clause=None, quote="", checked_by="code",
                        note="the model's reply was not valid JSON")

    status = raw.get("status")
    clause_no = raw.get("clause")
    quote = raw.get("quote") or ""

    if status not in _STATUSES:
        return Finding(rule=rule.id, status="unclear", clause=clause_no if isinstance(clause_no, int) else None,
                        quote=quote, checked_by="code",
                        note=f"the model returned a status outside breach/meets/missing/unclear: {status!r}")
    if status == "missing":
        return Finding(rule=rule.id, status="missing", clause=None, quote="", checked_by="model")
    if not isinstance(clause_no, int) or clause_no not in clauses:
        return Finding(rule=rule.id, status="unclear", clause=clause_no if isinstance(clause_no, int) else None,
                        quote=quote, checked_by="code",
                        note=f"cites clause {clause_no!r}, which this agreement does not have")
    if not quote or quote not in clauses[clause_no]:
        return Finding(rule=rule.id, status="unclear", clause=clause_no, quote=quote, checked_by="code",
                        note=f"the quoted text does not appear in clause {clause_no}")
    return Finding(rule=rule.id, status=status, clause=clause_no, quote=quote, checked_by="model")


def run(
    agreement_text: str,
    model: Model,
    tracer: Tracer,
    *,
    checklist: tuple[Rule, ...] = CHECKLIST,
) -> ReviewCheckpoint:
    text = agreement_text.strip() if isinstance(agreement_text, str) and agreement_text.strip() else AGREEMENT_TEXT
    clauses = _parse_clauses(text)
    tracer.record(kind="code", decided_by="code", title="Read the agreement",
                  detail=f"{len(clauses)} numbered clauses, {len(checklist)} checklist rules")

    # One call per rule, all sent at once; each sees only its own rule and the whole agreement.
    with ThreadPoolExecutor(max_workers=len(checklist)) as pool:
        completions = list(pool.map(lambda r: _check_rule(r, text, model), checklist))

    for rule, completion in zip(checklist, completions):
        tracer.record(kind="model", decided_by="code", title=f"Check {rule.id} alone",
                       detail=completion.text[:200], tokens_in=completion.tokens_in,
                       tokens_out=completion.tokens_out, ms=completion.ms)

    findings = tuple(_merge_finding(rule, completion, clauses) for rule, completion in zip(checklist, completions))
    tracer.record(kind="code", decided_by="code", title="Check every quote against its cited clause",
                   detail=", ".join(f"{f.rule}:{f.status}" for f in findings))

    needs_review = tuple(f for f in findings if f.status != "meets")
    cleared = tuple(f for f in findings if f.status == "meets")
    tracer.record(kind="code", decided_by="code",
                   title="Gate: every breach, missing and unclear finding goes to a person",
                   detail=f"{len(needs_review)} to review, {len(cleared)} cleared")
    return ReviewCheckpoint(agreement=text, findings=findings, needs_review=needs_review, cleared=cleared)


def resume(checkpoint: ReviewCheckpoint, decision: Decision, tracer: Tracer, *, note: str = "") -> ReviewRecord:
    tracer.record(kind="code", decided_by="code", title="Resume from checkpoint with the reviewer's decision",
                   detail=f"decision={decision}" + (f" note={note!r}" if note else ""))
    return ReviewRecord(agreement=checkpoint.agreement, findings=checkpoint.findings,
                         reviewer_decision=decision, note=note)
