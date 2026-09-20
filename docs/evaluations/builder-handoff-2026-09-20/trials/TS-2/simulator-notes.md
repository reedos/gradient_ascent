# TS-2 simulator notes

## Confirmed from the simulator input

- The requested artifact is a scoped proposal for a personal photo export helper; this trial requests no implementation or export.
- The helper is intended to organize photos for sharing, create resized copies, apply a crop policy, and preserve attribution metadata.
- Originals must never be deleted.
- Skipped, duplicate, and low-quality files must be shown.
- Known synthetic fixtures include `originals/2026-09-trip`, `edited/`, and `exports/old`, with JPG and HEIC examples.
- Synthetic desired names include `trip-001` and `trip-002`.
- The user reviews every export before sharing, and exact location may be sensitive.

## Unknowns that must remain open

- Destination: phone, cloud folder, or both.
- Crop shape: square or portrait.
- Maximum output size and exact dimensions.
- Naming rule beyond the examples.
- Whether location metadata should be stripped or retained.
- Which image-processing and metadata capabilities are available.
- What constitutes low quality and whether a quality detector exists.
- Any cloud integration, phone API, or publishing permission.

## Proposed specification boundary

The deliverable should define inputs, outputs, a source-to-output manifest, and status categories without pretending the unresolved choices are settled. It should require separate output locations, preserve originals, and make review possible before sharing. A destination, crop, size, naming, and location policy should be selected explicitly before finalization. Defaults should be reversible and should not silently remove metadata or publish files; location handling deserves explicit confirmation because it may be sensitive.

## Checks and failure behavior

- Check that each selected source is readable and is a supported JPEG or HEIC input.
- Check that an output path is separate from the originals and that naming collisions are handled as reported duplicates rather than silent overwrites.
- Record one status per source: exported, skipped, duplicate, low-quality, unsupported/invalid, or failed, with a reason.
- Verify output dimensions, crop policy, naming, and attribution metadata against the finalized settings.
- Report metadata that cannot be preserved by the selected output format or mechanism.
- Treat mixed outcomes as partial completion and require the user to review every export before sharing.
- Report destination or capability dependencies instead of inventing integrations, detectors, APIs, or publishing authority.

## Reviewable finalization checklist

Before the proposal is finalized, obtain decisions for destination, crop shape, maximum size, naming, and location stripping; confirm the available processing and metadata capabilities; define the low-quality rule; and agree on the manifest fields and failure statuses. Then review the specification against the synthetic folder and filename examples without running an export.
