# Prompt chaining

Level 3: four fixed steps, always run in this order: rewrite the question into up to three
search queries, retrieve for each with keyword search, draft an answer from what came back, and
check the draft's citations against what was actually retrieved.

Two of the four steps call the model (the rewrite and the draft), but the code decides the
sequence before either call happens and always runs all four steps regardless of what the model
returns. That is the difference from level 4: the model fills in step content, never step order.
The citation check is what earns this level a better score than RAG on questions where a single
retrieval pass misses a fact that needs a second, differently worded query.

Run it:

```
python -m examples.prompt_chaining --model stub:scripted
```

All four steps printed: the rewrite into three queries, what the five retrievals returned, the
draft, and the citation check keeping the one citation retrieval actually supports.

Every step is `decided_by: "code"`, the same as levels 0 through 2, even the two that call the
model: the chain never branches on what the model says.
