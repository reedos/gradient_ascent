# Builder response 1

I could access `artifact.md` and `attachments.json`. The three explicitly named fixtures (`receipt-us.jpg`, `receipt-eur.jpg`, and `receipt-notes.txt`) were absent at the declared paths, so their descriptions are recorded as unverified reference metadata. I did not execute tests or inspect other trial material.

Confirmed requirements: define reviewable acceptance checks for phone photos, PDFs, and scans in USD, CAD, and EUR; cover taxes, tips, refunds, handwritten notes, and unreadable or partial images; preserve uncertainty and route uncertain records to human review; use synthetic fixtures; and avoid invented values or silent currency conversion.

Proposed defaults, pending approval: record-level extraction error ≤1% on a labeled synthetic set for present fields; field-level exact-match reporting for merchant, date, currency, subtotal, tax, tip, total, refund, and line items; preserve source currency and store conversion as a separate optional value; never guess obscured values; reject or review duplicates using a stable image/document fingerprint plus human confirmation; represent missing merchant/date as null with a reason code; and require both totals and line items when present. These are proposals, not settled policy.

Acceptance matrix (all status values are **Not run**):

| Requirement | Test input | Expected behavior | Evidence | Judge | Status |
|---|---|---|---|---|---|
| Readable USD with tax/tip | Supplied readable USD fixture (currently unavailable) | Extract present fields, retain USD, distinguish tax and tip, reconcile total under agreed tolerance | Raw output, field assertions, reconciliation log | Deterministic check plus reviewer | Not run |
| Phone photo, PDF, scan | One fixture of each format | Same schema and uncertainty behavior across formats | Input manifest and normalized records | Deterministic | Not run |
| CAD handwritten tip/refund | Supplied notes fixture (currently unavailable) | Mark handwriting provenance; classify tip/refund; retain CAD; expose uncertainty for review | Record JSON and review decision | Human reviewer for handwriting/classification | Not run |
| Partial EUR | Supplied obscured fixture (currently unavailable) | Set obscured date/total incomplete; do not infer; route record to review; retain EUR | Missing-field reason codes and queue event | Deterministic plus human review | Not run |
| Missing/conflicting fields | Synthetic variants | Null plus reason code, conflict flag, and review route; no invented merchant/date/amount | Assertions and audit trail | Deterministic | Not run |
| Duplicate/repeat run | Same input twice and near-duplicate | Apply approved duplicate policy; repeat is idempotent and auditable | Fingerprints, IDs, run log | Deterministic | Not run |
| Error threshold | Labeled synthetic corpus | Report field and record error rates against approved threshold | Evaluation report | Reviewer | Not run |

Manual-effort plan: start the timer immediately before fixture import; stop after the automated result and queue are visible. Record machine waiting separately. For each queued record, time required review from opening the record to accept/correct/reject and save; optional corrections are timed separately. Report median and p95 review time per record, setup time once per run, and number of required reviewer actions. No timing has been performed.

Three material questions block a final policy: (1) What extraction-error threshold and fields count toward it? (2) Which exchange-rate source and timing apply, if conversion is required? (3) Should acceptance cover both totals and line items, and what accounting period/shared-organizer/output schema should be used?
