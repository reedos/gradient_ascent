# Provisional builder proposal

## Decision and intended experience

Build a small fixed workflow for recurring operation, with a one-time coding-agent build and validation phase. The workflow should start from a user-selected folder, a watched folder, or a weekly schedule (choice pending), read JPEG and HEIC files without modifying them, and create a separate run workspace. It should group related sightings, draft carousel copy and captions, suggest metadata, and create a map card only when the configured location rule permits it. It should deliver a private review package to the photographer’s phone. Sharing and deletion remain human actions.

Three choices materially affect the design: the trigger, the phone destination, and the visual/location policy. The open questions are listed in `builder-response-1.md`; this document uses labeled defaults only so planning can continue.

## Confirmed requirements and provisional assumptions

Confirmed by the brief: originals are preserved forever; the photographer reviews weekly; suggestions must arrive on a phone; approval is required before anything is shared; blurry images, duplicates, missing locations, and photos that do not fit must be called out rather than discarded; JPEG and HEIC are inputs; fixtures are synthetic.

Proposed defaults pending answers: run on a button press after a folder is ready; use portrait output with six to eight carousel items; place drafts in a private cloud album; show only a broad area on maps and queue exact coordinates for review. These are acceptance targets, not user decisions. If a private album is unavailable, a local review bundle plus a phone sync is a simpler fallback.

## Data flow and recurring work

| Stage | System does | Photographer does | Status |
|---|---|---|---|
| Intake | Read-only scan; copy references and hashes into a run workspace; retain names and provenance | Put the batch in the agreed input location or press Run | Proposed |
| Triage | Generate previews; flag blur, likely duplicates, unsupported/corrupt files, and missing location; never drop an item | Resolve only items needing a correction or leave them queued | Proposed |
| Grouping and drafting | Group related sightings; make a pack manifest, carousel text, caption/metadata suggestions, and an exception report | No intermediate approval assumed | Proposed |
| Location safety | Match approved metadata; redact or generalize unsafe/exact coordinates; withhold map card when uncertain | Set or confirm the safety policy; review flagged location cases | Proposed |
| Delivery | Publish a private draft album or equivalent review package; label each pack and exception | Open it on the phone, edit as needed, and approve selected packs | Proposed |
| Share/recovery | Keep the run manifest for retry; retry only failed delivery; never publish automatically | Share approved content and decide whether to rerun unresolved cases | Proposed |

The main mismatch risk is delivery: a cloud album or message service may need account permissions and may not preserve carousel ordering. That integration is untested until a destination is chosen. A local export is reliable but adds a transfer step, so it is a fallback rather than the preferred experience.

## Approach tradeoffs and first release

Ordinary file software is the most reliable choice for intake, hashing, conversion, manifests, and read-only boundaries. A fixed model workflow is suitable for grouping and copy drafts because its prompts, output schema, and exception labels can be checked on every run. An agent is useful during development to adapt connectors, generate tests, and inspect outputs; it need not have recurring access to the photo folder or phone service. A fully agentic recurring process would reduce setup only if its permissions and decisions were tightly bounded, so it is not the starting choice.

Version one should accept a folder and location export, create a reviewable pack manifest and contact sheets, and deliver drafts to the selected private destination. It should include an exceptions page for the synthetic duplicate and missing-location cases. It should not attempt automatic social posting, exact-coordinate publication, or deletion. More complex automation is justified only after a measured run shows that manual transfer or correction exceeds the agreed time target.

## Proposed checks

For one representative batch, success means every input appears exactly once in either a pack or exceptions report, originals have unchanged hashes, duplicate and missing-location cases are visible, carousel order and copy are editable, and no share occurs before approval. Failure tests should include a corrupt HEIC, ambiguous duplicate, missing location, unsafe exact coordinate, and interrupted delivery; each should preserve the input and produce a retryable status. Proposed hands-on target: five minutes per run for intake and phone review, excluding one-time setup and optional copy edits. This timing and the quality threshold are estimates until measured. No checks have been executed in this handoff.

The actual attachments needed to validate these claims are image files, a real location export, and a preferred or annotated carousel example. No external reference pages or product integrations were fetched here, so their capabilities remain unverified until the destination and architecture are chosen.
