# Lead agent and workers

Level 6: one call asks the lead to split the question into independent sub-questions, at most
`MAX_WORKERS` (default 3); code spawns one worker per sub-question, each of them
`examples.rag.run.run` reused unmodified, and a second call asks the lead to combine
their answers, keeping their citations.

The split is the one model decision in this file: the lead's own output picks how many workers
run and what each is asked, which code could not write down in advance. Everything else is
code's: the worker cap, the team's shared token budget (`MAX_TEAM_TOKENS`), spawning each
worker, and returning its answer to the lead.

Run it:

```
python -m examples.orchestrator_workers --model stub:scripted
```

The lead splits one question into two, a worker is spawned for each, and the merge keeps both
answers and both citations. The split is the model's; the worker count follows from it.

Every worker's own steps are `decided_by: "code"`, the same as `examples/rag/run.py` on its own
page, since retrieval there is fixed. Only the split is `decided_by: "model"`.
