# Workflow audit — first response

## Evidence reviewed

The supplied fixtures are explicitly synthetic. The registration export contains two records for Ari Lee with the same name/email but different phones and shifts (09:00 and 10:00). The schedule sheet assigns Ari Lee to Harvest at 09:00. I treat these as evidence to investigate, not as permission to merge, overwrite, or notify.

## Proposed staged design

1. **Capture and preserve.** Keep an immutable intake snapshot for each export, with received time and row identifier. Normalize names, contact fields, event labels, and shift formats into comparison fields while retaining the original values.
2. **Review queue.** Flag likely duplicates and disagreements (same email/name with different phone or shift; event-label variants; schedule-versus-registration differences). Show the source values side by side, including uncertainty and sensitive accessibility notes with restricted access.
3. **Coordinator decision.** A coordinator explicitly chooses link, keep-separate, or needs-more-information for each suspected duplicate, and records the reason and reviewer. For a shift conflict, record the chosen value and authority source; do not infer it from row order.
4. **Controlled publication.** After review, publish approved assignments to the scheduling workbook or a reviewed staging sheet. Keep correction history and before/after values. Volunteer-facing visibility remains gated on coordinator approval.
5. **Automation pilot.** Only after permission and data-governance decisions, automate low-risk import, normalization, and exception reporting. Keep assignment changes and reminders behind explicit review and a dry-run/audit mode.

## Initial disposition of the sample

- **Possible duplicate:** the two registration rows share name and email but have different phones. Proposed status: `needs-review`; no merge.
- **Shift conflict:** registration includes 09:00 and 10:00 while the schedule sheet has 09:00. Proposed status: `conflict`; 09:00 is not treated as authoritative until the coordinator confirms it.
- **Accessibility information:** limit access to authorized reviewers, avoid copying it into broad exports, and record only the minimum operational fields needed for accommodation.

## Decisions needed before implementation

1. Which system is authoritative for identity/contact details, event labels, and final shift assignments? Who may approve a schedule change, and does that authority differ by event?
2. May an automation connect to or write the scheduling workbook? If yes, should it be read-only, staging-only, or allowed to update approved rows, and what rollback/audit requirements apply?
3. May the workflow send reminders? If yes, who authorizes them, through which channel, and what consent, opt-out, and accessibility constraints apply?
4. What matching key is approved (email, phone, a volunteer ID, or a coordinator-confirmed link), and what evidence is required to merge records?
5. What event naming vocabulary, retention/deletion period, and access roles apply, especially to accessibility data?

I need answers to these authorization and governance questions before turning the proposal into an implementation-ready design. Until then, the fixtures support only a review queue and audit trail.
