# Proposed `AGENTS.md`

## Purpose

This repository is a small community website with event pages and accessibility notes. Preserve working links while planning or making any approved reorganization.

## Scope and applicable guidance

- This file is intended for the repository root as `AGENTS.md`, so it should govern the repository unless a more specific, existing instruction file applies in a descendant directory.
- Before changing guidance, inspect all applicable instruction files and resolve conflicts explicitly. Do not silently replace existing guidance with the former layout note.
- Written instructions describe workflow expectations; filesystem permissions, sandbox/tool access, and deployment credentials must enforce actual boundaries.

## Verified project structure

The supplied synthetic tree identifies:

- `legacy-pages/index.md`
- `legacy-pages/events/spring.md`
- `legacy-pages/assets/logo.svg`
- `legacy-pages/scripts/check-links.ps1`

The supplied starting guidance says pages stay in `legacy-pages`, the release volunteer publishes, and the link check is run. A former note proposes `content/` and `assets/`, but gives no approval or date and is therefore not authoritative.

## Conventions and reuse

- Keep existing pages under `legacy-pages` until an approved migration plan exists.
- Preserve existing URLs and links. If a move is approved, document redirects or equivalent link-preserving handling before moving files.
- Reuse the existing asset and script patterns. Do not infer that the former `content/` and `assets/` note replaces the current `legacy-pages` rule.
- Keep accessibility notes with the relevant event/page content unless repository evidence establishes another convention.

## Allowed actions and approval boundaries

- Local inspection, comparison of guidance, and running the repository’s link check are allowed.
- Drafting a reorganization plan is allowed.
- Do not move, delete, or rename files before review and explicit approval for that change.
- Do not publish, deploy, or claim hosting access. Publication belongs to the release volunteer and is a separate step.
- Do not assume credentials, hosting configuration, or deployment ownership.

## Verification and completion reporting

- The expected link-check entry point is `legacy-pages/scripts/check-links.ps1`, based on the supplied synthetic tree. Its behavior and invocation were not independently verified in this handoff.
- Before completion, report the exact checks run and their results, checks not run and why, files changed, and remaining uncertainties. A successful command is evidence about that command only, not proof of deployment or complete correctness.
- A reorganization is ready for review only when the proposed target layout, URL/link preservation approach, authoritative guidance, and deployment owner are all stated. Publication remains outside this artifact.

## Definition of done for the guidance/reorganization plan

1. Applicable instruction files and their directory scopes have been identified.
2. The conflict between the current `legacy-pages` rule and the former `content/`/`assets/` note is explicitly resolved or left as a review decision.
3. The actual tree and reusable check command have been verified from repository evidence.
4. Proposed changes list file moves only after review, with link-preserving handling for affected paths.
5. The link check has been run and its output recorded, or is marked unrun with a reason.
6. The release volunteer and publication boundary are documented without claiming deployment.

## Unresolved items

- The full repository tree, existing instruction-file set, link-check invocation/output, and URL scheme were not independently verified from this handoff.
- The public references `https://reedos.github.io/gradient_ascent/agents.md` and `/llms.txt` could not be fetched in this environment.
- Confirm whether the supplied synthetic attachments represent the current repository state before treating this draft as final operational guidance.
