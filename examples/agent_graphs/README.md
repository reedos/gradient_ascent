# Agent graphs

Level 6: a graph runner in the same shape as `examples/workflow_graphs/run.py`, where nodes are
functions over shared state and the runner checkpoints after every node. One node, the
supervisor, is a model call that picks the next node from an explicit allowlist
(`ALLOWED_HANDOFFS`, `{"research", "write"}`) instead of a fixed code rule.

The supervisor's own output decides whether the team needs another `research` hop or is ready to
`write`, which code cannot know in advance. Code still runs every node, still checkpoints every
one, and blocks any node name the model invents that is not in the allowlist rather than calling
it. `MAX_RESEARCH_HOPS` (default 4) caps how many times the supervisor may send the team back to
`research` before code forces `write` on its own.

Run it:

```
python -m examples.agent_graphs --model stub:scripted
```

The supervisor sends the team back to `research` three times, each hop surfacing a section of the
corpus the last one did not, and then hands off to `write`.

Every "Supervisor picks the next agent" step is `decided_by: "model"`; every checkpoint, and the
blocked-handoff and hop-cap steps, are `decided_by: "code"`.
