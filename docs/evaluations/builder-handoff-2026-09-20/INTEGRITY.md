# Evidence integrity checks

Completed 2026-09-20.

- Frozen cases checksum unchanged after trial preparation.
- 13 actual live-form exports match their downloaded Markdown and retain all submitted nonempty field values.
- 13 builder finals, four baseline finals, and one diagnostic replay final are present.
- 18 unique reviewed conditions appear in the current score summary.
- 62 JSON files parsed successfully.
- Relative links in REPORT.md and README.md resolve to existing files.
- Git normalizes line endings. case-freeze.json retains the original byte hash and a canonical LF hash for comparing checkouts.
- Raw model Markdown retains intentional hard-break spaces and an extra final blank line; those three whitespace warnings were not edited out of the evidence.
- These checks establish evidence-file consistency only, not implementation correctness or human usability.
