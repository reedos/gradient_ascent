# Prompt engineering

Level 1: the same question and the same source passage, sent to the model two ways. The
structured prompt adds a role, an explicit output format, and one worked example. The bare
prompt is just the question. Both are one call; nothing here is decided by the model.

The point is checkable: the reply is parsed against a fixed `PART: ... PRICE: ...` format. The
two commands below differ only in the system prompt, which is the one thing `--model stub` cannot
show: it echoes the user turn back, so neither run matches and both print the same reply.
`--model stub:scripted` plays a reply for each style instead, which is what makes the two runs
worth comparing.

Run it:

```
python -m examples.prompt_engineering --model stub:scripted --structured
python -m examples.prompt_engineering --model stub:scripted --no-structured
```

The structured run comes back in the `PART: ... PRICE: ...` shape it asked for and parses. The
bare run hedges ("I believe it's one of the HLV-22 series pumps"), matches nothing, and cites
nothing, from the same question and the same passage.

Every step is `decided_by: "code"`: the code always builds the prompt style it was asked for and
asks the model exactly once. Nothing here is a model-made choice.
