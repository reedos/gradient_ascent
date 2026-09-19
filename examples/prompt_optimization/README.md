# Prompt optimization: search, select, report separately

Three candidate system prompts are scored against the site's 32 exact-graded questions, split into
a development set and a held-out set. Every candidate is scored on the development set only; the
best-scoring one is picked, and only then is it scored on the held-out set, which no candidate was
compared against while being chosen. No weights are touched and no training API is contacted.

Run it:

```
python -m examples.prompt_optimization --model stub
```

With `--model stub`, every candidate ties at 0 correct, so the "selected" one is just the first in
the list — the search has nothing real to search over. A real model makes the development scores
differ, which is what the selection step needs to mean anything. A `held_out_fraction` that would
leave no development questions raises instead of returning a result: selecting on nothing and
printing a held-out score for the winner would read exactly like a search that worked.

Every step is `decided_by: "code"`: the code always tries every candidate, always grades the same
way, and always picks the top score. The model's own output never chooses what happens next.
