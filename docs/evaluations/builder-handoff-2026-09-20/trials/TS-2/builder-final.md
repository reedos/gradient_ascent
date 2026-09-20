# Proposed tool specification: personal photo export helper

## Scope and contract

This is a reviewable specification only. It defines a future helper that accepts selected folders or files containing JPEG and HEIC originals, plus finalized export settings. It does not authorize implementation, export, sharing, cloud access, phone access, or publication. The absent synthetic attachments leave the folder and filename examples unverified.

Inputs must include an explicit source selection and settings for destination (`local review folder`, `phone`, `cloud folder`, or `both`), crop shape (`square` or `portrait`), maximum output dimension, naming rule, and location-metadata policy (`strip`, `retain`, or an explicitly chosen per-run value). Missing settings are validation errors. JPEG and HEIC support must be verified against the selected processing library; unsupported files remain untouched and receive an `unsupported` record.

The output is a separate run directory containing sharing copies where processing succeeds, plus a manifest/report. Each manifest row maps one source identity to one outcome: `exported`, `skipped`, `duplicate`, `low_quality`, `invalid`, `unsupported`, or `failed`. It records source path, content hash, detected format, output path when present, dimensions, crop policy, requested maximum, metadata actions, reason, and tool/schema version. The report must distinguish complete success from partial completion and failure.

## Processing and preservation rules

The helper must never delete or mutate originals. It should validate readability, decodeability, orientation, dimensions, and required settings before writing. Cropping must be deterministic and documented, including how the crop window is selected and how EXIF orientation is applied. A low-quality rule must be specified before use; if no verified detector exists, the tool should not silently invent one. It should report the detector/version or mark quality assessment unavailable.

Attribution metadata is copied when the output format and library support it. The manifest must name fields that could not be preserved. Location handling is a deliberate privacy decision: stripping should remove location-bearing metadata where the mechanism supports it and record that action; retaining it requires an explicit choice. Metadata should not be logged wholesale, and secrets must never enter logs.

Naming should be deterministic and collision-safe. The attachment description suggests names such as `trip-001` and `trip-002`, but that example was not inspectable and does not establish a rule. A proposed rule is a user-supplied stem plus zero-padded sequence, with the source hash retained in the manifest. Existing files are never overwritten: the row becomes `duplicate` or `failed` according to the decided repeat-run policy.

## Side effects, errors, and repeat runs

The only intended side effect is creation of a new, separate export directory and its report. Destination delivery is a separate capability requiring verified integration and permission. Actionable errors must state the source, phase, reason, and recovery: invalid settings, unreadable input, decode failure, unsupported format, crop/resize failure, metadata write failure, destination unavailable, or interrupted run. An interruption must leave originals intact, mark unfinished work, and permit safe resumption.

Repeat runs should use source content hashes, settings, and tool version to identify equivalent work. Reusing an existing matching output may be proposed as `duplicate` or `already_exported`; changed settings must create a new run directory. The exact policy remains open until destination and overwrite choices are decided.

## Dependencies and verification plan

Before implementation, verify an existing project capability that can decode JPEG and HEIC, resize, crop, preserve supported attribution fields, and write a manifest. Verify version compatibility, HEIC licensing/runtime behavior, metadata limitations, and any phone/cloud connector permissions. No such capability, detector, integration, or permission is established by this trial.

Fixtures should cover a normal JPEG, normal HEIC, wrong extension, unreadable file, corrupt image, missing settings, duplicate hash, existing output name, low-resolution image, metadata-bearing image, unsupported metadata, and interrupted processing. Acceptance checks should confirm originals are byte-for-byte unchanged; dimensions and crop shape follow finalized settings; names are deterministic; metadata actions are truthful; every source has exactly one visible status; reruns avoid unintended overwrite; and partial results are recoverable. These checks are proposed and were not run.

## Illustrative exchange

The following is illustrative rather than observed output. Given `originals/2026-09-trip/photo.heic`, a selected portrait policy, a finalized maximum dimension, and a local review destination, a successful row could report `exported`, an output such as `trip-001.jpg`, the actual output dimensions, the applied crop, the content hash, and whether attribution and location fields were retained or removed. If the same source hash is encountered in a second selected folder, the second row should report `duplicate` with the first output reference. If decoding fails, the row should report `failed` and retain the original. A low-resolution source should report `low_quality` only when a documented rule classified it; otherwise it should be `skipped` with “quality assessment unavailable.”

The human review step remains part of the workflow. Before any external sharing, the reviewer should inspect the generated copies and manifest, confirm crop and metadata choices, and decide whether any skipped or failed source needs correction. The tool may offer a review summary, but it must not imply that a file was delivered merely because a local copy was created. Destination delivery, if later selected, needs its own receipt or failure status and a verified permission boundary.
