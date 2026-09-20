# Workflow audit proposal

## Evidence and boundaries

I inspected `artifact.md` and `attachments.json`. The brief says the current sequence is Monday collect, Wednesday chase, Thursday copy, Friday format, followed by coordinator review. It supplies two issue examples: Pine is blocked, owned by Sam, and updated 2026-09-15; River is in progress, has no owner in the current export, and was updated 2026-09-10. It also says last week’s report lists River’s owner as Jo. The requested outcome is an evidence-based current-state map, ranked options, a comparison of recurring manual work, and one bounded experiment. Human review, wording decisions, and the decision that a risk is material must remain with a person. No messages or publication may occur without an explicit decision.

The manifest identifies `current-process.md`, `issues.csv`, and `last-report.md` as synthetic attachments. Those three files were not present at the specified trial path, so their contents were unavailable. I did not infer contents from their filenames. I did not fetch the reference URLs in the brief or verify product capabilities; those are therefore untested. No system, message channel, or workflow was changed.

## Current-state map

The coordinator first collects an issue export on Monday. On Wednesday they chase owners, which depends on knowing which records are stale and who should be contacted. On Thursday they copy updates into a status sheet, creating a transcription point. On Friday they format a report, then review wording and risk before leadership receives it. The repeated work is collection, waiting for owners, chasing, copying, and formatting. The quality risks are stale information, missing ownership, contradictory sources, and rework during review. The examples demonstrate a contradiction for River, but provide no measured frequency, elapsed time, or error rate. Any savings below are estimates to be measured, not results.

The required judgment is whether a record is materially risky, whether an owner correction is valid, how wording should be presented, and whether a reminder or publication should occur. Automation can normalize fields, compare snapshots, flag exceptions, and draft a report or reminder; it should stop at a human decision boundary.

## Ranked options

1. **Read-only reconciliation and draft workflow (recommended).** Each week, normalize the export, compare it with the prior report, flag missing owners, stale updates, and contradictions, then create a coordinator queue and draft report. It targets copying, formatting, and some chasing while preserving review. Effort is moderate; maintenance is mainly field mapping and threshold upkeep. The recurring manual work that remains is source collection, resolving exceptions, deciding materiality, and approving any reminder or publication.

2. **Fixed workflow with approved reminders.** Add a stale rule and an approved reminder template after reconciliation. This could reduce waiting and repeated chasing, but requires an authoritative owner source, consent, a channel, and an approver. Effort and maintenance are moderate. Manual work remains for exceptions, consent and approval, and ambiguous ownership. The stale threshold and channel are currently unknown.

3. **Formatting automation only.** Generate the status sheet or report layout from existing fields. This is the smallest implementation and may reduce Friday formatting, but leaves collection, chasing, copying, contradictions, and review largely intact. Effort and maintenance are low, while quality improvement is limited.

## Bounded experiment

Run two weekly cycles in a review-only workspace using the available issue export and prior report when they can be supplied. For each cycle, record timestamps for collection, reconciliation, draft completion, coordinator review, and publication decision. Count records with missing owners, stale flags, contradictions, corrected fields, and rejected drafts. Compare those observations with a manually prepared baseline; baseline values are not currently available and must be measured before claiming savings.

Acceptance evidence: every input record appears in the draft or an explicitly logged exception; River-like contradictions are surfaced with both source values; no reminder or publication is sent automatically; the coordinator can approve, edit, or reject the draft; and the audit log identifies source, timestamp, and decision for each exception. A useful result would be reduced copying or formatting time without increased unresolved contradictions, but the threshold should be agreed before the trial.

Rollback is to stop the draft workflow, discard its generated artifacts, and continue the existing Monday-to-Friday process. Because this proposal is read-only and review-gated, it does not require changing production systems.

## Open decisions and assumptions

The authoritative owner/status source is unknown. The stale definition, reminder channel, owner consent, leadership format, integration availability, and maintenance cost are unknown. I assume the coordinator can provide a prior report and export for the experiment and can review drafts. Before reminder automation, decide who may approve reminders and what evidence is sufficient. Before implementation, confirm the source locations and whether the synthetic attachments can be made available.
