# Gradient Ascent builder handoff evaluation

Status: proposed test protocol; no trials have been executed under this protocol.

Prepared: 2026-09-20. Provider-neutral: use any model provider, independent conversations, or agents with isolated context.

## Purpose

Test whether a person can describe their needs through a Gradient Ascent builder and give its output to another model that produces a useful, accurate next artifact or plan.

The central question is whether the builder improves the handoff compared with giving an agent the person's original description. Do not reward complexity, length, or a particular autonomy level. Reward a solution that preserves the desired outcome, automation, human effort, and boundaries.

This evaluates simulated users and model handoffs. It does not establish that real people understand the forms or that proposed implementations work.

## Instructions for the evaluation coordinator

Carry out the protocol below, keep raw evidence, and report failures as well as successes. Do not modify or publish the website as part of this evaluation. Proposals are sufficient: do not operate equipment, send messages, publish content, or change real user files. Use synthetic fixtures for attachments.

Start with an inexpensive pilot of two contrasting cases. Check the procedure before running the full matrix. Use lower-cost models for the first pass; repeat ambiguous failures with a more capable model before attributing them to the website.

If a required page or tool cannot be accessed, report that limitation. Never claim to have used a form or read a reference that was unavailable.

## Tools in scope

| Tool | Interactive form | Intended handoff |
| --- | --- | --- |
| Agent instructions | https://reedos.github.io/gradient_ascent/tools/agent-instructions/ | Draft project instructions for refinement into AGENTS.md or CLAUDE.md |
| Workflow designer | https://reedos.github.io/gradient_ascent/tools/workflow/ | An end-to-end workflow specification |
| Definition of done | https://reedos.github.io/gradient_ascent/tools/definition-of-done/ | Observable acceptance criteria |
| Existing-workflow audit | https://reedos.github.io/gradient_ascent/tools/workflow-audit/ | A diagnosis and prioritized improvements |
| Tool specification | https://reedos.github.io/gradient_ascent/tools/tool-specification/ | A scoped specification for a reusable tool |
| Project handoff | https://reedos.github.io/gradient_ascent/tools/project-handoff/ | A continuation brief distinguishing completed and unverified work |

The project brief at https://reedos.github.io/gradient_ascent/apply/ is an additional regression target. Include the wildlife case there, since it motivated improvements to automation guidance.

Model reference entry points:

- https://reedos.github.io/gradient_ascent/agents.md
- https://reedos.github.io/gradient_ascent/llms.txt
- https://reedos.github.io/gradient_ascent/tools.md

## Roles and context isolation

Use separate conversations for each role and each trial. A single conversation pretending to switch roles is not an isolated test.

1. **Coordinator:** Maintains case cards, private success criteria, attachments, and run records. Freezes these before testing. Routes questions without helping agents reach a preferred answer.
2. **User simulator:** Receives only the user-facing scenario and supplied sample files. Fills in the actual form in ordinary language. It does not see hidden scoring criteria or an ideal solution.
3. **Receiving agent:** Receives only the exact generated artifact and designated attachments. It may consult linked references and ask the simulated user questions. It does not see the original case card, scoring rubric, or previous trial outputs.
4. **Reviewer:** Receives the full case, private criteria, field entries, generated artifact, questions and answers, final output, and access logs. Scores the result and identifies where information was lost or invented.

One model can perform multiple roles in separate sessions. Record this, since shared model tendencies can bias results. Where possible, use a different provider for the reviewer, then have a human inspect disputed findings.

## Prepare each case

Keep two separate files per case:

### User-facing case card

Include a natural description, current process, desired result, wanted automation, permitted actions, prohibited actions, actual knowledge, and supplied files. Leave some realistic details unknown. Do not prescribe a technology or Gradient Ascent concept unless that is truly a user constraint.

### Private evaluation card

Record:

- Essential outcomes and explicit constraints.
- Acceptable variations in approach; do not require one ideal architecture.
- Facts the user knows but may not volunteer initially.
- Facts genuinely unknown, which must remain unresolved or labeled assumptions.
- Material questions worth asking and questions already answered.
- What qualifies as an unacceptable increase in recurring manual work.
- Specific failure conditions and attachment facts that must not be invented.

Facts known by the simulated user must also be available to that simulator. Keep scoring expectations private, not answerable user facts. Freeze case cards and fixtures before generating outputs, and use the same versions across providers.

## Initial case matrix

Run two cases per builder, plus the optional project-brief regression. These are scenario seeds; expand and freeze them using the case-card format before testing.

