# Memory

Level 2: a small store with three operations, write, recall by relevance and forget,
standing in for what a chat product's memory feature does between conversations. A question in
one conversation is answered using facts written down in earlier ones, not from that
conversation's own history, which this level never sees.

Recall ranks stored facts by embedding similarity to the new question, the same mechanism
`examples/embeddings_search` uses over documents. Forgetting removes an entry outright: nothing
later can recall what was forgotten.

Run it:

```
python -m examples.memory --model stub:scripted
```

Three facts recalled out of the store, and an answer that says no: not because the warranty ran
out on its own, but because one of those facts is that the unit is in a rental property.

Every step is `decided_by: "code"`: the code always writes what it is given, always searches,
always forgets what it is told to, and asks the model once at the end with whatever recall
turned up.
