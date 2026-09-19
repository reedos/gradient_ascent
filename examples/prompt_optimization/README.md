# Prompt optimization: search, select, report separately

Three candidate system prompts are scored against the site's 32 exact-graded questions, split into
a development set and a held-out set. Every candidate is scored on the development set only; the
best-scoring one is picked, and only then is it scored on the held-out set, which no candidate was
compared against while being chosen. No weights are touched and no training API is contacted.

Run it:

```
python -m examples.prompt_optimization --model stub:scripted --max-questions 6
python -m examples.prompt_optimization --model stub
```

The first scores the three candidates on four of the site's own questions: one takes 4/4, the
other two take 0/4, and the winner then confirms 2/2 on the two held-out questions it was never
compared against. `--max-questions` is what makes that small enough to read, since the whole set
is 80 model calls. The questions and the grading are the real ones; there are fewer of them, and
a score from four questions is evidence about four questions.

The second is the full 32-question set against the echo stub: every candidate ties at 0/24, so
the "selected" one is just the first in the list and the search has chosen nothing. A real model
makes the development scores differ, which is what the selection step needs to mean anything.

A `held_out_fraction` that would leave no development questions raises instead of returning a
result, and so does a `max_questions` below 1: selecting on nothing and printing a held-out score
for the winner would read exactly like a search that worked.

Every step is `decided_by: "code"`: the code always tries every candidate, always grades the same
way, and always picks the top score. The model's own output never chooses what happens next.
