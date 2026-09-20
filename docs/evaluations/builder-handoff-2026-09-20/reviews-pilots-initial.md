# Independent pilot reviews: AI-1 and WF-2

Same-provider reviewer limitation applies. These are single exploratory runs, not a human usability study or reliable provider comparison. Scores use the plan's 0–4 rubric; proposed behavior is not treated as executed behavior.

## AI-1

| Condition | Outcome | Automation | Clarification | Usefulness | Evidence | Authority | Verification | Proportionality | Mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Builder | 4 | 3 | 2 | 4 | 4 | 4 | 3 | 4 | 3.5 |
| Baseline | 4 | 3 | 2 | 4 | 4 | 4 | 3 | 4 | 3.5 |

Both outputs preserve the intended project shape, framework reuse, read-only shared assets, and separate approval for shared edits and every hardware action. Both keep commands, addresses, firmware IDs, instruments, measurements, and results unknown. Neither claims project files, hardware checks, or test results were produced. The builder adds a useful definition of done and instruction-placement caveat; the baseline adds a strong per-test schema. Neither created the project tree, but the trial requested a reviewable instruction artifact rather than execution.

Clarification is the main weakness. The builder asks for the bench address, firmware ID, and instruments despite `artifact.md` already marking them unknown. The baseline spends three questions on the same facts from `baseline.md`. These are receiver choices, not form-input loss. No critical failure was found, and both meet the exploratory numerical threshold.

## WF-2

| Condition | Outcome | Automation | Clarification | Usefulness | Evidence | Authority | Verification | Proportionality | Mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Builder | 3 | 4 | 3 | 4 | 4 | 4 | 3 | 3 | 3.5 |
| Baseline | 3 | 4 | 3 | 3 | 4 | 4 | 3 | 4 | 3.5 |

Both preserve automatic intake and preparation, non-destructive originals, phone review, visible exceptions, conditional map cards, and approval before sharing. Both correctly say that image processing, quality checks, privacy assessment, and phone delivery did not occur. Completion at the actual destination remains unavailable because the phone destination is genuinely unknown; neither confuses intermediate review files with delivered output.

The builder is more useful operationally: its stage table identifies human action frequency, and its manifest, retry, resume, and duplicate-prevention rules make automation concrete. Its fixed two-retry policy and manifest complexity are proposals without measured justification. Its questions omit crop ratio, pack size, and retention while asking about a less central batch limit. The baseline explicitly surfaces every consequential crop, pack, destination, privacy, GPS-stripping, and retention decision, but its final lacks stage-level recovery and review-frequency detail. Its initial 4:5, eight-photo, and 30-day defaults are clearly proposals and are withdrawn after the user's unknown answers, so they are premature suggestions rather than invented facts.

No critical failure was found. Both meet the exploratory numerical threshold. The builder's advantage is limited to operational structure; the baseline is at least as strong on preserving unknown decisions.
