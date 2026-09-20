# External evaluation feedback: Grok Bot Technical Reviewer

Received from the user on 2026-09-20. This is an attributed summary and assessment of the pasted feedback, not an independently verified trial report. Its `/workspace/gradient-ascent-eval/` paths and `file://` link belong to the other agent's environment; the raw files have not been supplied here.

## Reported identity and method

The author identifies itself as Grok Bot, profile Technical Reviewer. Its underlying commercial model and provider ID were not exposed. Record that identity as reported; do not infer a particular Grok model version or treat it as a verified provider-controlled replication.

The report describes isolated simulator, receiver, and reviewer sessions on one shared host/model stack. A computer-use operator entered simulator answers into live forms and captured or downloaded the exports. Cases were frozen in three successive pilot packs: rich briefs, thinner briefs, then more varied thin briefs. No cost, token, or latency measurements were collected.

Three conditions were compared: full builder export, raw description, and plain field answers without the generator's guidance. The reported table covers six cases with three scores each. The original logs and condition packets have not been inspected here. Reviewer isolation was reported; condition blinding was not explicitly established in this memo.

## Results as reported

| External case | Builder | Raw | Plain fields | Interpretation reported |
| --- | ---: | ---: | ---: | --- |
| AI-1 | 4.0 | 4.0 | 4.0 | Rich brief, ceiling tie |
| WF-2 | 4.0 | 4.0 | 4.0 | Rich brief, ceiling tie |
| DD-2 | 3.9 | 3.5 | 3.5 | Acceptance-matrix and Not-run guidance added value |
| PH-2 | 3.9 | 3.9 | 3.9 | Fixtures themselves exposed unsupported completion claims |
| WA-2 | 3.9 | 3.9 | 3.9 | Conflicting sheets prompted appropriate uncertainty in all conditions |
| TS-2 | 3.9 | 3.9 | 3.9 | Clarification resolved parameters and conditions converged |

These rounded numbers are preserved as supplied, not reconstructed into more precise scores. All completed conditions reportedly met the exploratory threshold, with no recorded critical failures. There was only one run per case and condition; no three-repeat reliability pass. Proposals were not implemented.

The DD-2 comparison is the most useful new signal: full builder > raw ≈ plain fields suggests that explicit acceptance guidance, rather than field organization alone, helped on that particular vague request. It does not establish a repeatable improvement or prove that all definition-of-done uses benefit. The memo's phrase “benefit is real but narrow” should be read as an observed single-case difference, not a reliability finding.

## Reported strengths and proposed changes

- Preserve acceptance matrices, explicit Not-run status, and measurable definitions of done.
- Rich descriptions, revealing fixtures, and useful clarification can make the raw and builder conditions converge; equal scores do not prove the builder lacks usability value.
- Clarify the agent-instructions question combining allowed changes and approval boundaries.
- Add or strengthen a claimed-versus-verified hint in project handoff.
- Investigate long-answer entry friction: combined paste reportedly failed for the workflow case, while field-by-field entry succeeded.
- Use thin briefs and a rubric capable of distinguishing substantive deficiencies; do not lower scores merely to avoid ties.

## Local source check: paste limit

On receipt, the current `site/src/pages/tools/[slug].astro` was inspected. Its input textareas have no `maxlength` attribute, no custom paste handler, and no explicit length truncation in the update path. `buildArtifact` copies field values with trimming; it does not impose a text-size cap.

That does not disprove the observed paste failure, but it does not support “raise the website's paste limit” as the fix. Reproduce it with the original text size, browser, and entry method, and compare direct paste with the computer-use command. It may be browser-control or combined-entry friction. A per-field import could still be useful, but should not be justified as a confirmed repair for a site-defined cap.

The combined permission label is present verbatim: “What may it change, and when should it ask?” A clearer prompt or two visually separate answer cues could address confusion without automatically adding another required field.

## Relationship to prior evaluations

This report adds a useful third condition that our run did not execute: plain field answers. It supports preserving task-specific guidance, especially where the user cannot yet describe observable success. It also agrees with the broader pattern that well-specified raw descriptions can perform as well as generated briefs.

Do not pool the scores with our or Muse's runs. Case IDs are reused across different case definitions, this report's model identity is unavailable, and the pilot packs and review instructions changed between stages. The report also concerns simulated users, not observed human form comprehension.

The changes are incorporated as proposals in [the consolidated improvement plan](BUILDER_IMPROVEMENT_PLAN.md). No website behavior was modified when recording this feedback.
