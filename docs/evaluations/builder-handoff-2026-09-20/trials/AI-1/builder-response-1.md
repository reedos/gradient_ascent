Confirmed from the supplied files:

- Target artifact: `AGENTS.md` for a Sable temperature logger sensor-board project.
- DUT scope: USB serial and I2C; temperature behavior from -10C through 60C; a 55C alarm.
- Intended project shape: `tests/`, `configs/`, `reports/`, and `README.md`, reusing a shared read-only pytest framework, fixtures, and report helpers.
- Hardware commands, bench address, firmware build identifier, measurements, and test results are not supplied or verified.
- The starting brief permits drafting project files for review, while hardware connection, flashing, board tests, shared utilities, and shared configuration changes require approval.

Proposed defaults (for review):

- Keep the shared framework read-only and place project-specific tests/configuration/report outputs under the new project tree.
- Treat the 55C alarm threshold, -10C/60C endpoints, USB serial, and I2C as planned coverage until acceptance limits and observability are supplied.
- Mark all commands, addresses, firmware IDs, measurements, and verification outcomes as unresolved unless later evidenced.

Material questions:

1. What exact acceptance limits and alarm behavior should define pass/fail at -10C, 55C, and 60C (including hysteresis, timing, and clear conditions)?
2. What bench address, firmware build identifier, and optional instruments should the plan name, if any?
3. Should the project instruction file authorize only offline/dry-run planning by default, or may it authorize board tests after separate hardware approval?

The attached `artifact.md` and `attachments.json` were accessible. The attachment entries are explicitly synthetic, so they support planning only; no checks were executed and no hardware or repository conventions were independently verified.
