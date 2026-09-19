# Synthetic data: generate, deduplicate, verify

A model paraphrases each of the site's 32 exact-graded questions. Each paraphrase is checked by
normalized text against every one of the 60 questions in the set, not only the 32 it generates
from, since a paraphrase landing on a rubric-graded question is a copy of a question the eval set
already asks, and against every paraphrase already accepted, so a duplicate or a paraphrase that
didn't actually change anything is rejected before it costs a second call. What survives is answered blind by the same model and graded against the seed
question's own accept/require/reject contract (`examples.distillation.run.grade_exact`); only a
paraphrase whose blind answer still passes is kept. No training API is contacted.

Run it:

```
python -m examples.synthetic_data --model stub:scripted --out .local/scratch/synthetic-data/questions.jsonl
```

28 of the 32 paraphrases kept and 4 rejected, split into the reason each was rejected: three
duplicates and one whose blind answer did not pass the seed question's own contract.

With `--model stub`, the interactive stub echoes back a placeholder mentioning the question it was
asked, so nothing collides as a duplicate, but nothing verifies either: the placeholder never
contains a real answer, so every one of the 32 candidates is rejected at the grading step. That is
the checks working correctly on an input that was never trying to be right: a real run needs a
real model to keep anything. Every step is `decided_by: "code"`: the code always generates, always
checks, and always grades the same way.
