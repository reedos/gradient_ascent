# Builder access record

## Files inspected

- `artifact.md` — project brief and recommendation constraints.
- `attachments.json` — two synthetic inline attachment descriptions and their declared roles.

The declared examples identify a wildlife-folder input and a location-table input. They indicate a duplicate (`fox-01-copy.jpg`) and a missing location (`heron-02.heic`), while supplying coordinates for `fox-01.jpg`. They do not provide image bytes, EXIF, a real CSV, a desired carousel example, or a failure-output example.

## Files deliberately not inspected

No simulator, entries, criteria, source, or other-trial material was used. The recommendation below is based only on the two files above and the requirements written in the brief.

## Actual checks and limits

- Confirmed that the brief requires originals to remain untouched, human review before sharing, phone delivery of suggestions, and surfaced exceptions.
- Confirmed that square/portrait, carousel size, exact-coordinate policy, trigger, delivery service, and automation level are unanswered.
- No processing, image inspection, duplicate detection, map generation, phone delivery, publication, or deletion was performed.
- No external reference pages were fetched in this handoff review; documented capabilities and integrations therefore remain unverified assumptions.

## Evidence needed next

Provide representative JPEG and HEIC files, the actual location export, and one preferred or annotated carousel result. Decide the three questions in `builder-response-1.md`. Then test the intake, EXIF/CSV matching, duplicate and blur reporting, safe-location redaction, review delivery, and the no-write/no-publish boundary on a synthetic batch.
