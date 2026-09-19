# One call

Level 1: the question alone, straight to the model. No documents, no tools, no retrieval. The
model answers from what it already knows.

Halvorsen is a fictional maker invented for this eval set, so a model has never seen its
manuals. A correct run mostly means declining lookup and numeric questions rather than
inventing a plausible-sounding part number or price. This level exists to measure that failure
mode directly: the eval score at level 1 is close to the floor set by order zero, and the gap
between them is the value of giving the model documents at all.

Run it:

```
python -m examples.one_call --model stub --question "What voltage does a DR-210 need?"
```

The trace has exactly one step of `kind: "model"`; its `decided_by` is `"code"`, since the code
always makes this one call regardless of what the model returns. Nothing in this level is a
model-made choice.
