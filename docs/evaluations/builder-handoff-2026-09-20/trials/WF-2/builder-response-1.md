I could access `artifact.md` and `attachments.json`. The attachments are explicitly synthetic placeholders, so I am treating their image quality, GPS values, and dimensions as example inputs rather than executed checks.

Confirmed requirements: a weekly, automatic batch process starts after original wildlife photos are added; originals remain untouched; suggested carousel packs reach phone review with grouping, crops, resized exports, captions/metadata, and a map end card only when location is available and safe; you approve before sharing; blurry, duplicate, uncertain-crop, missing-location, and privacy cases are flagged for review.

Proposed defaults: keep generated work in a separate review area; use deterministic grouping and export rules first; stop after bounded retries; make each run resumable with a run manifest and per-item status; treat location as “not safe to publish” until the review decision is recorded.

Documented capabilities: the brief identifies original files, a metadata CSV, sample folders, and phone review as available inputs/destinations. Untested assumptions: the actual folder watcher, supported image formats, phone-review destination, crop/export limits, duplicate threshold, and location-safety source are not specified or verified here.

1. What exact phone-review destination should receive the generated packs (for example, a local synced folder, photo album, or another named destination)?
2. Should location safety be a human approval field for every GPS-bearing pack, or may a documented rule auto-allow some locations?
3. Which input formats and maximum batch size should the first version support?
