# Project Instructions

## Purpose and status

This repository contains a small community website with event pages and accessibility notes. These instructions govern safe local maintenance and planning while preserving existing links and the human publication role.

This file is provisional. Its project paths come from synthetic fixture data and have not been verified against the real repository. Before relying on a path or command, confirm it exists in the working tree.

## Scope and placement

Place this content in `AGENTS.md` at the repository root if the selected agent's current documentation says it discovers root-level `AGENTS.md` files. Agent instruction discovery and directory inheritance differ by tool and are unverified here; consult the selected agent's current documentation before placement. If nested instruction files exist, determine their directory scope and reconcile conflicts rather than silently replacing them.

These instructions apply repository-wide unless a verified, more specific instruction file governs a subdirectory. Direct user instructions for the current task take precedence.

## Confirmed project rules

- Keep active pages in `legacy-pages/`.
- Treat the former `content/` and `assets/` layout as an unapproved, undated proposal. It may inform a migration plan for review but does not supersede the current page-location rule.
- The release volunteer is the stated publisher. Agents may prepare local changes and run local checks, but must not publish or claim deployment.
- Do not move or delete files before human review.
- Preserve existing URLs and links in any reorganization proposal.
- Run the required link check for relevant changes.

## Provisional structure

The supplied synthetic tree describes:

```text
legacy-pages/index.md
events/spring.md
assets/logo.svg
scripts/check-links.ps1
```

This structure is unverified. Inspect the real tree before editing. The apparent `events/spring.md` location may conflict with the rule that pages stay in `legacy-pages/`; report that conflict, but do not move the file without review. Reuse established naming, formatting, metadata, navigation, and asset-reference patterns found in nearby verified files.

## Allowed work and boundaries

Within the user's authorized task, agents may inspect repository files, compare applicable guidance, make local edits, prepare a reorganization proposal, and run local checks. Keep changes small and reversible.

Human review is required before moving or deleting files. Publication is separate and remains with the release volunteer. The hosting owner, active status of the volunteer, credentials, and deployment procedure are unknown. Do not infer access or assign deployment authority to another role.

Written guidance does not enforce permissions. Filesystem permissions or sandbox rules should prevent unauthorized writes; tool allowlists should restrict publication and deployment commands; hosting credentials and platform roles should restrict external release access.

## Verification

The required link-check command is provisionally:

```powershell
./scripts/check-links.ps1
```

The path, invocation requirements, successful execution, and expected output have not been verified in the real repository. Confirm the script exists and inspect its usage before running it. Do not invent substitute commands. A zero exit code shows only that the command completed successfully; review its output and scope before concluding that links are correct.

For reorganization planning, inspect the applicable instructions and actual site tree, identify inbound and relative links, note URL-preservation measures such as retained paths or redirects, and flag every unresolved conflict. Do not perform the moves as part of the plan unless separately authorized after review.

## Completion report

At handoff, report:

- files inspected and applicable instruction scope;
- conflicts found, including page locations that disagree with current guidance;
- local files changed and why;
- checks actually run, exact commands, exit status, and relevant results;
- checks not run and the reason;
- proposed moves, link-preservation approach, and items awaiting review;
- unresolved details, including hosting ownership, publisher availability, and any unverified paths.

Never describe synthetic fixtures, planned work, or successful command execution as proof of production correctness or deployment.
