I could access `artifact.md` and `attachments.json`. The three named attachments are synthetic fixture summaries, not independently verified repository files. I attempted both permitted public references, but neither was accessible through the available web tool, so I have not treated them as read.

Confirmed requirements: preserve pages in `legacy-pages/`, have the release volunteer publish, run the link check, do not move or delete files before review, and do not claim deployment. The proposed `content/` and `assets/` layout has no approval or date and therefore does not currently override the existing rule.

1. Which guidance is authoritative for page location?
   - Keep `legacy-pages/` as the active rule and describe `content/` as an unapproved proposal.
   - Approve migration planning toward `content/`, while still requiring review before any move.

2. Who owns deployment preparation and execution?
   - Agents may prepare and verify local changes; only the release volunteer publishes.
   - Another named role owns deployment (please identify it).

3. Should `scripts/check-links.ps1` be documented as the required link-check command, despite the fixture being synthetic, or left as an unresolved candidate until verified in the actual repository?

