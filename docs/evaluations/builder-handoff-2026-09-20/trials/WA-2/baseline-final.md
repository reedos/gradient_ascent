# WA-2 provisional workflow audit

## Scope and evidence

The supplied records are synthetic. The registration export has two Ari Lee rows with the same name and email, different phones (`555-0101` and `555-0199`), and different shifts (`09:00` and `10:00`). The scheduling sheet lists Ari Lee for Harvest at `09:00`. These are verified observations from the supplied fixtures. They establish a duplicate candidate and a shift conflict; they do not establish identity, the correct shift, or permission to change either source.

## Provisional source-of-truth position

No authoritative system can be selected yet. Treat the registration export as the preserved intake record and the scheduling spreadsheet as a provisional assignment view until the organization names an authority for identity, contact details, event vocabulary, and final shifts. A coordinator's review remains the publication gate: no assignment should become volunteer-visible solely because it appears in either input.

## Recommended staged workflow

1. **Ingest and preserve.** Save each export with receipt time, source, file/version identifier, and row identifiers. Retain original values. Create normalized comparison fields for name, email, phone, event, and shift without replacing the originals.

2. **Detect and queue exceptions.** Flag probable duplicates (same name/email with differing contact fields), shift disagreements, and event-label variants. Present the competing source values side by side. Keep accessibility notes in a restricted field or separate controlled view, with only the minimum operational detail exposed to assignment reviewers.

3. **Resolve explicitly.** A designated coordinator records one of `link`, `keep separate`, or `needs information` for each duplicate candidate. For conflicts, record the approved value, authority/source, reviewer, timestamp, and reason. Never merge, overwrite, or infer a shift from row order. Preserve before/after values and unresolved uncertainty.

4. **Publish under review.** Write only coordinator-approved results to a reviewed staging area or scheduling workbook after access is authorized. Keep a correction log and a rollback path if updates are eventually permitted. Volunteer-facing output should contain approved assignment data only.

5. **Pilot limited automation.** Begin with read-only import, normalization, exception reporting, and audit-log generation. Move to staging writes only after governance approval and a dry run. Assignment updates and reminders require separate authorization and an auditable approval step.

## Sample disposition

The two Ari Lee registration rows remain separate records with status `needs-review`; matching on name/email alone is insufficient while the approved key and merge evidence are unknown. The 09:00-versus-10:00 disagreement remains `conflict`. The schedule's 09:00 value may be displayed as a source value, but it is not treated as final. No reminder is sent.

## Decisions required before implementation

The organization must designate authoritative systems and the person or role that approves schedule changes, including any event-specific variation. It must define whether scheduling access is prohibited, read-only, staging-only, or permitted to apply approved updates, plus rollback and audit requirements. It must decide whether reminders are allowed, who authorizes them, the channel, consent/opt-out rules, and accessibility handling. It must approve a matching key and merge evidence standard; define canonical event names, retention/deletion periods, and access roles; and specify controls for sensitive accessibility information.

Until those decisions are recorded, the safe deliverable is a preserved intake, a coordinator-facing exception queue, and an audit trail. The fixtures support the proposed process only; they do not verify organizational policy or authorization.
