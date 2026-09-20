# Builder response 1

Confirmed from the starting brief: the proposed tool converts measurement CSVs using existing temperature, length, and pressure utilities; preserves originals; emits a clearly named converted CSV plus a handled-column/unit report; and stops safely on missing, incompatible, or malformed units. Inputs may contain headers and blank rows. Malformed values and incompatible dimensions must remain visible rather than becoming plausible numbers.

Documented capability: a synthetic package supports temperature, length, and pressure, but its import/API is undocumented. The attached conversion-utilities, measurements, and tool-policy entries are synthetic descriptions/sample material; no actual attachment files were supplied for inspection.

Proposed defaults are labeled in `builder-final.md`. Two material questions remain:

1. Should a mixed-unit column be converted row by row when each row has a valid unit, or should any mixed-unit column fail as a whole?
2. What output naming and destination policy should be adopted (for example, a sibling file with a fixed suffix and never-overwrite behavior)?

I proceeded with a provisional contract that requires explicit answers before implementation.
