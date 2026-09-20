# Sable temperature logger project instructions

## Purpose and scope

Create a new device-under-test project for the Sable temperature logger using the shared Python test framework and the structure demonstrated by the past project. Treat all supplied files as synthetic fixtures. The agent may inspect the supplied framework and patterns and draft project-local files. The shared framework is read-only unless a maintainer explicitly approves a change.

The project-local draft should use this proposed structure:

```text
tests/
configs/
reports/
README.md
```

Keep any proposed project-local configuration, fixtures, and tests clearly identified as drafts until reviewed.

## DUT facts currently available

- Interfaces: USB serial and I2C.
- Operating temperature range: -10 °C through 60 °C.
- Alarm threshold: 55 °C.
- Bench/device address: TBD; unavailable.
- Firmware build identifier: TBD; unavailable.
- Optional instruments: TBD; unavailable. Do not name or assume instruments.

The plan should propose coverage for USB serial communication, I2C communication, temperature behavior at the lower and upper stated boundaries, and alarm behavior at and around the stated 55 °C threshold. Exact commands, register maps, transport details, fixtures, measurement methods, tolerances, and pass/fail criteria must come from approved project information or the framework. Do not invent them.

## Required operating rules

1. Separate proposed content from approved operations and verified results. Mark unknown values as `TBD` or `unavailable`.
2. Do not invent commands, instrument addresses, measurements, firmware identifiers, test results, device addresses, or hardware capabilities.
3. Do not modify shared utilities or shared configuration without explicit maintainer approval.
4. A review of this project-local draft does not grant hardware approval. Ask before connecting to hardware, flashing firmware, or running board tests.
5. Until those approvals and the missing details are provided, limit work to read-only inspection and project-local drafts.
6. Record actual execution evidence separately from proposals; a test must not be described as run unless an approved run produced evidence.

## Proposed test-plan outline

- **USB serial:** define connection and protocol checks only after approved command and fixture details are available.
- **I2C:** define addressing, transactions, and expected responses only after approved device details are available; the address is currently TBD.
- **Temperature range:** plan checks at -10 °C and 60 °C, with the stimulus and measurement method left TBD until approved.
- **Alarm:** plan checks below, at, and above 55 °C, with hysteresis, timing, and observable output left TBD until approved.
- **Traceability:** record firmware build ID, bench/device address, fixture/instrument identity, measured values, and evidence when those values become available.

Each proposed case should state its preconditions, DUT interface, intended stimulus, expected observable behavior, evidence to capture, and its unresolved assumptions. Keep execution commands and concrete values out of the draft until approved.

## Approval gate

Before any hardware action, the agent must ask the maintainer for approval and for the missing bench/device address, firmware build identifier, and any optional instrument details. Approval must explicitly cover the requested action: hardware connection, firmware flashing, or board-test execution. A project review alone is insufficient.
