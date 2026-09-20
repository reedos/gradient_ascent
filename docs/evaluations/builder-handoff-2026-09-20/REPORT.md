# Builder handoff evaluation

2026-09-20 · Gradient Ascent · Exploratory, single-provider trial

## Assessment

The builders produce useful starting artifacts, especially structured acceptance criteria, tool contracts, and continuation handoffs. They do **not** reliably make the receiving model preserve every detail, ask good questions, or consult the reference guide. The four raw-description comparisons do not establish a consistent overall advantage from the builders; both conditions often produced useful results, with different strengths.

The most actionable website finding is in the simplified project brief: its export still includes empty legacy fields labeled “Not specified,” even when the user supplied that information in the three visible free-text fields. That should be corrected before expanding the tool collection.

The trials also exposed a materially inaccurate file-path claim, an inconsistent delivery-completion rule, unnecessary questions, and confusion between using an agent to build a tool and using an agent to operate a workflow. These are evidence-backed improvement targets, not grounds to claim that every output fails.

## What was run

- Thirteen cases: two per new builder, plus one wildlife project-brief regression.
- Thirteen actual live-form submissions. Each simulator supplied its own field answers; the coordinator entered them without rewriting them. Every downloaded Markdown file matched the generated text, and every nonempty submitted value survived export.
- Thirteen isolated receiving-agent trials using `gpt-5.6-luna`.
- Four fresh raw-description baselines using the same model: DUT instructions, wildlife workflow, volunteer-workflow audit, and an unsupported “done” handoff.
- One fresh `gpt-5.6-sol` diagnostic replay of the inaccurate file-path case, without telling that agent about the earlier error.
- Independent grouped reviews using `gpt-5.6-sol`, followed by coordinator evidence checks and documented adjudications where reviewers missed issues.

The site revision at collection was `61ea8eb5f5d1d0277c26374c743711292f974453`. No website source changes or deployments were made. None of the proposed photo, hardware, reporting, or data-cleanup workflows was implemented or executed.

## Findings and proposed corrections

### 1. Personalized exports sometimes label known information as missing

