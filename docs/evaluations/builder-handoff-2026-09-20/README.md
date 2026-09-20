# Builder handoff evaluation — 2026-09-20

Status: complete. Read [the report](REPORT.md). This is a single-provider exploratory evaluation, not a cross-provider benchmark or real-user usability study.

Completed: 13 live-form builder trials, four isolated raw-description baselines, one stronger-model diagnostic replay, and independent reviews with preserved adjudications. The original protocol is included in [TEST_PLAN.md](TEST_PLAN.md); instructions for another provider are in [REPLAY_WITH_ANOTHER_PROVIDER.md](REPLAY_WITH_ANOTHER_PROVIDER.md).

- Site revision at start: `61ea8eb5f5d1d0277c26374c743711292f974453`.
- Provider: OpenAI through Codex subagents. First-pass actors: `gpt-5.6-luna`; diagnostic receiver and independent reviewers: `gpt-5.6-sol`. No reasoning-effort override was supplied; the effective inherited setting was not independently measured. Coordinator: current parent session; no independent provider used.
- Actual live forms captured in `form-snapshots.json`.
- The simulator supplies field entries. The coordinator operates the actual form via Playwright without rewriting entries, saves its generated artifact, and verifies its downloaded Markdown matches.
- This is an **agent-operated form** variant of the plan's human-operated form fallback. It tests actual form generation and handoff content, not independent human/browser usability. Simulators see captured labels, help text, and examples, not generator source.
- Fresh subagents isolate simulation from receiving. Shared filesystem is not a security boundary: actors are instructed to read only supplied input files. Context isolation relies on fresh sessions and adherence to that restriction.
- Cost, tokens, and human completion time are not measured. Provider comparisons require replaying these saved artifacts elsewhere.
- No website changes, external actions, equipment operations, or real project implementation are authorized by this evaluation.

Per-trial evidence is stored under `trials/<case-id>/`. Scenario and evaluator criteria are frozen in `cases.json`; the receiving agent must not read that file. Baselines receive only a separate raw-description packet and the same supplied synthetic fixtures and reference access.
