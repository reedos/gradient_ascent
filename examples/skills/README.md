# Skills

Level 5: a registry of three skills (`warranty-checklist`, `unit-conversion`, `citation-style`),
each a short description that is always in context and a longer body that loads only when
chosen. The model reads the descriptions, calls `load_skill` with the name of whichever one
applies, and your code appends its body to the conversation; the model then continues, with that
body available, and decides whether it needs another skill or is ready to answer. Capped at 3
steps and 1500 tokens (`MAX_STEPS`, `MAX_TOKENS`).

Choosing a skill, and the decision to stop, are `decided_by: "model"`; looking one up and loading
its body are always `decided_by: "code"`, the same split `examples/agentic_rag/` and
`examples/single_agent/` make.

Run it:

```
python -m examples.skills --model stub:scripted
```

The three skill descriptions that are always in context, the one the model chose, its body loaded
into the conversation, and an answer that follows that skill's own checklist.

If a cap is reached before the model stops on its own, the code forces one last no-tools call for
a final answer, `decided_by: "code"`, and the trace records which cap it was.
