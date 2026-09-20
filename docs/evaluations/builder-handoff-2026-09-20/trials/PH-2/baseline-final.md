# PH-2 provisional continuation handoff

## Current status

The claimed cleanup is **unverified**. The original workspace and private reference are unavailable. The supplied CSV is a synthetic mock, and the script excerpt is synthetic, incomplete, and untested. No cleanup, execution, or reference inspection was performed. The mock output therefore cannot establish that duplicates were removed, dates were normalized, or source rows remain traceable.

## Evidence received

- Handoff claim: “duplicates removed and dates normalized”; no run log, source sample, dependency list, commit, or review record.
- `mock-output.csv`: synthetic example only.
- `script-excerpt.py`: synthetic excerpt that reads `input.csv`, drops duplicate rows, and writes `cleaned.csv`; date logic is omitted.
- Receiver answers confirm that all production rules and environment details remain unknown.

## Missing evidence and required inputs

Request the complete script, a sanitized representative input sample, and the data contract. The contract must define duplicate identity (full row, ID, or business key), the winner rule, accepted date formats, timezone handling, invalid-date behavior, encoding, delimiter, expected input row count, output format, and the source-to-output traceability requirement. Also request the exact invocation, runtime/OS/dependency specification, immutable commit or artifact identifier, and a run log containing input/output hashes, timestamps, exit status, warnings, row counts, duplicate counts, and date-conversion failures. A reviewer record and expected output location are also needed.

## Safe validation plan

1. Preserve the original input and establish its schema, encoding, delimiter, row count, and date samples before any transformation.
2. Reproduce the claimed command in an isolated, documented environment using a copy or sanitized fixture.
3. Independently calculate expected duplicate decisions and date conversions from the agreed contract; record rejected or ambiguous values rather than silently coercing them.
4. Verify row-count reconciliation, duplicate outcomes, date parsing, output encoding, and a stable source-row identifier mapping every output row to its input row or inputs.
5. Review edge cases (multiple duplicate candidates, missing/invalid dates, mixed formats, non-ASCII text), retain hashes and logs, and label the result validated only after review.

## Known unknowns and assumptions

Duplicate semantics, winner selection, date rules, CSV encoding/delimiter, expected row count, output details, runtime, OS, dependencies, and compatibility are all **unknown**. The only working assumption is that the intended deliverable is a cleaned CSV whose original rows remain traceable to outputs. All attached fixtures and claims are synthetic examples, not verified behavior.

## Concrete next step

Obtain the sanitized representative sample, complete script, data contract, and environment/invocation details. Do not run or publish a cleaned output until those inputs define the rules and a reproducible validation run can preserve the original and produce auditable evidence.
