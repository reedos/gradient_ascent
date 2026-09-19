# RAG

Level 2: chunk by section, embed the question and every chunk, take the top-k by cosine
similarity, and ask the model to answer using only those sources, citing which ones it used.

Chunking is free here because every corpus section is already a natural chunk (`file#section`).
The embedder is swappable (`StubEmbedder` for tests, `OllamaEmbedder` for a local run) behind
the same `Embedder` protocol the model uses. Retrieval is fixed: the code always embeds,
always keeps the top `k` (default 4), and always asks once. This is where citations enter the
site's running task, and where "conflicting sources" questions start to be answerable, since
more than one chunk can come back for the same query.

Run it:

```
python -m examples.rag --model stub:scripted
```

One grounded answer and the one citation that carries the number, out of the four sections
retrieval put in front of the model.

Every step is `decided_by: "code"`: retrieval and prompting are fixed, and the one model call
answers but does not choose what happens next.
