# Builder improvements: consolidated proposed work

Updated 2026-09-20. Status: proposed, not implemented. Sources: [our executed evaluation](builder-handoff-2026-09-20/REPORT.md) and [user-supplied Muse evaluation feedback](MUSE_FEEDBACK_2026-09-20.md). Do not treat the external scores as independently verified or pool the different case sets.

## Priority 1: preserve facts, unknowns, and their sources

- Remove misleading empty-field “Not specified” sections from personalized briefs when information may be present in free-text answers. Retain the questions in blank templates.
- Separate user-reported facts, claims in supplied files, independently inspected evidence, actual checks with results, proposed choices, and unresolved items.
- Preserve the subject of every evidence claim: “the user reports that X checked Y” is not “I checked Y.” An attachment being mentioned is not evidence it exists or was read.
- Keep unknowns and open judgments open. Do not silently choose halt/continue, invent a location, guess a directory parent, or infer an approval.
- Preserve named people, dependencies, deadlines, exceptions, and boundaries during summarization. Add a final coverage check against supplied requirements.
- Keep paths, commands, identifiers, and quoted facts literal; surface contradictions instead of silently correcting them.

Acceptance probes: no false missing-information labels when notes contain the fact; absent attachments remain absent; reported checks remain attributed; no altered paths; named dependencies survive; unresolved failure policy and file location stay unresolved.

## Priority 2: define the actual deliverable and remaining human work

- Specify what must exist, in what format, where, and how delivery is verified.
- Distinguish processing complete, delivered, ready for review, and approved for publication. A manifest, contact sheet, or proposal is not automatically the requested finished file.
- List recurring human actions and frequency. Do not introduce selection lists, manual transfers, or per-item preparation that contradicts the intended experience.
- Separate agent-assisted development from recurring runtime autonomy. A coding agent may create a small deterministic tool; that does not imply a broad rewrite or an always-on agent.

Acceptance probes: automatic photo preparation without an invented `keepers.txt` task; system-level delivery verification where feasible; completed outputs at the requested destination; agent-built fixed tools evaluated independently from autonomous operation.

## Priority 3: ask material questions without manufacturing certainty

- Extract already-known facts across the whole brief before asking questions.
- Ask one main decision per question. Distinguish what is needed to draft the artifact from what is needed before implementation or operation.
- Do not repeatedly ask for facts explicitly unavailable. Carry them as unresolved with a clear point at which they matter.
- Explain why a consequential proposed default is useful and what changes if it is rejected. Do not turn an arbitrary target into an agreed acceptance criterion.
- Distinguish the measurement procedure, illustrative target, and approved threshold. Missing a timing target should not prevent proposing how to measure effort.

Acceptance probes: no repeated bench-ID question when merely drafting instructions; no compound multi-decision questionnaire; no silent precision, freshness, or timing requirement.

## Priority 4: validate quantitative specifications and reference use

- Require unit, dimension, aspect-ratio, count, total, and constraint consistency checks for any numbers the receiving agent introduces.
- Use deterministic validation when a builder actually derives numeric output; do not imply that the current text-only generator calculates image dimensions.
- Check width-to-height convention: 1080×1350 is 4:5; a 3:4 example at width 1080 is 1080×1440. Keep the user's ratio unresolved if its orientation or meaning is ambiguous.
- Distinguish references read, fetches failed, and references not consulted. Provide a portable reference-export fallback.

Acceptance probes: ratio/dimension agreement; incompatible units remain errors; missing source access is explicit; requested concept recommendations link to references actually read.

## Retest before drawing stronger conclusions

1. Preserve current cases and outputs as the baseline; do not overwrite them with improved results.
2. For the external PH-1, AI-2, PH-2, and PB-1 findings, obtain simulator entries, exact exports, receiving Q&A/output, and source cards before assigning failure to a particular stage.
3. Run matched before/after trials with the same frozen inputs and model settings. Add messy novice descriptions, literal synthetic files, open decisions, contributor dependencies, and numeric traps.
4. Use blinded reviews and adjudicate concrete evidence errors. Treat claimed execution without evidence and proposal-only execution violations consistently with the critical-failure policy.
5. Replay identical artifacts across providers for a controlled comparison; keep different scenarios separate. Repeat important cases before claiming reliable gains.
6. Evaluate form comprehension with actual users separately from model handoff quality.

Preserve the builders' useful structure: stage tables, acceptance matrices, explicit unknowns, reported-versus-executed checks, boundaries, and measurement of recurring human effort. The objective is better fidelity and traceability, not more confident or longer prose.
