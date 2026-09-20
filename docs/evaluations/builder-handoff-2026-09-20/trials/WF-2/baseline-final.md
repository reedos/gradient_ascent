# WF-2 provisional workflow specification

## Goal and boundaries

Each week, turn newly added original wildlife photos into reviewable carousel-pack candidates for phone use. The workflow must preserve every original without deletion or overwrite, automate routine processing, and send uncertain cases to review. Approval is required before sharing. This document is a proposed specification; no processing, delivery, or quality check has been run.

## Trigger and intake

Watch a designated intake location for newly added supported image files. On arrival, record a stable file identity, source path, capture time when available, dimensions, GPS presence, and processing status. Treat an unchanged file as already seen so retries do not create duplicate outputs. Originals remain in their source location and are read-only inputs. The original storage location is still to be chosen.

## Candidate preparation

For each new image, generate a non-destructive working record and inspect signals available from metadata and the image: capture-time proximity, likely scene or subject similarity, duplicate or near-duplicate relationship, blur risk, orientation, and missing metadata. Group likely related images into weekly candidate packs. Put blurry, duplicate, metadata-conflicted, or otherwise ambiguous images into an exception queue with a reason and suggested action. Grouping and quality judgments are proposed behavior, not verified against real photos.

## Pack generation

For each accepted candidate group, create resized exports, crop candidates, and caption or metadata suggestions. Crop dimensions and the maximum number of photos per pack are unresolved: choose square (1:1), portrait (4:5), or both, and set the pack limit before implementation. Until chosen, the workflow must label these as pending decisions rather than silently selecting a format.

Use deterministic names that retain a link to the original identity. Write generated files to a separate output area and keep a manifest containing source identities, selected crop, export dimensions, caption/metadata suggestion, warnings, and approval state.

## Location and privacy

A map end card is conditional: create it only when location is present and the selected privacy policy says it is safe. Exact-coordinate handling is unresolved. Before implementation, choose whether map cards show an approximate area, exact coordinates only after explicit approval, or no location. Also decide whether exported files must have GPS metadata stripped. Until decided, mark location-bearing candidates as privacy-review exceptions and do not claim they are safe to share.

## Review and phone handoff

Place candidate packs and exception reports in a review area for phone inspection. The delivery method and cloud destination are unresolved; choose local phone synchronization, a named cloud drive, or another explicit destination. The review record must make approval, rejection, edits, and privacy decisions visible. Sharing is blocked until approval is recorded.

## Retention and recovery

Generated-pack and exception retention is unresolved and must be specified, along with the storage location for originals. Originals are retained indefinitely unless the owner later changes that requirement; the workflow never deletes or overwrites them. Generated outputs should be versioned or safely replaceable without affecting inputs.

## Decisions required before implementation

1. Crop format: square, portrait, or both; maximum photos per pack.
2. Phone delivery method and cloud destination, if any.
3. Approximate versus exact location policy, approval gate for exact coordinates, and GPS stripping.
4. Retention period and locations for originals, generated packs, and exceptions.

## Verification status

Fixtures and references are synthetic or descriptive. No image processing, crop inspection, duplicate/blur validation, map safety assessment, phone delivery, or sharing occurred. Those are acceptance checks for a later implementation review.
