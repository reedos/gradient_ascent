# Organizations of agents

Level 7: three roles, researcher, writer and reviewer, share one task board. `coordinate` asks a
coordinator model which open task to hand to which role (`decided_by: "model"`); a fixed
`BUDGET_PER_ROLE` caps how many tasks a role can take in one round no matter what the coordinator
asks for, and claiming a task is checked against the board itself, so a task the coordinator
tries to assign twice in one call is only ever claimed once.

Run it:

```
python -m examples.organizations_swarms --model stub:scripted
```

The coordinator's five assignments, four of them claimed by the three roles, and the fifth
refused: it names a task another role already holds, and the board, not the coordinator, is what
says so.

`tests/test_example_organizations_swarms.py` scripts the same call plus one that over-assigns a
single role, and checks the per-role budget and the no-double-claim rule both hold.
