# Acceptance proposal: wildlife photo packs

This provisional matrix uses only `artifact.md` and synthetic attachment content in `attachments.json`. No workflow or fixture was executed. Confirmed requirements are preserved originals, traceable derivatives, coherent packs, crops/resizes, metadata, optional map end cards, visible exceptions, location privacy, and phone review. The reviewer judges subjective quality and readiness.

Proposed defaults are decision aids, not approved guarantees. Exact quality, crop-failure, location, dimension, timing, volume, delivery, and storage thresholds remain unresolved.

| Requirement | Test input | Expected behavior | Evidence | Judge | Status |
|---|---|---|---|---|---|
| Preserve originals | A pack containing readable originals, including a repeated run | Originals remain byte-identical and available after processing and reprocessing | Before/after hashes, inventory, run log | Deterministic check by implementer; reviewer confirms availability | Not run |
| Trace every derivative | Synthetic manifest shown in `attachments.json`: `wildlife-01.jpg` → `carousel-01/01.jpg`; `wildlife-02.jpg` → `carousel-01/02.jpg` | Every crop, resize, metadata record, and end card has an unambiguous original identifier; no orphan output | Manifest with source IDs, derivative paths, and lineage validation report | Implementer checks; reviewer samples links | Not run |
| Produce coherent packs | Originals from one encounter plus a mixed-subject boundary set | Grouping is understandable; duplicate subjects and unrelated images are excluded or flagged | Contact sheet, grouping rationale, duplicate/subject flags | Reviewer, with deterministic duplicate checks as support | Not run |
| Acceptable crops | Portrait, landscape, close subject, edge subject, and subject partly occluded | Requested crop/export exists when useful; poor or ambiguous crops are rejected or visibly flagged for correction | Contact sheet at review size, crop warnings, rejected-item list | Reviewer judges usefulness; implementer records failures | Not run |
| Resized exports and dimensions | Representative aspect ratios, plus tiny and unusually large files | Outputs open on a phone and match approved carousel dimensions or are flagged | Inventory, dimensions, decode/open check, phone review notes | Deterministic checks plus reviewer; dimensions pending approval | Not run |
| Metadata included | Files with available capture time, camera data, and non-exact location information; one file missing each field | Available metadata is retained or represented accurately; absent values stay absent; no invented facts | Metadata extraction report and sidecar/embedded comparison | Implementer for field fidelity; reviewer for practical usefulness | Not run |
| Protect location privacy | Exact coordinates, coarse location, conflicting fields, and no location | Exact coordinates are never exposed; map/end-card location is coarse and conflicts or absence are visible | Redacted metadata inspection, end card, exception log | Reviewer/privacy judge; deterministic scan supports it | Not run |
| Optional map end card | Pack with a suitable coarse location, pack with no location, and pack with conflicting locations | End card appears only when appropriate and approved; otherwise it is omitted or marked unavailable, never guessed | Pack inventory, rendered end card, decision/exception record | Reviewer | Not run |
| Show exceptions | Crop failure, missing metadata, conflicting location, duplicate subject, partial export failure | Each exception is visible beside the item or in a linked report; incomplete packs are not presented as complete | Exception report, pack status, logs | Reviewer verifies visibility and actionability | Not run |
| Safe repeated execution | Run the same input twice, then add one new original | Existing originals and accepted derivatives are not overwritten unexpectedly; results are stable or changes are explained | Run IDs, hashes, diffed manifests, collision report | Implementer checks; reviewer inspects changed items | Not run |
| Boundary and prohibited actions | Read-only source location, attempted overwrite/delete target, malformed file, and unsupported format | Workflow refuses destructive or unsupported action, preserves source, and reports the reason | Command/run log, source hash, error and exception records | Deterministic check, with reviewer confirmation | Not run |
| Phone review and sharing readiness | Completed pack containing normal outputs and visible exceptions | Pack can be located and reviewed on a phone; ordering, text, and warnings are legible; reviewer can decide share/hold | Phone review checklist, access path, screenshots or notes, final disposition | Reviewer | Not run |

## Manual-effort measurement plan

For three representative runs (normal, exception-heavy, repeated), record timestamps separately for setup, machine waiting, required review, required correction, optional correction, and final share/hold decision. Start setup when input preparation begins; stop when launch is possible. Start machine waiting when processing begins; stop when outputs are available. Start required review on first pack open; stop when every required criterion has a disposition. Record correction only when needed for acceptance, and optional polish separately. Exclude unrelated idle time.

Report per-run and median values, plus image count and exception count. Proposed reporting targets are descriptive only: required review time per pack and correction rate should be measured before any service-level promise is made. Timing, weekly volume, delivery service, and phone-storage limits are unresolved unknowns.

## Open decisions and assumptions

Assumptions: “coherent” is a reviewer judgment; “appropriate” map use requires a privacy-approved coarse-location rule; and “phone review” means the reviewer can open the pack without a desktop dependency. Hashes, lineage, decodability, dimensions, metadata comparison, and coordinate scans support checks but do not establish visual quality.

The embedded synthetic manifest and review note are reference examples, not executed fixtures. The paths `sample-manifest.csv` and `review-notes.md` listed in `attachments.json` were not accessible at the trial location, so their contents cannot be independently verified.
