# Gradient Ascent: newcomer usability session

Status: ready to run; no human sessions recorded for this revision.

## Purpose

Observe whether a newcomer can find one useful concept, explain it, and create a handoff they understand. This tests the website experience, not model quality. Agent simulations cannot substitute for these observations.

## Setup

Invite 3–5 people unfamiliar with the site, including everyday and technical users and at least one phone user. This is a proposed first batch for finding problems, not a representative statistical sample. Use their normal device. Allow about 20 minutes, with permission to stop at any time. Do not request personal files, account access, or confidential project details. Ask permission before recording; handwritten anonymous notes are enough.

Record the date, site commit/version, device/browser, relevant AI experience, and whether the person has seen the site. Use anonymous participant IDs. Start on https://reedos.github.io/gradient_ascent/ with no prior explanation of its navigation or taxonomy.

## Facilitator script

“We are testing the site, not you. Please say what you expect and what seems confusing. You can stop whenever you want. I will mostly watch rather than explain where to click.”

Do not explain the site’s categories, name the target button, or correct a misunderstanding during a task. If the person becomes stuck, ask “What would you try next?” Record any help you provide. Separate unassisted completion from assisted completion.

## Tasks

1. “You have several documents and want useful answers grounded in them. Find something here that helps you understand how that could work.” Ask them to explain what goes in, what happens, what comes out, and one limitation in their own words. Do not require them to know the term RAG.
2. “Choose a small task you would like help with, or use weekly project reporting. Prepare something you could give your own AI to help plan it.” Observe their route, whether they find a suitable tool, and whether they can copy or download the result.
3. “What did the site just create? What would you do with it next? Has anything run or been verified? If this were a request for project instructions, would you install this file directly?” Do not show the expected answer first.
4. “Find one other example that would be useful to you. Where would you go next?” Observe whether optional depth and the full catalogue are discoverable without overwhelming them.

## Observation sheet (one per person)

Participant ID: ___   Date: ___   Site version: ___
Device/browser: ___   Prior AI/site experience: ___
Consent/recording choice: ___

| Task | First route taken | Completed / assisted / abandoned | Time | Confusion or exact quote | Evidence / help given |
|---|---|---|---|---|---|
| Find and explain a concept | | | | | |
| Prepare and export a request | | | | | |
| Explain the output and next step | | | | | |
| Find another example | | | | | |

Record time from reading the task to completion or abandonment; record interruptions separately. Timing is diagnostic, not a pre-agreed pass threshold. Distinguish navigation trouble, wording trouble, technical failure, and unfamiliarity with AI.

## Interpretation for the facilitator

Evidence of success: the person independently reaches relevant material, explains the basic input/action/output, produces a request preserving their intent, and knows it goes to their own model for refinement rather than being a verified implementation. A shorter session is not automatically better if understanding is worse.

Record important misunderstandings explicitly: thinking higher levels are inherently better; expecting the site to call a model; thinking a request is final AGENTS.md; assuming illustrative results were actually executed; thinking every tool is a required step.

## Synthesis and retest

Keep observations separate from interpretations and proposed fixes. Group repeated friction, but retain severe one-off failures. Report participants and assisted/abandoned tasks, not only successes. Prioritize issues by blocked outcomes and misunderstanding. After fixes, repeat the same tasks with fresh participants; do not claim measured improvement from different tasks or coached repeat users.

Results so far: NOT RUN. No participant counts, success rates, or usability gains have been established.
