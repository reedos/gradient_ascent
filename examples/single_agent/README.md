# Single agent

Level 5: plan-and-execute. One call asks the model for a short plan (plain text, no tools
offered), then a loop offers `search(query)` and `lookup_part(part_number)` and lets the model
act on the plan, revise it, and decide when to stop, capped at 5 steps and 3000 tokens
(`MAX_STEPS`, `MAX_TOKENS`).

The planning call is `decided_by: "code"`: the code always makes it and always moves on to the
loop afterward, whatever the plan says. Every step inside the loop, which tool, with what
arguments, or the decision to stop, is `decided_by: "model"`, the same rule
`examples/agentic_rag/` follows. Compare the two traces: agentic RAG has no separate planning
call, only the loop.

Run it:

```
python -m examples.single_agent --model stub:scripted
```

A two-step plan, two tool calls acting on it, and a stop, with a cited answer carrying both
halves of the question.

If a cap is reached before the model stops on its own, the code forces one last no-tools call
for a final answer, which is `decided_by: "code"`, and records which cap it was.
