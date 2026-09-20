# Replay these handoffs with another model provider

Use a fresh conversation per case and condition. Do not give a receiving model `cases.json`, simulator-input.json, entries.json, reviews, or this run's outputs.

1. Choose a case folder in `trials/`.
2. Give the receiving model only `artifact.md` and `attachments.json`. For a comparison, open another fresh session with `baseline.md` and the same attachments instead.
3. Use the receiving-agent prompt from `actor-protocol.md`, substituting a place to save the response if your provider has no filesystem tools. The model may read the public links. Record failed or unavailable access honestly.
4. If it asks questions, a separate simulator should answer using only that case's simulator-input.json. Do not show that file to the receiving model. Preserve unknowns rather than inventing helpful decisions. Save every question and answer.
5. Allow at most three clarification rounds, then ask for a complete provisional artifact with unresolved choices marked. In this first run, after one round of answers that left material facts unknown, the coordinator asked for a provisional artifact rather than further interviewing. Use the same rule for comparable trials.
6. Record provider, exact model/version, exposed settings, date, actual attachments, reference access, and all outputs. Keep costs and times marked unmeasured unless recorded.
7. Give a separate reviewer the plan, case criteria, inputs, dialogue, and output. Use the eight-dimension rubric and cite evidence. Prefer anonymous condition labels if possible.

The synthetic attachment contents are embedded in `attachments.json`; they are the supplied evidence, not names of real files that a model can retrieve elsewhere. Do not supply a real repository or images only to one condition.

The first-run scenarios contain detailed guardrails and explicitly described unknowns. For a more realistic novice test, create a new case version with shorter, less structured user language before running it. Do not change a case midway through a provider comparison.
