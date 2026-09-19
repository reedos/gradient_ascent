# Distillation: capture, filter, write

A teacher model answers the 32 of the site's 60 questions that are graded `"exact"`. Each answer
is filtered by the same accept/require/reject pattern check the site's own eval runner would use
to grade it (see `docs/EVALS.md`). What passes is written as a chat-format JSONL file, a student
training file, in the teacher's own words, not the answer key. No training API is contacted, and
no student model is ever trained here.

Run it:

```
python -m examples.distillation --model stub:scripted --out .local/scratch/distillation/student.jsonl
```

30 of the 32 answers kept and 2 dropped, with the dropped ids named: the filter is what makes the
student file worth training on, so it says which questions the teacher got wrong.

With `--model stub`, the teacher is a placeholder that never matches any grading pattern, so every
question is dropped: a real run needs a real teacher model to keep anything. Every step is
`decided_by: "code"`: the code always calls the teacher, always grades the same way, and always
writes the same filter's output; nothing here is a choice the model makes.
