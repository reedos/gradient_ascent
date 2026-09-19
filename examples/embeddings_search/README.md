# Embeddings and search

Level 2: index the corpus once, then rank it against a query two ways, by embedding similarity
and by keyword (BM25), and report where the two agree and disagree. There is no model call and
no answer: this is the search step RAG is built on, not RAG itself.

`StubEmbedder` (`examples/common/model.py`) is a deterministic hashing bag of words, not a
trained model. It has no notion that "quiet" and "dBA" are related unless the words themselves
overlap. It is good for exercising chunking, indexing and similarity ranking on a stub, and bad
at exactly the thing a real embedding model is for: finding a passage that answers a question
worded differently than the passage itself. `OllamaEmbedder`, behind the same `Embedder`
interface, is what a real reading of this page's eval would use instead.

Run it:

```
python -m examples.embeddings_search --model stub --question "DW-300 Normal cycle water use"
```

The semantic top three and the keyword top three side by side, and which sections the two agree
on: two of three here, on a query whose words are already in the passage.

Every step is `decided_by: "code"`: what gets embedded, how many results come back, and how they
are compared are all fixed before anything runs.
