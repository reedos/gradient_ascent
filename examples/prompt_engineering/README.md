# Prompt engineering

Level 1: the same question and the same source passage, sent to the model two ways. The
structured prompt adds a role, an explicit output format, and one worked example. The bare
prompt is just the question. Both are one call; nothing here is decided by the model.

The point is checkable: the reply is parsed against a fixed `PART: ... PRICE: ...` format. Run
against `--model stub`, both commands below print the system prompt they built and whether the
reply matched; the stub only ever echoes the question, so neither matches, which is expected.
`tests/test_example_prompt_engineering.py` scripts a stub that actually answers, so that is where
the pass and the fail both happen.

Run it:

```
python -m examples.prompt_engineering --model stub --structured
python -m examples.prompt_engineering --model stub --no-structured
```

Every step is `decided_by: "code"`: the code always builds the prompt style it was asked for and
asks the model exactly once. Nothing here is a model-made choice.