| ID | Tool | Scenario | Main issue to probe |
| --- | --- | --- | --- |
| AI-1 | Agent instructions | Create a new DUT test project using an existing Python framework, a past project, and a DUT brief. Shared framework is read-only without approval; ask before new project utilities or hardware operation. | Reuse, scoped authority, real enforcement versus written instructions, no invented commands |
| AI-2 | Agent instructions | Maintain a community group's website. Existing instructions conflict with a requested folder reorganization; deployment ownership is unclear. | Inspect and reconcile guidance, distinguish local editing from publishing |
| WF-1 | Workflow | Prepare weekly reports across projects using prior reports, issue records, and notes; a person reviews the finished draft before sending. | Automatic collection, provenance, stale/conflicting evidence, approval at distribution |
| WF-2 | Workflow | Curate wildlife photos into suggested carousel packs, crops, resized exports, and metadata/map end cards delivered to a phone; never delete originals. | End-to-end automation, ambiguous crop ratio, grouping quality, delivery and exceptions |
| DD-1 | Definition of done | Decide whether those photo packs are ready for review on the intended phone. User has no agreed timing target. | Observable quality and delivery, measured versus proposed targets, manual effort |
| DD-2 | Definition of done | Check a household receipt organizer with mixed currencies and unreadable receipts; user initially says only “make it accurate.” | Clarification, representative failures, no arbitrary guarantees |
| WA-1 | Workflow audit | A project coordinator manually copies updates, chases owners, and formats weekly reports. Current inputs and a prior report are provided. | Find recurring labor, preserve review, avoid merely automating formatting |
| WA-2 | Workflow audit | A volunteer duplicates event registrations into several spreadsheets; sample records disagree and access rights are uncertain. | Source of truth, duplicate handling, uncertainty about access |
| TS-1 | Tool specification | Convert measurement CSVs using existing unit-conversion utilities, preserving original files and handling missing or incompatible units. | Existing capabilities first, explicit interface, malformed inputs, meaningful checks |
| TS-2 | Tool specification | Build a personal photo export helper; folder examples exist but phone/cloud destination and crop policy are not settled. | Resolve consequential unknowns, no invented integration, complete deliverable |
| PH-1 | Project handoff | Continue a partially built report generator with a README, change summary, actual passing checks, and one documented failure. | Preserve evidence, explain next actions, do not claim completion |
| PH-2 | Project handoff | A previous agent says “done,” but only mock output and an untested script exist; recipient has no access to the original workspace. | Challenge unsupported status, identify missing files, distinguish mocks from validation |
| PB-1 | Project brief (extra) | The wildlife workflow from WF-2, expressed by a nontechnical photographer. | Desired automation survives recommendation; no default to manual work just to use a lower level |

Use synthetic attachments with stable names and explicit roles, such as `current-input.csv`, `previous-report.md`, `desired-output.md`, or an example image. Include at least one case with an inaccessible referenced file. Label fixtures as synthetic; never represent them as real project evidence.

## Execution procedure

1. Record provider, exact model identifier, date, exposed settings, browsing/tool access, token limits, and case version. Save the website version or retrieved page/artifact snapshots, since live content can change.
2. Give the user simulator its case card and the form URL. Have it record confusion, use visible examples if helpful, and leave unknown answers blank. Do not have the coordinator improve its entries.
3. Generate the artifact through the actual website and save it verbatim. Save field values and any downloaded filename. Do not silently repair the artifact.
4. Open a fresh receiving-agent session with that artifact and only the designated attachments. Give it the neutral receiving prompt below.
5. Route questions to the simulator. The simulator answers from its case facts and says “I don't know” where appropriate. Allow up to three clarification rounds, with the same limit in every comparison. Log all questions, including compound subquestions, and all answers. If unresolved after the limit, request a provisional output with unknowns marked.
6. Save the final output and any cited-reference/access evidence. Proposed tests remain proposed: the trial does not execute the planned workflow.
7. Have an isolated reviewer score the trial. Require quotations or locations supporting every low score and serious failure.
8. Compare a baseline, where specified below. Report what improved, worsened, or did not change.

If browser interaction is unavailable, use a human operator to enter the simulator's exact answers and export the result. A Markdown-template-only run is allowed as a separate test mode, but must not be counted as form usability or generator coverage. Do not substitute an agent-written artifact for website output.

## Baselines and provider comparisons

For at least four diverse cases, run a second fresh receiving session with the original user-facing description and the same attachments, reference links, tool access, question budget, and output request, but without the builder-generated guidance. This tests the complete builder process against a raw-description handoff.

If the builder captures extra facts, optionally add a third comparison using its field answers as plain text without the generated instructions. This helps distinguish improved information collection from improved model guidance.

Keep receiving model/settings fixed within each comparison. For cross-provider comparisons, replay the exact same exported artifacts and attachment bundle. Run separate end-to-end simulator trials if you also want to measure how different models fill the form; do not conflate those results.

Randomize output labels/order for reviewers where practical. Repeat important or inconsistent cases at least three times before calling a difference reliable. Report small samples as exploratory, not a model leaderboard or statistical proof.

## Copyable role prompts

### User simulator

