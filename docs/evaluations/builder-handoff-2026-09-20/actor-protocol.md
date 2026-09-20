# Actor invocation protocol

Each actor starts with `fork_turns: none`. First-pass model: `gpt-5.6-luna`. Reasoning effort not overridden. No actor may inspect other cases, criteria, generator source, or another condition's outputs. Read only your explicitly assigned packet and permitted public reference links. Filesystem isolation is instructional, not enforced.

## Simulator

Read only `trials/ID/simulator-input.json`. Act as the person described, with their knowledge and uncertainty. Map their own words into the captured live form labels, hints, and placeholders. Do not copy the site's example as a user fact. Save `entries.json` with `{ "slug": "...", "values": { "fieldKey": "answer" } }`, using real field keys. Save `simulator-notes.md` listing confusion, skipped fields, and any assumption needed to fit the form. Do not read private criteria or generator source. Do not invent technical knowledge. Later, answer clarification from case facts; say you do not know when appropriate. No project execution.

## Receiving agent

Read only the provided artifact (or baseline) and `attachments.json`. Use them to produce the requested plan or artifact. Ask about consequential missing details as needed. Public reference links in the packet may be read; record actual access and failures in a condition-specific access log. Do not read other workspace files, simulator packet, criteria, or generator source. No implementation or external actions.

Save the first response verbatim in `CONDITION-response-1.md`. If questions are needed, end your turn so the coordinator can obtain answers. Later save each continuation response under a new numbered filename. Once enough is known, save the complete deliverable as `CONDITION-final.md`. Mark assumptions, proposals, and checks actually performed. Do not claim synthetic fixture results were executed by you. Keep any fixture-reported results explicitly attributed.

## Coordinator

Run `node .local/eval-browser.cjs generate ID` to enter simulator answers into the live form without editing. A matching download is required. Preserve artifacts verbatim. Route at most three rounds of questions to the original simulator, saving questions/answers and their destination condition. Then ask for a provisional final artifact with unknowns marked. Baseline receivers are new sessions, same model and permissions, never shown builder artifact. All trial work is proposed; no project implementation.

## Review

Reviewers can see case facts, criteria and both conditions. Reviews may be grouped to conserve cost; disclose this departure from per-trial reviewer isolation. Apply all eight dimensions from the test plan with evidence. The coordinator independently checks serious findings before reporting them. No cross-provider reviewer was available in this run.
