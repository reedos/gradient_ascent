# Workflow audit proposal

## Evidence and limits

I inspected `artifact.md`, `attachments.json`, and its three explicit synthetic attachments. The registration export contains two rows for Ari Lee at `ari@example.test`, both for Harvest, with different phone numbers (`555-0101` and `555-0199`) and shifts (09:00 and 10:00). The schedule sample contains one Ari Lee / Harvest / 09:00 row. The access note says export and attendance are editable; scheduling permission and reminder authority are unknown. These examples establish a duplicate or conflict needing review. They do not establish the true identity, intended shift, data volumes, timings, permissions, or production behavior.

No live systems, logs, policies, or public concept sources were available or independently verified. Consequently, time saved, error reduction, match rate, and reliability are unmeasured. The proposal below labels estimates and uses the supplied examples only as test fixtures.

## Current-state map

1. A volunteer submits one form. The exact form, fields, validation, and event naming rules are unknown.
2. Registrations are manually copied into several spreadsheets for scheduling, accessibility needs, and attendance. This is documented in the brief; frequency and effort are unknown.
3. A coordinator reviews assignments before volunteers see them. This review is a confirmed requirement and includes judgment about conflicts.
4. The schedule is then exposed to volunteers, but publication authority and mechanism are unknown.

The recurring manual work is transcription across sheets, normalization of names/events/shifts, duplicate and conflict investigation, correction logging, and coordinator review. It creates waiting while copying and reviewing, rework when values disagree, and risk of a wrong assignment or mishandled sensitive accessibility information. These are process risks inferred from the supplied examples, not measured incident counts.

## Ranked options

1. **Review-gated staging and reconciliation (recommended).** Import an export into a staging table, preserve raw values, normalize event and shift values, flag duplicate/conflict candidates, and produce a coordinator queue. Approved changes can be applied to a controlled schedule view or copy. This has the best expected quality and reversibility for the stated needs; implementation effort is moderate and maintenance is a rules table plus audit log. Expected time savings are an estimate until measured.
2. **Fixed spreadsheet workflow.** Add protected staging, validation lists, duplicate formulas, and an approval column to existing sheets. This is the lowest effort and easiest to roll back, but recurring copying remains and cross-sheet drift may persist. Quality and reliability should improve only if people follow the workflow; no benefit is measured yet.
3. **Small integration.** Connect the export to staging and write approved records into the scheduling workbook, with an audit log. This may reduce transcription most, but needs confirmed permissions, field mapping, failure handling, and ownership. It carries higher implementation and maintenance effort, so it should follow a successful pilot.
4. **Agent-built or broad rewrite.** Defer. The problem is bounded and human approval is required; a new system would add validation, privacy, and maintenance surface before the basic rules and authority are known.

Each option still has recurring work. The first reduces repeated copying while retaining exception review; the second reduces error-prone edits but keeps more manual entry; the third reduces entry after approval but adds monitoring and integration upkeep; the fourth adds the most build and governance work.

## Recommended experiment and workflow design

Run a two-event or otherwise agreed small pilot using a copy or staging destination. Before the pilot, record a baseline for one comparable intake window: row count, time spent copying, number of corrections, unresolved conflicts, and time from export to coordinator-ready schedule. These are proposed measurements, not existing results. Load the export without overwriting raw fields. Normalize only through documented mappings. Use a proposed matching key of normalized email plus human review; this is an assumption, not an approved identity policy. Flag changed contact details, same-person different shifts, missing values, and unknown event names. Never merge silently.

The coordinator reviews each queue item and records approve, reject, or unresolved, with reason and timestamp. Only approved records may be applied to the pilot schedule destination. Accessibility fields should be minimized in the queue, access-limited, and retained only under an approved policy. Do not send reminders or publish volunteer-facing changes during the pilot unless authority is explicitly confirmed. Capture a before snapshot and provide a rollback by replacing the pilot destination with that snapshot.

Acceptance evidence: every input row is accounted for; the two Ari Lee rows produce an explicit duplicate/conflict review item; the 09:00 schedule sample is not silently changed; unresolved items remain visible; approval precedes any schedule update; source values, decisions, reviewer, and timestamps are auditable; rollback restores the prior snapshot; and baseline/outcome measures are recorded for the agreed pilot window. Success thresholds require organizational agreement because none were supplied. A failed threshold should stop expansion and return to the prior snapshot.

## Decisions still needed

Confirm the canonical event and shift vocabulary, retention period, identity matching key, accessibility-data handling, who may change schedules, and who may authorize reminders or publication. Confirm whether the pilot may write to a staging copy. These are consequential unknowns; until resolved, they remain constraints rather than implementation assumptions.
