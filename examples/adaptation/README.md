# Adaptation: data preparation

Builds and validates a small supervised fine-tuning file from the site's own 60-question set.
No model is called and no training API is contacted; this is the step before fine-tuning, not
fine-tuning itself.

Each question becomes one chat-format JSONL line (`system`/`user`/`assistant` messages, the
shape Together AI's fine-tuning data preparation guide documents), shuffled with a fixed seed
and split into `train.jsonl` and `val.jsonl`. `leaked_questions` then checks that no question's
normalized text appears in both files.

Run it:

```
python -m examples.adaptation --out .local/scratch/adaptation
```

It writes 48 training and 12 validation examples and reports that no held-out question leaked
into training.

Every step is `decided_by: "code"`: the split is a fixed shuffle-and-cut and the leak check is a
fixed comparison: nothing here is a choice a model makes.
