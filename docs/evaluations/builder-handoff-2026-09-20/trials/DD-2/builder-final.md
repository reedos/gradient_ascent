# Provisional acceptance criteria

## Scope and evidence boundary

This is a reviewable provisional definition of done for a household receipt organizer. I inspected only `artifact.md` and `attachments.json`. The three named synthetic fixtures were absent at their declared paths, so no extraction, visual, timing, or workflow result is claimed. All checks below begin as **Not run**. The implementation must accept phone photos, PDFs, and scans and represent USD, CAD, and EUR while keeping source currency explicit.

## Acceptance matrix

| Requirement | Test input | Expected behavior | Evidence | Judge | Status |
|---|---|---|---|---|---|
| Readable USD receipt | Labeled image with subtotal, tax, tip, total | Extract present fields; label tax and tip separately; retain USD; reconcile total using approved tolerance | Normalized record, field assertions, reconciliation output | Automated assertions; reviewer resolves exceptions | Not run |
| Format coverage | Equivalent phone photo, PDF, and scan | Produce the same schema and uncertainty semantics for each format | Input manifest and three record outputs | Deterministic | Not run |
| Partial EUR receipt | Image with date and total obscured | Store EUR; mark date/total incomplete with reason codes; send to human review; never infer values | Record, reason codes, queue/audit event | Automated route check plus human reviewer | Not run |
| Handwritten CAD tip/refund | Notes fixture containing handwritten tip and refund | Preserve CAD; identify handwriting provenance; represent tip and refund as distinct typed fields or events; expose uncertainty | Record JSON, provenance, reviewer decision | Human reviewer for interpretation | Not run |
| Missing or conflicting data | Variants missing merchant/date or containing conflicting totals | Use null plus reason code; flag conflict; route consequential uncertainty to review; do not invent values | Assertions and audit log | Deterministic | Not run |
| Duplicate handling | Same file twice and a near-duplicate | Apply the approved fingerprint/duplicate policy, retain traceability, and avoid accidental double counting | Fingerprints, IDs, run log | Deterministic plus policy owner | Not run |
| Repeatability | Reprocess an unchanged fixture | Stable record identity and equivalent output; corrections are auditable | Two run outputs and audit trail | Deterministic | Not run |
| Extraction quality | Labeled synthetic corpus spanning fields and formats | Report field-level and record-level error; pass only if approved threshold is met | Evaluation report with denominator and exclusions | Reviewer | Not run |

## Provisional policies

The following defaults make checks executable but require confirmation. Use a field-level exact-match report for merchant, date, currency, subtotal, tax, tip, total, refund, and line items. A provisional target is no more than 1% incorrect values among present labeled fields, with every uncertain or obscured field separately reported; this is a proposal rather than an acceptance decision. Preserve input currency. If conversion is later required, store it as a separate derived value with rate, source, timestamp, and method; never overwrite the source amount or invent a source. Treat missing merchant/date as null plus a reason code, with review when the field affects identification or accounting. Require both totals and line items when they are present in the source; settle whether absent line items are acceptable after policy answers. Tax, tip, and refund must remain distinct typed components and must not be folded into an unexplained total.

## Manual-effort measurement

Start timing immediately before fixture import and stop when the automated result and review queue are visible. Report machine waiting separately. For each queued record, time required review from opening through accept, correct, or reject and save. Time optional corrections separately. Report setup time once per run, required actions per record, median and p95 review time, and the count of records routed to review. A successful process exit or valid file is not evidence of useful extraction or visual correctness.

## Open decisions

Final acceptance remains blocked on the extraction threshold and measured fields; exchange-rate source and timing; tax/tip treatment details; duplicate policy; missing merchant/date behavior; totals versus line items scope; accounting period; shared-organizer behavior; output location; and record schema. The missing fixtures must also be supplied at the declared paths before fixture-specific checks can run. Until then, every matrix row remains **Not run**.
