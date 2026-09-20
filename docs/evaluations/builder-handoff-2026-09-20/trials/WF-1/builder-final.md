# Workflow specification: Friday three-project report

## Evidence status

**Confirmed from the brief:** a Friday run covers three projects; it collects issue records, team notes, and the previous report; it produces a reviewable draft with **Progress, Risks, Decisions, Next week**; each claim has dated source links; stale, missing, and contradictory information is flagged; no email or publication happens automatically; the user reviews before sending. The attached files are accessible and explicitly synthetic. Their contents are fixtures, not live project facts.

**Proposed defaults:** run at 09:00 in the user’s local time; accept CSV exports and plain-text notes; treat data as fresh for seven days unless the user sets another threshold; write the draft beside the collected inputs; use project keys Alpha, Beta, and Gamma, with “A-team” as a reviewable alias for Alpha. These defaults require confirmation during setup.

**Untested assumptions:** connected systems, destination folder, recipient list, exact freshness threshold, issue-state vocabulary, and whether a human can resolve aliases or conflicts in the source systems. No external access was available in this build.

## Trigger-to-destination

```text
Friday schedule
  -> collect permitted issue export + team notes + previous report
  -> normalize project names/fields and retain source URLs + dates
  -> validate freshness, completeness, duplicates, and contradictions
  -> synthesize four sections with claim-level citations
  -> draft saved to configured review destination
  -> user reviews, corrects/approves, and sends manually
```

The run stops at the draft. Sending, publishing, changing issue records, and changing notes are outside authorization.

## Stages and human effort

| Stage | Input | System action | Output | Required human action and frequency |
|---|---|---|---|---|
| Setup | source locations, schedule, freshness rule, destination | configure connectors, project aliases, schema mappings, and permissions | tested workflow configuration | Provide/confirm once at setup; resolve connector access if needed |
| Collect | issue records/exports, notes, previous report | fetch or read each source; retain retrieval time, source link, and raw copy; retry each source twice | run manifest and raw inputs | None per run; provide a replacement input only when a source is unavailable |
| Normalize | raw inputs | map columns, parse dates/statuses, match aliases, identify unknown projects, deduplicate by stable ID or source+title+date | normalized records plus mapping warnings | Review only flagged alias or mapping items, per flagged item |
| Validate | normalized records | check required fields, seven-day freshness default, duplicate IDs, missing project coverage, and conflicting status/owner/date claims | issue list with severity and citations | Review every blocking warning per run; choose a source or mark unresolved |
| Synthesize | validated records and prior report format | draft Progress, Risks, Decisions, Next week; cite every factual claim with dated source links; label unknowns and unresolved conflicts | review draft and evidence appendix | Review/edit/approve once per output; sending remains manual |
| Recover | manifest and partial outputs | resume from last successful stage; avoid duplicate records and preserve prior draft versions | complete draft or actionable failure report | Replace failed input or rerun failed stage, per failure |

## Exception policy

Missing source, stale input, unmapped project, malformed row, or unresolved contradiction is never silently repaired. Mark it `needs review`, preserve the original value and source, and downgrade affected prose to “unknown” or omit it. Do not infer closure from silence. A source retries twice with backoff; then the run continues for independent projects but cannot claim complete coverage. A failed normalization or synthesis stage blocks delivery of a draft and emits the manifest plus error details. Duplicate prevention uses stable issue IDs where available and a reviewable composite key otherwise. A partial run resumes using the manifest and an idempotent run ID. Previous-report owners and dates are formatting examples only and are never copied as current facts.

## Authorization boundaries

Permitted: read configured inputs, create a local draft, preserve source links, and write run logs. Required approval: initial connector setup, destination choice, alias mappings, freshness threshold, and conflict resolutions. Prohibited without a separate explicit instruction: send email, publish, modify issue records or notes, alter source permissions, or treat a draft as approved.

## Complete first version

Support one CSV issue export, one plain-text notes file, and one previous Markdown report for exactly three projects. Use a manually supplied alias map and a local output folder. Implement the Friday trigger, raw-input manifest, normalization, seven-day freshness warning, duplicate detection, contradiction flags, cited four-section draft, resumable run ID, and a human review gate. Verify completion by opening the draft at the configured destination and checking that all three project headings, four required sections, dated source links, and warning statuses are present. Optional later improvements include more connectors, richer schema inference, and automatic alias suggestions; they must not remove the review gate.
