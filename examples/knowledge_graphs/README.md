# Knowledge graphs

Level 2: extract (subject, relation, object) triples from two documents, store them in a small
dict-based graph, and answer a two-hop question by walking two edges -- a part number to the
model it fits, that model to its warranty class -- showing the path as provenance instead of a
single retrieved passage.

Extraction is one model call per document, the same shape as GraphRAG's own indexing step: an
LLM reads the text and states the facts in it. The code always makes these two calls, in this
order, and always walks the graph the same way afterward.

Run it:

```
python -m examples.knowledge_graphs --model stub --question "What warranty class covers the model HLV-5520 fits?"
```

`--model stub` replays a transcribed extraction (`REPLAYED_TRIPLES` in `__main__.py`) instead of
calling anything, so the graph walk runs with no model and no network. It shows what the code
does with triples, not what a model's extraction of those documents looks like; point `--model`
at a real backend for that. Every step is `decided_by: "code"` either way: the model fills in
what a step says, never which step runs next.
