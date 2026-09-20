# AGENTS.md — Sable temperature logger project

## Purpose

Turn the Sable temperature logger DUT brief into a reviewable, actionable test plan and project layout. The project covers USB serial and I2C behavior across -10°C to 60°C, including the stated 55°C alarm condition.

## Scope and evidence

This file is a provisional project instruction artifact based only on the supplied builder brief and synthetic attachment descriptions. The expected project shape is `tests/`, `configs/`, `reports/`, and `README.md`; this structure has not been independently verified in a repository. Reuse the shared Python/pytest framework, fixtures, and report helpers as read-only inputs when they are made available.

The operating range and 55°C alarm are confirmed requirements from the brief. Exact pass/fail limits, hysteresis, alarm timing, alarm clear behavior, bench address, firmware build identifier, and optional instruments remain TBD and must be recorded as unresolved until supplied.

## Working conventions

- Keep project-specific tests, configuration, reports, and documentation under this project’s tree.
- Follow established pytest fixture and reporting patterns when actual framework files are available; do not invent commands, paths, APIs, hardware addresses, measurements, or firmware identifiers.
- Separate confirmed requirements, proposed defaults, documented capabilities, assumptions, and observed results in plans and reports.
- Treat supplied synthetic fixtures as planning references, not evidence that a command, test, or hardware interaction succeeded.

## Allowed actions and approval boundaries

By default, the agent may inspect supplied/read-only references, draft or revise project files for review, map requirements into tests, and prepare offline or dry-run plans.

Before connecting to hardware, flashing firmware, running board tests, changing shared utilities or shared configuration, or operating optional instruments, obtain separate explicit approval. This document does not itself grant that approval. Keep bench address, firmware build ID, and instrument details as `TBD` until clarified.

## Actionable test-plan requirements

The plan should identify coverage for:

1. USB serial communication and observable logger behavior.
2. I2C communication and observable logger behavior.
3. Temperature behavior at the -10°C and 60°C operating endpoints and representative points across the range.
4. The 55°C alarm transition, reported state, timing, and clear/recovery behavior once acceptance limits are provided.
5. Repeatability, captured configuration, firmware identity, and report output, subject to the approved bench setup.

Do not mark any item pass or fail until the acceptance limits and required observables are defined.

## Definition of done

The draft is complete when the project root contains the proposed instruction file, `tests/`, `configs/`, `reports/`, and `README.md` layout or an evidence-based explanation of any deviation; the README maps each DUT requirement to planned coverage; unresolved inputs are listed as TBD; and the plan names the approval gate before hardware execution. Verification must state exactly which files or commands were inspected, which checks were run, their results, and which checks were not run. A successful tooling command alone is not proof of DUT correctness.

## Placement and completion reporting

Place this content in `AGENTS.md` at the project root so agents that discover root-scoped instruction files can apply it. Agent loaders differ, so report the chosen path and whether the current agent actually loaded it; do not assume discovery. Final handoff reports must distinguish changed files, checks actually executed, untested hardware work, assumptions, unresolved questions, and any requested approvals.
