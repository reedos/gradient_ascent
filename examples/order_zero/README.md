# Order zero

Level 0: no model. Keyword search over the corpus with a BM25-ish score (stdlib only, no
external library) and the best-scoring section returned verbatim. No drafting, no synthesis, no
judgment about whether the section actually answers the question.

This is the floor the site measures every other level against. It is fast, free and completely
predictable, and it fails in an obvious way: it returns a plausible-looking section even when
the real answer needs two documents, arithmetic, or noticing that a fact was never stated.

Run it:

```
python -m examples.order_zero --question "How often should the DW-300's filter be cleaned?"
```

The best-scoring section, printed verbatim with its citation and nothing written around it. The
answer to this question is one sentence in the middle of it.

Every trace step is `decided_by: "code"`; there is no model in the loop to decide anything.
See `examples/common/trace.py` for what a step records, and `evals/corpus.py` for the search.
