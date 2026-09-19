# Parallel calls (sectioning)

Level 3: retrieve a fixed set of candidate sections, ask the model to answer from each one
*alone*, at the same time (`concurrent.futures.ThreadPoolExecutor`), then combine deterministically
— keep whichever sections answered part of the question, in retrieval order, and cite each one
directly, with no citation parsing needed.

Each call sees exactly one passage and nothing about the other calls, so this is sectioning, not
voting: the calls answer different parts of one question rather than all answering the same one.
`.map` submits every call to the pool at once and returns results in candidate order regardless
of which one finishes first, so determinism comes from retrieval order, not from a race.

Run it:

```
python -m examples.parallelization --model stub:scripted
```

Three branches answering from one passage each, one of them saying the passage does not cover the
question, and the two that did answer combined in retrieval order with a citation each.

Every step is `decided_by: "code"`: how many calls go out, which section each one gets, and how
the results are combined are all fixed before the first call is made.
