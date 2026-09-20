# Sable temperature logger project instructions (initial response)

## Scope

Set up a new device-under-test project for the Sable temperature logger using the shared Python test framework and the past-project structure as references. Treat supplied material as synthetic fixtures. Inspect the framework and draft project-local files only; do not modify shared utilities or shared configuration.

## Known DUT behavior

- Interfaces: USB serial and I2C.
- Temperature range: -10 °C to 60 °C.
- Alarm threshold: 55 °C.
- Firmware build identifier: TBD.
- Bench/device address: TBD.
- Optional instruments: TBD.

## Operating rules

- Keep proposals separate from approved operations.
- Do not invent commands, instrument addresses, measurements, firmware identifiers, or test results.
- Ask the maintainer before adding shared utilities, changing shared configuration, connecting to hardware, flashing firmware, or running board tests.
- Until those approvals and missing details are supplied, limit work to inspection and project-local drafts.

## Proposed project-local layout

```text
tests/
configs/
reports/
README.md
```

Proposed tests should cover USB serial and I2C communication, temperature boundary behavior at -10 °C and 60 °C, and alarm behavior around 55 °C. Exact commands, fixtures, measurements, and pass/fail criteria remain to be confirmed from the framework and DUT brief.

## Questions before finalizing

1. What bench/device address should the project use?
2. What firmware build identifier should be recorded?
3. Which optional instruments are available, if any?
4. May the agent connect to hardware, flash firmware, or run board tests after the project-local draft is reviewed?

Public references were attempted but were inaccessible in the current fetch environment; see `baseline-access.md`.
