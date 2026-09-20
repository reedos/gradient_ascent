# Workflow specification: wildlife carousel suggestions

## Scope and status

This is a complete provisional first version. The original brief and the supplied answers confirm the desired outcome, but the phone destination, location-safety rule, non-JPEG support, and batch limit remain unresolved. The supplied JPG and CSV descriptions are synthetic examples; no image or workflow check was executed.

## Trigger-to-destination sequence

```text
JPEG batch added
  -> detect batch and create run manifest
  -> read CSV metadata and match by filename
  -> assess quality, duplicates, privacy, GPS, and crop confidence
  -> group candidates into suggested carousel packs
  -> generate review copies, crops, resized exports, captions/metadata
  -> add map end card only for approved-safe available location
  -> place pack plus exception queue in [PHONE_DESTINATION_TBD]
  -> human reviews and approves before sharing
```

The system must never overwrite originals or publish/share externally. A run is complete when every input is either in a review pack or has a recorded exception, and the manifest is saved.

## Stage table

| Stage | Input | System action | Output | Required human action/frequency |
|---|---|---|---|---|
| Intake | Added JPEGs | Detect a new batch; assign run ID; copy or reference read-only originals | Manifest and candidate list | Setup: choose watched source and destination [TBD] |
| Metadata | JPEGs, CSV | Match rows by filename; validate timestamps/GPS fields | Normalized metadata with missing fields marked | Per run: resolve unmatched or conflicting rows only |
| Screening | Images and metadata | Score blur, duplicate likelihood, privacy risk, and crop confidence | Per-item status: eligible or flagged with reason | Per flagged item: review; required before approval |
| Grouping | Eligible items | Deterministically group by capture context/time and carousel size rule [TBD] | Suggested packs | Per output: review grouping |
| Rendering | Suggested packs | Produce non-destructive crops, resized exports, captions/metadata, and conditional map card | Review-ready pack | Per output: correct optional crop/caption issues |
| Delivery | Packs and flags | Write to phone-review destination [TBD], with run manifest and exception queue | Phone-review set | Per run: confirm destination receipt |
| Approval | Review-ready set | Record approve, reject, or revise; retain audit status | Approved set or revision queue | Per output: approve before sharing |

## Exception and recovery policy

Missing or unmatched metadata is flagged; the system does not invent details. GPS-bearing items receive a location-present status but no map card unless the configured safety decision is recorded. Privacy concerns, uncertain crops, blur, and likely duplicates go to the exception queue. Empty or corrupt files are skipped with an error.

Retry transient read/render/delivery failures up to two times, then mark the stage failed and continue independent items. Never create a second output for an item already marked successful. Resume from the manifest using per-item, per-stage status; a partial run can be rerun safely. A failed delivery remains review-pending until receipt is confirmed.

## Authorization boundaries

Adding files authorizes processing into the review area only. Approval is required before sharing. The workflow has no authority to publish, message others, alter external albums, expose GPS, or change originals. A future location-safety rule must be explicitly configured and documented; until then, human review is required for every GPS-bearing pack.

## Complete first version

Support JPEG inputs, CSV filename matching, a bounded batch size [TBD], deterministic grouping, blur/duplicate/privacy/crop flags, separate review exports, captions/metadata, and optional map cards gated by human location approval. Use a local or synced review destination once selected. Keep all uncertain values visible in the pack and manifest. Verify completion at the selected phone destination and record approval status.

Before implementation, choose the phone destination, maximum batch size, carousel/export limits, and whether a documented location rule can replace per-pack approval. Until those choices are made, those fields remain unresolved and the workflow must not auto-share.
