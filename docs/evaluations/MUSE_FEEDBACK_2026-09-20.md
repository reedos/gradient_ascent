# External evaluation feedback: Muse / Meta

Received from the user on 2026-09-20. This is an attributed summary of the pasted designer feedback, full-matrix report, and pilot report—not a copy of the underlying trial evidence. The original case cards, simulator entries, captured artifacts, Q&A, condition mappings, and scores were not supplied as files and have not been independently inspected here.

## Reported method and results

The report identifies its actors as Meta Muse Spark 1.3 agents. It describes 13 synthetic cases, with a builder and raw-description receiving condition for every case, isolated receiving agents, and independent reviewers blinded to A/B condition mapping. Scoring was by models, not people. Each condition had a maximum of three clarification rounds. The artifacts were captured from live read-only previews, not byte-compared with downloaded files.

Reported overall means: builder **3.875**, baseline **3.875**. The 11 non-pilot cases averaged 3.864 versus 3.966. Reported critical failures: zero. Evidence/files and verification/failures had the largest negative dimension deltas, −0.273 and −0.364 respectively. Outcome fidelity and automation also had smaller negative deltas; the losses were concentrated in, rather than exclusive to, evidence-related dimensions.

| External case | Builder | Baseline | Reported observation |
| --- | ---: | ---: | --- |
| AI-1 | 4.000 | 3.875 | Preserved four claimed-but-missing attachments as unresolved and asked about them |
| AI-2 | 3.625 | 4.000 | Silently selected continue rather than preserving an open halt/continue decision |
| WF-1 | 4.000 | 4.000 | Tie |
| WF-2 pilot | 4.000 | 3.500 | Avoided the baseline's invented recurring handwritten `keepers.txt` chore |
| DD-1 | 4.000 | 3.875 | Left walkthrough duration unfilled instead of inventing a time budget |
| DD-2 pilot | 3.875 | 3.250 | More explicit acceptance matrix and manual-effort measurement |
| WA-1 | 4.000 | 4.000 | Tie |
| WA-2 | 4.000 | 4.000 | Tie |
| TS-1 | 4.000 | 4.000 | Tie |
| TS-2 | 3.875 | 3.875 | Tie after disclosed contamination and blinding repairs |
| PH-1 | 3.500 | 4.000 | A reported homeowner/city call became a check the receiving agent claimed to have run |
| PH-2 | 3.625 | 4.000 | Lost named contributor dependencies and assigned a draft to an unspecified location |
| PB-1 | 3.875 | 4.000 | Specified 1080×1350 for a 3:4 step; those dimensions are 4:5 |

The report's case IDs are **not** the same case definitions as our earlier evaluation. For example, its PH-1 concerns a homeowner/permit record, while ours concerns a report-generator handoff. Do not pool scores or treat repeated IDs as matched cross-provider replications.

## Recommendations reported by Muse

1. Trace factual claims to supplied evidence; label assumptions and missing information explicitly.
2. Preserve unresolved decisions rather than choosing an answer silently.
3. Verify quantitative specifications, including dimensions, aspect ratios, and counts.
4. Explicitly identify what the user has not supplied while retaining short, focused clarification.

Preserve the successful behavior: explicit unknowns, missing-attachment questions, acceptance matrices, and accounting for recurring human effort.

## Attribution and scoring issues to resolve

The current site generator is deterministic: it inserts form values and static guidance. `buildArtifact` in `site/src/lib/artifact-builders.ts` does not call a model or autonomously invent case-specific panel counts, people, paths, or city calls. A polished artifact can still contain an unsupported claim entered by a simulator, and guidance can influence the receiving agent, but the stage of introduction matters.

For disputed cases compare: **user card → simulator entries → captured website export → clarification → receiving output**. Identify the first appearance or omission of each claim. The external report alone cannot establish whether the form/template, simulator, capture/transcription, or receiving agent introduced it. This distinction is not a reason to dismiss the reported failure.

An accurate evidence taxonomy should allow facts from user answers, supplied files, cited references, or actual checks—not only facts explicitly typed by the user. Preserve who reported or observed each fact. A user-reported check must never become a check the receiving agent performed.

The zero-critical-failure conclusion needs reconciliation with the described PH-1 invented execution claim, since the proposed protocol lists fabrication of executed results as critical. The report also discloses a TS-2 baseline that wrote and executed a fixture generator despite proposal-only instructions. That is a protocol violation even if the extra code was deleted and no external side effect occurred. These do not invalidate every trial, but they do qualify the statement that all boundaries held universally.

The pilot rewards a proposed timing budget in DD-2, while DD-1 rewards leaving a timing budget unknown. Those can both be reasonable depending on the task, but grading should distinguish a measurement method, an illustrative target, and a user-approved acceptance threshold. Merely proposing a number is neither automatically good nor automatically a failure.

## Other reported limitations

- Small samples, one reviewer per pair, no inter-rater reliability, and no measured costs.
- All roles used the same provider/model within this study.
- Browser disconnects required re-entry; artifact captures required disclosed transcription corrections.
- Some receiving conversations continued through successor agents carrying Q&A.
- TS-2 initially leaked condition labels; the review was discarded and rerun blind.
- TS-2 initially accessed a private card; that receiving run was discarded and rerun.
- Provider/model identity is stated in the full report, but the pilot also says some surfaced actor metadata was unavailable. Treat identity as reported rather than independently established here.

## Relationship to our evaluation

Both studies suggest that structure can preserve automation and clarify deliverables, while polished prose does not ensure factual grounding. Neither establishes reliable superiority over a well-written raw description. The external study adds valuable reported examples, especially reported-versus-executed checks, contributor omissions, and numeric consistency. Its broader paired coverage and reported blinding improve on parts of our design, but the different cases and uninspected raw evidence prevent a controlled provider comparison.

See [the consolidated improvement plan](BUILDER_IMPROVEMENT_PLAN.md) and [our completed report](builder-handoff-2026-09-20/REPORT.md). No website changes were made when recording this feedback.
