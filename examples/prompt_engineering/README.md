# Prompt engineering

Level 1: the same question and the same source passage, sent to the model two ways. The
structured prompt adds a role, an explicit output format, and one worked example. The bare
prompt is just the question. Both are one call; nothing here is decided by the model.

The point is checkable: the structured reply is parsed against a fixed `PART: ... PRICE: ...`
format, so whether the structure helped is a pass or fail, not an impression. A real prompt gets
tuned the same way, against a small set of test cases instead of one.

Run it:

```
python -m examples.prompt_engineering --model stub --structured
python -m examples.prompt_engineering --model stub --no-structured
```

Every step is `decided_by: "code"`: the code always builds the prompt style it was asked for and
asks the model exactly once. Nothing here is a model-made choice.
