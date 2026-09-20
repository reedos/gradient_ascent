# Independent additional reviews

Same-provider reviewer limitation applies. These are isolated synthetic trials, not a human usability study or reliable provider comparison.

| Case / condition | Outcome | Automation | Clarification | Usefulness | Evidence | Authority | Verification | Proportionality | Mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AI-2 builder | 3 | 3 | 1 | 3 | 1 | 4 | 2 | 3 | 2.50 |
| AI-2 stronger-final | 4 | 3 | 4 | 4 | 4 | 4 | 3 | 4 | 3.75 |
| WF-1 builder | 3 | 4 | 1 | 4 | 3 | 4 | 3 | 2 | 3.00 |
| PH-2 builder | 4 | 3 | 3 | 4 | 4 | 4 | 4 | 4 | 3.75 |
| PH-2 baseline | 4 | 3 | 3 | 4 | 4 | 4 | 4 | 4 | 3.75 |

## AI-2

The original builder final contains a material evidence error. `attachments.json` literally lists `legacy-pages/index.md`, `events/spring.md`, `assets/logo.svg`, and `scripts/check-links.ps1`; the final rewrites the last three beneath `legacy-pages/`. This hides the useful conflict between `events/spring.md` and the active page-location rule and invents the link-check path `legacy-pages/scripts/check-links.ps1`. It also asks none of the requested questions about authoritative guidance or deployment ownership. Boundaries remain strong: no moves before review, no publishing, and no assumed credentials.

The stronger replay preserves every literal path, calls out the event-page conflict, asks three focused questions, and records unknown hosting ownership and publisher availability. Deadline and external bookmarks remain implicit; those facts were lost in the form and not recovered by the receiver. The replay's improvement is therefore mainly receiving-model behavior, not a builder change.

## WF-1

The final preserves end-to-end automation and limits recurring work to exception review plus one review per draft. It retains claim-level provenance, refuses silent conflict resolution or closure inference, supports partial recovery, and stops before sending. Completion is checked at the configured review destination, which remains unknown and explicitly requires setup.

Clarification is poor: no questions are asked, while 09:00, seven-day freshness, and a local folder are introduced as proposed defaults. They are not claimed facts, but freshness and destination are consequential choices. Two retries, manifests, and multiple approvals also add complexity without measured justification. The statement that attached files were accessible overstates access to JSON descriptions, though the final immediately labels them synthetic.

## PH-2

Builder and baseline both correctly reject “done,” explicitly state that the workspace and private reference are unavailable, treat mock output as non-evidence, request the complete implementation and data contract, and separate future validation from executed checks. Neither performs cleanup. The builder has particularly clear stop conditions; the baseline adds useful hashes, reproducibility records, and edge cases. Their clarification questions are somewhat compound and repeat known unavailable facts, but the resulting briefs remain highly actionable. No critical failure was found in any reviewed condition.
