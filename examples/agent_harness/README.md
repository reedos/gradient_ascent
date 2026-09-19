# The agent harness

Level 5: the same loop as `single_agent`, built from four pluggable parts instead of one fixed
shape: a `ToolRegistry` (definitions plus an allowlist), a `ContextPolicy` (`keep_everything` or
`trim_to_budget(n)`), a `Hook` (`allow_everything` or `deny_after(n)`), and the step and token
caps (`MAX_STEPS`, `MAX_TOKENS`).

Every tool call, its arguments, and the decision to stop are `decided_by: "model"`. Running a
tool, trimming context, and a hook's veto are always `decided_by: "code"` -- the harness's
decisions, made around the model rather than by it.

Run it:

```
python -m examples.agent_harness --model stub --question "What does the DW-300's drain pump cost, and how long is it under warranty?"
```

`tests/test_example_agent_harness.py` runs the same scripted model twice, once with each context
policy, and shows the answer changes even though the model's own logic did not: the harness
decided what it could still see.
