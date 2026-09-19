# Organizations of agents

Level 7: three roles — researcher, writer, reviewer — share one task board. `coordinate` asks a
coordinator model which open task to hand to which role (`decided_by: "model"`); a fixed
`BUDGET_PER_ROLE` caps how many tasks a role can take in one round no matter what the coordinator
asks for, and claiming a task is checked against the board itself, so a task the coordinator
tries to assign twice in one call is only ever claimed once.

Run it:

```
python -m examples.organizations_swarms --model stub --question "Fact-check the DW-300 section before it ships"
```

`tests/test_example_organizations_swarms.py` scripts a coordinator that tries to over-assign one
role and to double-claim one task in a single call, and checks the budget and the no-double-claim
rule both hold.
