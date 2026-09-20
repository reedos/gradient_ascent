# WA-2 simulator notes

The packet was represented with the four real workflow-audit field keys: `process`, `pain`, `evidence`, and `preserve`.

Known facts retained from the packet:

- One form feeds spreadsheets for scheduling, accessibility needs, and attendance.
- Registrations are copied manually.
- The synthetic examples contain two Ari Lee registration rows with the same email, different phones (`555-0101` and `555-0199`), and shifts `09:00` and `10:00` for `Harvest`.
- The synthetic schedule row lists Ari Lee for `Harvest` at `09:00`.
- Export and attendance are editable.
- A coordinator reviews assignments before volunteers see them.

Unknowns preserved for organizational clarification:

- Whether automation may connect to the scheduling workbook.
- Whether reminders may be sent and who has authority to send them.
- The source of truth.
- The matching key and duplicate resolution policy.
- Canonical event naming.
- Retention requirements.
- Who has authority to change schedules.

The staged-design request is recorded as a recommendation request only. No merge, schedule change, automation connection, reminder, or message was executed. Accessibility information is treated as sensitive, and corrections should retain an audit trail with visible uncertainty.
