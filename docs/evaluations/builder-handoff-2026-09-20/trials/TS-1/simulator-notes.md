# TS-1 simulator notes

Mapped the scenario to the four builder fields while preserving stated unknowns.

- `job` captures the reusable CSV conversion responsibility, preservation, reporting, safe stopping, and proposal-only status.
- `contract` maps CSV inputs and the requested converted-file/report outputs; it leaves destination, naming, API, precision, catalog, and mixed-unit behavior unresolved.
- `reuse` records the known synthetic capability and its undocumented import/API, with inspection required before conversion logic is proposed.
- `limits` retains read-only originals, visible malformed/incompatible data, safe stopping, maintainer review for new units, and unresolved rounding/mixed-unit/approval details.
