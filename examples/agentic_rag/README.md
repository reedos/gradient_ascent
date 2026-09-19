# Agentic RAG

Level 5: a loop with two tools, `search(query)` and `read(cite)`, that keeps running until the
model stops calling tools, capped at 6 steps and 4000 tokens (`MAX_STEPS`, `MAX_TOKENS`).

`search` returns only titles and citations, not full text, so the model must call `read` before
it can rely on a section: a question that needs two documents (a part's price and the manual
that confirms it fits) takes one search and two reads, chosen by the model as it goes, rather
than a retrieval count fixed in advance. Every tool call and the decision to stop are
`decided_by: "model"`; running a tool, and forcing a final answer if a cap is hit before the
model stops on its own, are `decided_by: "code"`.

Run it:

```
python -m examples.agentic_rag --model stub --question "Does the 2026 bulletin affect the DR-210?"
```

This is the level where the site's dashed-edge count stops being small: compare its trace to
`examples/function_calling`, which allows exactly one model-decided step.
