# Measurement CSV conversion tool specification (provisional)

## Purpose and contract

The tool accepts one measurement CSV and a requested target unit for each supported dimension, then writes a newly named converted CSV and a machine-readable or human-readable report of handled columns, source units, target units, row counts, and errors. Temperature, length, and pressure are the only documented dimensions in this handoff. The existing conversion utility must be discovered and used after its package import, API, supported-unit catalog, and version compatibility are verified. This document does not authorize running the tool, changing inputs, adding dependencies, or publishing outputs.

The input is read-only. The output must be created separately, with no in-place edits. Exact destination and naming remain unknown. Proposed default: write beside the source using a deterministic suffix such as `.converted.<target-profile>.csv`; refuse to overwrite any existing path unless an explicit, separately authorized overwrite option is provided. A repeat run against the same unchanged input and profile should produce equivalent content and a stable report, while an existing output should cause a clear collision error rather than a duplicate or silent replacement.

## Data and validation

The reader should preserve the header, recognize blank rows without silently shifting fields, and retain non-measurement columns unchanged. A conversion mapping must identify each value column, its unit column or declared unit, its target unit, and its dimension. Every unit token must be nonempty, recognized by the verified utility, and compatible with the declared dimension. Missing units, malformed numeric values, unknown units, and dimension mismatches are errors. The tool must never coerce them into plausible numbers. Error records should include source row number, column, reason, and remediation; the original text should remain visible in the report and, where the output schema permits, in the corresponding output cell.

Proposed default is fail-closed: if any required conversion is invalid, do not emit a promoted “successful” converted file. A diagnostic artifact may be emitted only if its status clearly says failed or partial and it preserves the problematic rows. Whether valid rows may be converted alongside invalid rows is a material policy decision. Mixed-unit columns likewise require a decision: row-wise conversion is useful when each row has a valid unit, but whole-column failure is simpler and safer. No rounding or precision rule is confirmed; preserve utility precision by default and document the chosen serialization format before implementation.

Illustrative input (not verified):

```csv
id,temp,temp_unit,length,length_unit
1,21,C,2,m
2,70,F,unknown,m
3,5,,4,kg
```

Illustrative behavior: row 1 is convertible; row 2 has a malformed length value; row 3 has a missing temperature unit and an incompatible length unit. The report must identify all three conditions and must not represent `unknown` or kilograms as a length conversion. Any converted values shown in examples are intentionally omitted until the utility API and precision are verified.

## Side effects, permissions, and errors

Required permissions are read access to the input and write access to the selected output directory. Logs and reports must exclude secrets and include only paths, schema metadata, counts, and actionable diagnostics. Errors should distinguish unreadable input, malformed CSV, missing mapping, unknown unit, incompatible dimension, invalid value, unsupported target unit, output collision, and interrupted write. Writes should be atomic where the platform permits: write a temporary sibling, validate it, then rename it into the final destination. An interruption must leave the original untouched and must not advertise a complete output.

## Dependencies and workflow integration

Before implementation, verify the existing utility package, import path, callable API, unit catalog, temperature semantics, pressure/length dimensions, numeric and text handling, and supported runtime versions. Confirm the destination/naming convention and link this tool into the workflow specification’s definition-of-done builder step. The workflow should require a reviewable report and human maintainer review for any newly requested unit. No model-based conversion is proposed; behavior should be deterministic and utility-backed.

## Acceptance checks and fixtures

Use fixtures for valid temperature, length, and pressure rows; headers plus blank rows; missing units; unknown units; malformed numbers; incompatible dimensions; mixed units; boundary and negative temperatures; repeated runs; pre-existing output; and interrupted writes. Check both structure and meaning: unchanged source bytes, expected headers and row alignment, correct dimension validation, no invented values, deterministic collision handling, atomic output behavior, and complete actionable reporting. Run these checks only after the utility interface and workflow authorization are supplied. Current status: specification drafted; no conversion, package import, or acceptance check was executed.
