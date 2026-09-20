# WA-2 baseline answers

1. The authoritative system for identity, contact details, event labels, and final shifts is unknown. A registration export and a scheduling spreadsheet both contain volunteer and shift information, and their sample rows disagree. A coordinator reviews assignments before volunteers see them. Who approves schedule changes, and whether that authority varies by event, is unknown.

2. Permission to connect to or write the scheduling workbook is unknown. The export and attendance data are editable; scheduling permission is not established. Whether access should be read-only, staged for review, or allowed to apply approved updates, and whether rollback is required, is unknown.

3. Reminder authority is unknown. It is unknown whether reminders may be sent, who would authorize them, which channel would be used, what consent or opt-out rules apply, and how accessibility needs should affect reminder handling. No reminder should be sent based on this packet.

4. The matching key and merge policy are unknown. The synthetic examples show the same name and email with different phone numbers and different shifts, so the records must not be merged silently. Evidence required for a merge is unknown; conflicting values and uncertainty should remain visible with an audit trail.

5. Canonical event vocabulary, retention requirements, and access roles are unknown. Accessibility information is sensitive, so its access controls and handling requirements need organizational clarification. No event label, retention period, or role permission is assumed.
