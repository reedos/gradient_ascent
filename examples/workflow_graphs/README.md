# Workflow graphs

Level 3: a tiny dict-based graph runner. Nodes (`NODES`) are plain functions that take the
shared state and return an updated state; edges (`EDGES`) are plain functions that read that
state and return the id of the next node, or `None` to stop. The runner writes a checkpoint after
every node.

The graph is the same draft/check/revise loop as write-and-check, plus one branch a single loop
does not express as cleanly: if retrieval finds nothing, the graph goes straight to a dead end
(`no_match`) instead of drafting from zero sources. `state`'s durable fields are all plain values
— strings, an int, a list of citation strings — so the checkpoint after every node is a real
`json.dumps`, not a stand-in for one.

Run it:

```
python -m examples.workflow_graphs --model stub --question "How often should the DW-300's filter be cleaned?"
```

Every step is `decided_by: "code"`: each edge function is a fixed rule the code wrote before the
graph ever ran, even though the state it reads was shaped by what a model said.