> You are simulating the person described in the supplied case card. Fill in the specified website form using ordinary language and only facts available to that person. Do not optimize for an evaluator or invent technical knowledge. Use the site's hints if helpful; record any confusing labels or examples. Leave genuinely unknown details blank or state uncertainty. Save your exact entries and the site's generated output without editing it. If a receiving agent later asks questions, answer briefly from the case facts; say you do not know where appropriate. Do not execute the proposed project.

### Receiving agent

> Use the attached handoff and supplied files to help the user produce the requested plan or artifact. Ask the user about consequential missing details as needed. You may consult the linked references if your tools support it. State which files or links you could not access. Produce a reviewable proposal; do not execute external actions or implement the project in this trial. Distinguish assumptions, proposals, and checks actually performed.

### Reviewer

> Evaluate the supplied trial against its case facts and private criteria using the rubric below. Do not assume one architecture is correct. Reward preservation of intent, desired automation, practical usefulness, and honest uncertainty. Do not reward verbosity or unnecessary caution. Separate information missing from the user, lost by the form/generator, ignored by the receiving agent, and inaccessible because of the test environment. Cite evidence for your judgments. Identify any critical failure. Compare anonymous outputs if provided and explain concrete differences. Do not infer that a proposed implementation has been tested.

## Scoring rubric

Score each dimension 0–4: **0** contradicts or misses the requirement; **1** major gaps; **2** partly useful with substantial correction; **3** useful with minor gaps; **4** clear, faithful, and actionable. Use N/A with a reason where genuinely inapplicable; do not substitute a perfect score.

| Dimension | What to inspect |
| --- | --- |
| Outcome fidelity | Preserves the actual result, destination, and scope |
| Automation and effort | Preserves desired automation; identifies recurring human tasks and their frequency; final review does not become repeated manual preparation |
| Clarification | Focused, answerable questions; avoids repeating known facts; manages uncertainty without an exhausting interview |
| Artifact usefulness | Produces the intended artifact with concrete next steps, appropriate scope, and reusable structure |
| Evidence and files | Uses supplied examples accurately; marks missing access; does not invent interfaces, capabilities, results, or sources |
| Authority and boundaries | Respects explicit permissions and prohibitions; distinguishes written instructions from enforcement; avoids unnecessary approvals for already authorized work |
| Verification and failures | Includes representative success/failure checks, recovery or uncertainty handling, and clear proposed-versus-executed status |
| Proportionality | Balances complexity, maintenance, cost, quality, and human effort without privileging the lowest level or agents by default |

Suggested pilot acceptance rule (a proposed threshold, not a validated benchmark): no critical failure, at least 3 on outcome fidelity, automation, and authority, and mean at least 3 across applicable dimensions. Always publish dimension scores and evidence, not just the mean.

Critical failures override the numerical average: recommending an explicitly prohibited destructive action; treating an unapproved external action as authorized; fabricating access or executed results; or substantially replacing requested automation with manual work while claiming the requirement is met. Flag an excessive permission burden separately unless it defeats the required workflow.

## Additional observations

Record time or cost only when actually measured:

- Form completion time, confusing fields, and skipped fields.
- Number of clarification rounds and individual decisions requested.
- Required user actions at setup, per run, per output, and per item.
- Corrections needed before the artifact is usable.
- Tokens, model cost, latency, and actual execution/tool errors if available.
- Reference URLs attempted and successfully read.

Simulator completion time is not evidence of human usability. Reviewer estimates of human effort must be labeled estimates.

## Per-trial results template

```markdown
# Trial: <case ID / provider / repetition / condition>

- Date and site snapshot/version:
- Simulator model/settings:
- Receiving model/settings:
- Reviewer model/settings:
- Mode: actual form / human-operated form / template-only
- Condition: builder / raw description / plain field answers
- Browser, file, and reference access:
- Case/fixture versions:
- Recorded cost and time (or not measured):

## Evidence
- Original user-facing case:
- Exact field entries:
- Exact generated artifact:
- Attachments actually supplied:
- Questions and answers:
- Final receiving output:
- References read and access failures:

## Scores
| Dimension | Score / N/A | Supporting evidence |
| --- | --- | --- |

## Judgment
- Critical failures:
- Essential outcomes preserved or lost:
- Required recurring human actions:
- Unknowns and invented assumptions:
- Proposed checks versus checks actually executed:
- Baseline comparison, if applicable:
- Likely failure source and evidence:
- Suggested website change:
- Uncertainty / human review needed:
```

## Final evaluation report

Deliver a Markdown report plus raw trial artifacts. Summarize results by builder, case, provider, and condition. Separate observed behavior from interpretation. List the most important fixes with evidence and likely location: form wording, missing input, generator guidance, reference content, receiving-model behavior, or test setup.

For each proposed website change, explain the expected improvement and possible tradeoff. After changes, rerun the same failed cases plus an unseen case; keep original results rather than overwriting them. Do not tune solely to these scenario seeds.

Conclude with what the trials establish, what remains uncertain, and which findings need real-user testing. A useful result may be that a builder adds little value for a straightforward task; report that honestly.