In [PB-1's exported brief](trials/PB-1/artifact.md), the user says to preserve originals forever and approve before sharing. Later sections say “What must the system never do?” and “What needs your approval?” are “Not specified.” Automation is similarly described in the goal but separately labeled unspecified.

This is an export-design issue, rather than a model inventing information. It can encourage redundant questions, although this trial does not prove that it caused a particular question.

**Proposed correction:** Omit empty optional sections from personalized exports, or clearly state that they were not answered *separately* and may already be covered in the description. Keep the full questions in the reusable blank template. Ask the receiving agent to extract known requirements across the whole brief before deciding what is missing.

### 2. Clarification needs to distinguish drafting from implementation

The DUT agents asked for bench addresses and firmware IDs already marked unknown. Those details matter before hardware execution; they need not block drafting project instructions. Other responses squeezed several decisions into each numbered question. Merely asking for “two or three questions” did not ensure a short, manageable interview.

**Proposed correction:** Ask only for decisions needed for the current deliverable. Separate “needed to choose the approach now” from “needed before implementation” and “can remain unresolved in this draft.” Do not repeat an explicit unknown unless the user might now have new information. Treat one question as one decision, not one numbered paragraph.

Evidence: [AI-1 questions](trials/AI-1/builder-response-1.md), [PH-2 questions](trials/PH-2/builder-response-1.md), and [baseline audit questions](trials/WA-2/baseline-response-1.md).

### 3. A valid-looking instruction file can still contain invented facts

The community-site fixture lists `events/spring.md`, `assets/logo.svg`, and `scripts/check-links.ps1`. The first receiver moved them all beneath `legacy-pages/` in its proposed instructions and called the structure verified. The generator did not perform that transformation. The stronger replay preserved the paths and flagged their apparent conflict with the existing guidance.

**Proposed correction:** Require literal preservation of supplied paths, commands, and identifiers. Separate “reported by the supplied example” from “inspected in the current project.” Report conflicts instead of silently normalizing them. This single replay demonstrates variability, not reliable superiority of one model.

Evidence: [fixture](trials/AI-2/attachments.json), [original result](trials/AI-2/builder-final.md), [diagnostic replay](trials/AI-2/stronger-final.md).

### 4. Define completion at the user's destination

The wildlife workflow first declares a run complete once inputs have outcomes and the manifest is saved, then later requires verification at the phone destination. The reviewer initially missed this contradiction and corrected its assessment in a separate adjudication. The plan also adds human receipt confirmation, which deserves scrutiny when the goal is to reduce technical manual work.

**Proposed correction:** State a single end-to-end completion condition. Distinguish processing complete, delivery verified, ready for review, and approved for sharing. Specify how the system verifies delivery, and identify any genuinely unavoidable human action. Keep generated image files, contact sheets, manifests, and text suggestions distinct so a preview cannot substitute for the requested usable output.

Evidence: [workflow result](trials/WF-2/builder-final.md), [adjudication](reviews-pilots-adjudication.md).

### 5. Separate agent-assisted development from runtime autonomy consistently

The project-brief response correctly considers a coding agent building tools once, followed by a fixed recurring workflow. The volunteer audit instead groups “Agent-built or broad rewrite” together and defers it because the problem is bounded and requires human approval. Those are not sufficient reasons to reject using a coding agent to build a small integration.

**Proposed correction:** Compare two separate choices: who or what builds the solution, and how it operates afterward. A small deterministic tool can be agent-built; human review does not imply that its preparation must be manual. Do not force a coding agent when an existing product fits, but evaluate it as a development option without conflating it with a rewrite.

Evidence: [audit result](trials/WA-2/builder-final.md), [project-brief result](trials/PB-1/builder-final.md).

### 6. References and proposed defaults need explicit status

Reference handling varied: one baseline logged successful guide fetches, several trials logged failed fetches, and others did not attempt them. The project-brief response acknowledged not fetching the guide and did not supply the requested concept-page mapping. Links in a prompt do not establish that the site informed the result.

Several outputs introduced specific defaults without a user requirement: a 1% receipt error target, line-item extraction scope, freshness windows, retry counts, carousel sizes, and timing targets. These were generally labeled proposed, which is better than claiming them as facts, but some could meaningfully increase scope or manual correction work.

**Proposed correction:** Distinguish references read, fetches failed, and references not consulted. Make it easy to supply a reference export when browsing fails. For consequential defaults, explain the reason and tradeoff or leave the decision open; reserve arbitrary values for clearly labeled illustrations.

Evidence: [receipt criteria](trials/DD-2/builder-final.md), [PB-1 access log](trials/PB-1/builder-access.md), [successful baseline access](trials/WF-2/baseline-access.md).

## What worked

The generated artifacts generally preserved explicit boundaries and distinguished proposals from executed work. Acceptance matrices used “Not run” status; tool specifications described malformed-input and partial-failure behavior; handoffs kept fixture-reported checks separate from checks the receiving agent had actually performed. Both “unsupported done” conditions rejected the mock output as proof of completion.

Several outputs made the intended destination and recurring human work substantially clearer. The photo tool specification, for example, separates local export creation from phone/cloud delivery. These are useful contributions even when a well-written raw description also performs well.

## Scores and how to interpret them

The detailed eight-dimension scores and supporting evidence are retained in [pilot reviews](reviews-pilots.md), [additional reviews](reviews-additional.md), and [remaining reviews](reviews-remaining.md). The [score summary](score-summary.json) contains the current structured records. The [pilot adjudication](reviews-pilots-adjudication.md) and [remaining-case adjudication](reviews-remaining-adjudication.md) preserve disagreements rather than silently replacing the initial evidence.

Scores are subjective judgments of a *proposal*, not measured implementation accuracy. An acceptable mean can hide a weak dimension or a specific contradiction. Use the findings and quoted evidence before the aggregate number. One run per condition is insufficient for a reliable success rate or model ranking.

## Limits and protocol variations

- All models came from one provider. No model cost, token usage, latency, or human completion time was measured.
- Cases were unusually explicit about constraints and uncertainty. They were easier and more structured than many novice requests, and the raw-description baselines were correspondingly strong.
- Simulators saw captured live form text; the coordinator operated the browser. This tests content generation and handoffs, not independent human form usability.
- Attachments were short synthetic contents embedded in JSON, not full repositories or image files. Several agents tried the named file paths separately and reported them missing. That packaging limited the evidence-use test.
- Five non-baseline builder finals were written provisionally before simulator answers arrived. Those later answers mostly restated unknowns and were saved, but were not incorporated through a rewrite. The independent review explicitly accounts for this variation. The four paired baseline comparisons do not include those five cases.
- The wildlife regression is a simplified variation, not a reproduction of the original 45 MP photo request. Its simulator interpreted “carousel copies” as written “carousel copy.” That ambiguity weakens any claim about whether the resulting plan satisfies a complete image-export workflow.
- Fresh sessions and explicit read restrictions separated roles, but filesystem isolation was not technically enforced. Reviews were grouped and reviewers saw condition labels; coordinators checked their judgments. This was not a blinded review or human study.

## Recommended next step

Correct the personalized-export issue first, then tighten the deliverable, clarification, evidence, completion, and development-versus-runtime guidance. Rerun the failed or disputed cases against the unchanged baselines, add less structured novice descriptions and real synthetic files, and repeat important cases before making reliability claims. Use the saved artifacts for a second-provider replay rather than assuming these findings generalize to every model.

See [replay instructions](REPLAY_WITH_ANOTHER_PROVIDER.md), [case definitions](cases.json), [root orchestration](orchestration-root.md), and [remaining-trial orchestration](orchestration-remaining.md). The complete raw evidence is in `trials/`.
