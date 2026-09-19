# Context engineering

Level 2: no retrieval. The whole document set goes into one prompt, in an order chosen so the
part that never changes between calls -- the system instructions and the reference documents --
comes before the part that changes every call -- the conversation history and the question. That
ordering is what lets a caching backend reuse the front of the request instead of reprocessing
it. When history plus documents would not fit in the token budget, the code drops the oldest
history turns first and leaves the documents alone.

Run it:

```
python -m examples.context_engineering --model stub --question "What is the DW-300's Normal cycle water use?"
```

Every step is `decided_by: "code"`: what goes in, in what order, and what gets cut are all fixed
by the program before the model ever sees the request.
