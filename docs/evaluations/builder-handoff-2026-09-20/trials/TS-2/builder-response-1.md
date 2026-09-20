# Builder response 1

I could read `artifact.md` and `attachments.json`. The three files named by the manifest were absent, so I could not inspect their contents. No implementation or export was run.

## Confirmed requirements

- The tool is a personal photo export helper for selected JPEG and HEIC originals.
- Originals must never be deleted; work must be separate and reversible.
- Sharing copies may be resized and cropped under an explicitly chosen policy.
- Attribution metadata should be preserved where supported, with losses reported.
- Every source needs a visible outcome: exported, skipped, duplicate, low-quality, invalid, unsupported, or failed.
- Each run needs a reviewable source-to-output manifest, and partial completion must be distinct from complete success.
- Destination, crop shape, maximum size, naming, and location stripping remain consequential open decisions.

## Proposed defaults (pending approval)

- Write to a new run-specific export directory beside, but separate from, the source tree.
- Use deterministic processing and a manifest keyed by stable source path plus content hash.
- Default to “fail closed” for missing settings, unsupported formats, metadata uncertainty, and low-quality detection unavailable; preserve the source and report the reason.
- Never overwrite an existing output; use a collision status and require an explicit repeat-run policy.

## Questions

1. Should the first supported destination be a local review folder, phone, cloud folder, or both?
2. Which crop shape and maximum dimension should the contract require: square, portrait, and what pixel limit?
3. Should location metadata be stripped by default, retained by explicit choice, or selected per run?

Noncritical unknowns can remain assumptions until those choices are answered. The provisional contract is in `builder-final.md`.
